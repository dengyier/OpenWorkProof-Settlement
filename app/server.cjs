const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const envFile = require('node:path').resolve(__dirname, '../.env');
if (fs.existsSync(envFile)) process.loadEnvFile(envFile);
const { randomBytes } = require('node:crypto');
const { Keypair, PublicKey, SystemProgram } = require('@solana/web3.js');
const { createMint, getMint, getOrCreateAssociatedTokenAccount, mintTo } = require('@solana/spl-token');
const chain = require('./chain.cjs');
const { guardRequest, validateCaseId, validateSignedTransaction, settlementLabel } = require('./security.cjs');
const { propose } = require('./worker.cjs');
const ROOT = path.resolve(__dirname, '..');
const PRIVATE = path.join(ROOT, '.tools/settlement-private');
function save(file, value) { fs.writeFileSync(file, JSON.stringify(value), { mode: 0o600 }); }
function load(file) { return JSON.parse(fs.readFileSync(file)); }
function key(name) {
  fs.mkdirSync(PRIVATE, { recursive: true, mode: 0o700 });
  const file = path.join(PRIVATE, `${name}-keypair.json`);
  if (!fs.existsSync(file)) fs.writeFileSync(file, JSON.stringify(Array.from(Keypair.generate().secretKey)), { mode: 0o600, flag: 'wx' });
  if (fs.statSync(file).mode & 0o077) throw new Error('Private test key permissions must be 0600');
  return Keypair.fromSecretKey(Uint8Array.from(load(file)));
}
function delivery(operation, root, fields = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(path.join(ROOT, '.venv/bin/python'), ['-m', 'bridge.delivery_cli'], { cwd: ROOT, env: process.env });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => child.kill('SIGTERM'), 120000);
    child.stdout.on('data', d => { stdout += d; if (stdout.length > 1000000) child.kill('SIGTERM'); });
    child.stderr.on('data', d => { stderr += d; });
    child.on('error', reject);
    child.on('close', code => { clearTimeout(timer); if (code !== 0) return reject(new Error(`Native OWP refused operation: ${stderr.slice(-2000)}`)); try { resolve(JSON.parse(stdout)); } catch (e) { reject(e); } });
    child.stdin.end(JSON.stringify({ operation, root, ...fields }));
  });
}
async function start({ port = Number(process.env.OWP_PORT || 3188), network = process.env.OWP_NETWORK || 'devnet', rpc = process.env.OWP_RPC || 'https://api.devnet.solana.com' } = {}) {
  const connection = require('./rpc.cjs').connection(rpc);
  const genesis = await chain.assertSafeNetwork(connection, network);
  const program = await connection.getAccountInfo(new PublicKey(chain.PROGRAM_ID), 'finalized');
  if (!program?.executable) throw new Error('Configured settlement program is not deployed/executable on this network');
  let upgradeAuthority = null;
  if (program.owner.toBase58() === 'BPFLoaderUpgradeab1e11111111111111111111111') {
    const programDataAddress = new PublicKey(program.data.subarray(4, 36));
    const programData = await connection.getAccountInfo(programDataAddress, 'finalized');
    if (!programData || programData.data.readUInt32LE(0) !== 3) throw new Error('Invalid upgradeable program data');
    upgradeAuthority = programData.data[12] === 1 ? new PublicKey(programData.data.subarray(13, 45)).toBase58() : null;
  }
  const deployer = key('deployer'), provider = key('provider'), verifier = key('verifier');
  if (await connection.getBalance(provider.publicKey, 'finalized') < 1000000) {
    const seedFile = path.join(PRIVATE, `provider-fees-${genesis}.json`);
    if (fs.existsSync(seedFile) && !load(seedFile).finalized) {
      await chain.waitFinalized(connection, load(seedFile).signature);
      save(seedFile, { ...load(seedFile), finalized: true });
    } else {
      const { tx } = await chain.transaction(connection, SystemProgram.transfer({ fromPubkey: deployer.publicKey, toPubkey: provider.publicKey, lamports: 5000000 }), deployer.publicKey);
      tx.sign(deployer);
      const signature = require('bs58').encode(tx.signature);
      save(seedFile, { signature, finalized: false, recipient: provider.publicKey.toBase58(), lamports: 5000000 });
      await connection.sendRawTransaction(tx.serialize(), { skipPreflight: false, maxRetries: 0 });
      await chain.waitFinalized(connection, signature);
      save(seedFile, { ...load(seedFile), finalized: true });
    }
  }
  const token = randomBytes(32).toString('hex');
  const setupFile = path.join(PRIVATE, `token-${genesis}.json`);
  let mint;
  if (fs.existsSync(setupFile)) mint = new PublicKey(load(setupFile).mint);
  else {
    mint = await createMint(connection, deployer, deployer.publicKey, null, 6);
    save(setupFile, { mint: mint.toBase58(), genesis, program: chain.PROGRAM_ID, label: 'DemoUSD (test token; not dollars/USDC)' });
  }
  const mintInfo = await getMint(connection, mint, 'finalized');
  if (mintInfo.decimals !== 6 || !mintInfo.mintAuthority?.equals(deployer.publicKey) || mintInfo.freezeAuthority) throw new Error('Demo mint configuration mismatch');
  const sessions = path.join(ROOT, '.tools/delivery-sessions');
  fs.mkdirSync(sessions, { recursive: true, mode: 0o700 });
  const locks = new Set();
  const stateFile = id => path.join(sessions, `${validateCaseId(id)}.json`);
  const nativeRoot = id => path.join(sessions, validateCaseId(id));
  function terms(s, summary) { return { ...s.terms, job_id: summary.job_id, work_order_digest: summary.work_order_digest, bundle_digest: summary.bundle_digest, acceptance_digest: summary.acceptance_digest }; }
  async function current(id) {
    if (await connection.getGenesisHash() !== genesis) throw new Error('Network changed');
    const s = load(stateFile(id)), summary = await delivery('summary', nativeRoot(id));
    if (JSON.stringify(summary.chain_terms) !== JSON.stringify(s.terms)) {
      for (const k of Object.keys(s.terms)) if (summary.chain_terms[k] !== s.terms[k]) throw new Error('Native settlement terms mismatch');
      if (Object.keys(summary.chain_terms).length !== Object.keys(s.terms).length) throw new Error('Native settlement terms mismatch');
    }
    const onchain = await chain.snapshot(connection, terms(s, summary));
    if (['Delivered', 'Disputed', 'Settled'].includes(onchain.status) && onchain.bundle_digest !== summary.bundle_digest) throw new Error('On-chain delivery digest mismatch');
    if (onchain.status === 'Settled' && onchain.acceptance_digest !== summary.acceptance_digest) throw new Error('On-chain acceptance digest mismatch');
    return { s, summary, onchain };
  }
  async function prepareTx(id, kind) {
    const { s, summary, onchain } = await current(id), t = terms(s, summary);
    if (s.pending?.signature) throw new Error('A broadcast transaction is pending; refresh before retry');
    let ix;
    if (kind === 'fund') {
      if (BigInt(t.deadline) <= BigInt(Math.floor(Date.now() / 1000))) throw new Error('Funding deadline expired');
      if (onchain.status !== 'NotFunded') throw new Error('Order already funded'); ix = chain.fundInstruction(t);
    }
    else if (kind === 'release') {
      if (onchain.status !== 'Delivered' || summary.acceptance_decision !== 'ACCEPTED') throw new Error('Accepted native delivery and Delivered chain order required');
      const authorized = await delivery('authorize', nativeRoot(id));
      for (const k of ['job_id', 'work_order_digest', 'bundle_digest', 'acceptance_digest', 'chain_terms_digest']) if (authorized[k] !== summary[k]) throw new Error('Attester evidence binding mismatch');
      ix = chain.releaseInstruction(t);
    } else if (kind === 'reject') {
      if (onchain.status !== 'Delivered' || summary.acceptance_decision !== 'REJECTED') throw new Error('Native rejection required');
      ix = chain.rejectInstruction(t);
    } else if (kind === 'refund') {
      if (onchain.status !== 'Funded' || BigInt(t.deadline) > BigInt(Math.floor(Date.now() / 1000))) throw new Error('Undelivered expired order required');
      ix = chain.refundInstruction(t, false);
    } else if (kind === 'mutual-refund') {
      if (!['Delivered', 'Disputed'].includes(onchain.status)) throw new Error('Delivered/disputed order required');
      // Disclosed prototype policy: app-owned provider consents to customer-requested
      // cancellation. This is not unilateral arbitration or independent-provider approval.
      ix = chain.refundInstruction(t, true);
    } else throw new Error('Unknown transaction kind');
    const { tx, block } = await chain.transaction(connection, ix, t.customer);
    if (kind === 'release') tx.partialSign(verifier);
    if (kind === 'mutual-refund') tx.partialSign(provider);
    const serialized = tx.serialize({ requireAllSignatures: false }).toString('base64');
    s.pending = { kind, prepared: serialized, lastValidBlockHeight: block.lastValidBlockHeight, draft_id: randomBytes(16).toString('hex') };
    save(stateFile(id), s);
    return { transaction: serialized, draft_id: s.pending.draft_id, kind, terms: t };
  }
  async function reconcile(id) {
    const { s, summary } = await current(id);
    if (!s.pending?.signature) return;
    const pending = s.pending;
    const status = (await connection.getSignatureStatuses([pending.signature], { searchTransactionHistory: true })).value[0];
    if (status?.err && status.confirmationStatus === 'finalized' || (!status && pending.lastValidBlockHeight && await connection.getBlockHeight('finalized') > pending.lastValidBlockHeight + 32)) {
      // Expired or positively failed: preserve evidence, never replay the old transaction.
      // The public finalized history was queried before clearing the transport lock.
      s.transactions ||= [];
      s.transactions.push({ kind: pending.kind, signature: pending.signature, finalized: !!status?.err, reconciled: false, failed: status?.err || 'expired without finalized inclusion' });
      s.pending = null; save(stateFile(id), s); return;
    }
    const record = await chain.waitFinalized(connection, pending.signature, 1500);
    if (['fund', 'release', 'refund', 'mutual-refund'].includes(pending.kind)) chain.reconcileTransfer(record, terms(s, summary), pending.kind === 'mutual-refund' ? 'refund' : pending.kind);
    const onchain = await chain.snapshot(connection, terms(s, summary));
    const expected = { fund: 'Funded', submit: 'Delivered', release: 'Settled', reject: 'Disputed', refund: 'Refunded', 'mutual-refund': 'Refunded' }[pending.kind];
    if (onchain.status !== expected) throw new Error('Finalized transaction/state mismatch');
    s.transactions ||= [];
    s.transactions.push({ kind: pending.kind, signature: pending.signature, finalized: true, reconciled: true });
    s.pending = null; save(stateFile(id), s);
  }
  async function submitDelivery(id) {
    const { s, summary, onchain } = await current(id);
    if (onchain.status !== 'Funded' || s.pending?.signature || summary.verification_decision !== 'VERIFIED') throw new Error('Verified funded delivery without pending transfer required');
    if (BigInt(s.terms.deadline) <= BigInt(Math.floor(Date.now() / 1000))) throw new Error('Delivery deadline expired');
    const { tx, block } = await chain.transaction(connection, chain.submitInstruction(terms(s, summary)), provider.publicKey);
    tx.sign(provider);
    const signature = require('bs58').encode(tx.signature);
    s.pending = { kind: 'submit', signature, lastValidBlockHeight: block.lastValidBlockHeight }; save(stateFile(id), s);
    try { await connection.sendRawTransaction(tx.serialize(), { skipPreflight: false, maxRetries: 0 }); }
    catch (e) { throw new Error(`PENDING: ${signature}; submit outcome requires reconciliation (${e.message})`); }
    try { await reconcile(id); } catch (e) { if (!e.message.startsWith('PENDING:')) throw e; }
    return view(id);
  }
  async function dispatch(route, body) {
    if (route === '/api/config') return { network, rpc, genesis, program: chain.PROGRAM_ID, upgrade_authority: upgradeAuthority, provider: provider.publicKey.toBase58(), verifier: verifier.publicKey.toBase58(), mint: mint.toBase58(), model_configured: !!process.env.DEEPSEEK_API_KEY, token_label: 'DemoUSD — test token only' };
    if (route === '/api/create') {
      const customer = new PublicKey(body.customer), id = randomBytes(16).toString('hex');
      const customerATA = await getOrCreateAssociatedTokenAccount(connection, deployer, mint, customer);
      await getOrCreateAssociatedTokenAccount(connection, deployer, mint, provider.publicKey);
      await mintTo(connection, deployer, mint, customerATA.address, deployer, 1000000n);
      const t = { network, genesis, program: chain.PROGRAM_ID, customer: customer.toBase58(), provider: provider.publicKey.toBase58(), verifier: verifier.publicKey.toBase58(), mint: mint.toBase58(), amount: '1000000', deadline: String(Math.floor(Date.now() / 1000) + 3600) };
      await delivery('create', nativeRoot(id), { customer_public_key: customer.toBuffer().toString('hex'), chain_terms: t });
      save(stateFile(id), { terms: t, pending: null, transactions: [] });
      return { id, ...(await view(id)) };
    }
    const id = validateCaseId(body.id);
    if (locks.has(id)) throw new Error('Case operation already running');
    locks.add(id);
    try {
      if (route === '/api/view') {
        try { await reconcile(id); } catch (e) { if (!e.message.startsWith('PENDING:')) throw e; }
        return await view(id);
      }
      if (route === '/api/transaction') return await prepareTx(id, body.kind);
      if (route === '/api/submit') return await submitDelivery(id);
      if (route === '/api/broadcast') {
        const { s } = await current(id);
        if (!s.pending || s.pending.draft_id !== body.draft_id || s.pending.signature) throw new Error('Stale or already broadcast transaction');
        const tx = validateSignedTransaction(s.pending.prepared, body.transaction);
        // The prepared message includes the exact frozen instruction and attester signature.
        // Last-minute native verification is repeated before sending a release.
        if (s.pending.kind === 'release') await delivery('authorize', nativeRoot(id));
        const localSignature = require('bs58').encode(tx.signature);
        s.pending.signature = localSignature; save(stateFile(id), s);
        // Persist signature BEFORE transport: timeouts remain pending, never silently re-send.
        try { await connection.sendRawTransaction(tx.serialize(), { skipPreflight: false, maxRetries: 0 }); } catch (e) { throw new Error(`PENDING: ${localSignature}; broadcast outcome requires reconciliation (${e.message})`); }
        try { await reconcile(id); } catch (e) { if (!e.message.startsWith('PENDING:')) throw e; }
        return await view(id);
      }
      if (route === '/api/execute') {
        const { s, summary, onchain } = await current(id);
        if (onchain.status !== 'Funded' || s.pending?.signature || summary.tests.verifier) throw new Error('Funded order without completed verification required');
        if (BigInt(s.terms.deadline) <= BigInt(Math.floor(Date.now() / 1000))) throw new Error('Deadline expired');
        let result;
        if (summary.patch) result = await delivery('verify', nativeRoot(id));
        else {
          const proposal = await propose(body.mode);
          result = await delivery('execute', nativeRoot(id), { patch: proposal.patch, proposal: proposal.evidence });
        }
        if (result.verification_decision !== 'VERIFIED') return await view(id);
        return await submitDelivery(id);
      }
      if (route === '/api/decision') {
        const { s, onchain } = await current(id);
        if (onchain.status !== 'Delivered' || s.pending?.signature) throw new Error('Finalized Delivered order required');
        return await delivery('prepare', nativeRoot(id), { decision: body.decision });
      }
      if (route === '/api/commit') {
        const { s, onchain } = await current(id);
        if (onchain.status !== 'Delivered' || s.pending?.signature) throw new Error('Finalized Delivered order required');
        await delivery('commit', nativeRoot(id), { draft_id: body.draft_id, signature: body.signature });
        return await view(id);
      }
      throw new Error('Unknown API route');
    } finally { locks.delete(id); }
  }
  async function view(id) {
    const { s, summary, onchain } = await current(id);
    return { id, delivery: summary, chain: onchain, settlement_status: settlementLabel(onchain.status, s.transactions || []), worker: summary.proposal?.payload.proposal || null, transactions: s.transactions, pending: s.pending ? { kind: s.pending.kind, signature: s.pending.signature || null } : null };
  }
  const server = http.createServer(async (req, res) => {
    try {
      if (![`localhost:${port}`, `127.0.0.1:${port}`].includes(req.headers.host)) throw new Error('Invalid host');
      const route = req.url;
      if (route?.startsWith('/api/')) {
        guardRequest(req, port, token);
        if (req.method !== 'POST' || req.headers['content-type'] !== 'application/json') throw new Error('JSON POST required');
        let data = ''; for await (const chunk of req) { data += chunk; if (data.length > 200000) throw new Error('Request too large'); }
        const result = await dispatch(route, JSON.parse(data));
        res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }); res.end(JSON.stringify(result)); return;
      }
      const files = { '/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css' };
      let data, mime;
      if (route === '/solana.js') { data = fs.readFileSync(path.join(ROOT, 'node_modules/@solana/web3.js/lib/index.iife.min.js')); mime = 'application/javascript'; }
      else if (files[route]) { data = fs.readFileSync(path.join(__dirname, 'public', files[route]), 'utf8'); mime = route === '/' ? 'text/html' : route.endsWith('.css') ? 'text/css' : 'application/javascript'; if (route === '/') data = data.replace('__LOCAL_TOKEN__', token); }
      else { res.writeHead(404); res.end('Not found'); return; }
      res.writeHead(200, { 'content-type': mime, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff', 'content-security-policy': "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'" }); res.end(data);
    } catch (e) { res.writeHead(400, { 'content-type': 'application/json', 'cache-control': 'no-store' }); res.end(JSON.stringify({ error: e.message })); }
  });
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  console.log(`OWP delivery review: http://127.0.0.1:${port} (${network}; test tokens only)`);
  return server;
}
module.exports = { start, delivery };
if (require.main === module) start().catch(e => { console.error(e.message); process.exitCode = 1; });
