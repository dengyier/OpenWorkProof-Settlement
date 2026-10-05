// Explicit operator-owned software customer: tests real Devnet, not a browser wallet/adopter.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { Keypair, Transaction, SystemProgram } = require('@solana/web3.js');
const { connection } = require('../app/rpc.cjs');
const chain = require('../app/chain.cjs');
async function main() {
  if (process.env.OWP_ALLOW_DEVNET_TEST !== '1') throw new Error('Set OWP_ALLOW_DEVNET_TEST=1 to spend isolated Devnet test coins');
  const url = 'http://127.0.0.1:3188';
  const html = await (await fetch(url)).text();
  const token = /name="owp-token" content="([a-f0-9]+)"/.exec(html)?.[1];
  if (!token) throw new Error('Local application is not ready');
  const api = async (route, body = {}) => {
    const response = await fetch(`${url}/api/${route}`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-owp-token': token }, body: JSON.stringify(body) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error); return data;
  };
  const config = await api('config');
  assert.equal(config.network, 'devnet'); assert.equal(config.genesis, chain.DEVNET_GENESIS);
  const mode = process.env.OWP_WORKER_MODE || 'reference';
  if (!['reference', 'deepseek'].includes(mode)) throw new Error('OWP_WORKER_MODE must be reference or deepseek');
  if (mode === 'deepseek' && !config.model_configured) throw new Error('Configure the local model before creating or funding a live-model case');
  const rpc = connection(config.rpc); await chain.assertSafeNetwork(rpc, 'devnet');
  const payer = Keypair.fromSecretKey(Uint8Array.from(JSON.parse(fs.readFileSync(path.resolve(__dirname, '../.tools/settlement-private/deployer-keypair.json')))));
  let customer, active, seedSignature = null;
  const resume = process.env.OWP_RESUME_CASE;
  if (resume) {
    require('../app/security.cjs').validateCaseId(resume);
    const state = JSON.parse(fs.readFileSync(path.resolve(__dirname, `../.tools/delivery-sessions/${resume}.json`)));
    customer = Keypair.fromSecretKey(Uint8Array.from(JSON.parse(fs.readFileSync(path.resolve(__dirname, `../.tools/settlement-private/software-customer-${state.terms.customer}-keypair.json`)))));
    active = await api('view', { id: resume });
    if (active.delivery.patch && mode === 'deepseek' && active.worker?.mode !== 'deepseek') throw new Error('Cannot relabel an existing reference case as a live-model run');
    if (active.pending?.signature) { await chain.waitFinalized(rpc, active.pending.signature); active = await api('view', { id: resume }); }
  } else {
    customer = Keypair.generate();
    fs.writeFileSync(path.resolve(__dirname, `../.tools/settlement-private/software-customer-${customer.publicKey.toBase58()}-keypair.json`), JSON.stringify(Array.from(customer.secretKey)), { mode: 0o600, flag: 'wx' });
    const { tx } = await chain.transaction(rpc, SystemProgram.transfer({ fromPubkey: payer.publicKey, toPubkey: customer.publicKey, lamports: 20000000 }), payer.publicKey);
    tx.sign(payer); seedSignature = await rpc.sendRawTransaction(tx.serialize()); await chain.waitFinalized(rpc, seedSignature);
    active = await api('create', { customer: customer.publicKey.toBase58() });
  }
  const id = active.id;
  console.log(`Created software-customer case ${id}; customer key remains in ignored test-client storage.`);
  async function txAction(kind) {
    const prepared = await api('transaction', { id, kind });
    const signed = Transaction.from(Buffer.from(prepared.transaction, 'base64')); signed.partialSign(customer);
    active = await api('broadcast', { id, draft_id: prepared.draft_id, transaction: signed.serialize().toString('base64') });
    if (active.pending?.signature) await chain.waitFinalized(rpc, active.pending.signature);
    active = await api('view', { id });
  }
  if (active.chain.status === 'NotFunded') await txAction('fund');
  assert(['Funded', 'Delivered', 'Settled'].includes(active.chain.status));
  console.log('Funding finalized and exact deposit reconciled.');
  if (active.chain.status === 'Funded') {
    await assert.rejects(api('transaction', { id, kind: 'release' }), /Accepted/);
    active = await api(active.delivery.patch ? 'submit' : 'execute', { id, mode });
  }
  if (active.pending?.signature) await chain.waitFinalized(rpc, active.pending.signature);
  active = await api('view', { id });
  assert(['Delivered', 'Settled'].includes(active.chain.status)); assert.equal(active.delivery.verification_decision, 'VERIFIED');
  console.log('Native Docker verification and chain delivery finalized.');
  assert.equal(active.delivery.tests.verifier.exit_code, 0);
  const frozenBundle = active.delivery.bundle_digest;
  if (!active.delivery.acceptance_decision) {
    await assert.rejects(api('transaction', { id, kind: 'release' }), /Accepted/);
    const draft = await api('decision', { id, decision: 'ACCEPTED' });
  // Sign exact OWP bytes using this generated software test wallet outside the backend.
  const pkcs8 = Buffer.concat([Buffer.from('302e020100300506032b657004220420', 'hex'), Buffer.from(customer.secretKey.subarray(0, 32))]);
  const secret = crypto.createPrivateKey({ key: pkcs8, format: 'der', type: 'pkcs8' });
  const signature = crypto.sign(null, Buffer.from(draft.message_base64, 'base64'), secret).toString('base64');
  active = await api('commit', { id, draft_id: draft.draft_id, signature });
  console.log('Native exact-byte customer acceptance committed.');
  assert.equal(active.delivery.acceptance_decision, 'ACCEPTED'); assert.equal(active.delivery.bundle_digest, frozenBundle);
  await assert.rejects(api('commit', { id, draft_id: draft.draft_id, signature }), /stale|consumed/i);
  }
  const before = BigInt(active.chain.provider_balance);
  if (active.chain.status !== 'Settled') await txAction('release');
  assert.equal(active.chain.status, 'Settled'); assert.equal(active.chain.vault_balance, '0');
  assert.equal(active.settlement_status, 'SETTLED');
  if (active.transactions.filter(t => t.kind === 'release').length === 1 && before !== BigInt(active.chain.provider_balance)) assert.equal(BigInt(active.chain.provider_balance) - before, 1000000n);
  assert(active.transactions.every(t => t.finalized && t.reconciled));
  const released = active.transactions.find(t => t.kind === 'release');
  const releaseRecord = await chain.waitFinalized(rpc, released.signature);
  chain.reconcileTransfer(releaseRecord, { ...active.delivery.chain_terms, job_id: active.delivery.job_id, work_order_digest: active.delivery.work_order_digest }, 'release');
  await assert.rejects(api('transaction', { id, kind: 'release' }), /Accepted/);
  const record = { timestamp: new Date().toISOString(), network: config.network, genesis: config.genesis, program: config.program, mint: config.mint,
    customer: customer.publicKey.toBase58(), role_boundary: 'operator-generated software customer; not browser approval or an independent customer. Model attribution is app-operator signed, not provider signed.', worker: active.worker,
    job_id: active.delivery.job_id, work_order_digest: active.delivery.work_order_digest, bundle_digest: active.delivery.bundle_digest,
    acceptance_digest: active.delivery.acceptance_digest, native_tests: active.delivery.tests.verifier,
    chain: active.chain, transactions: active.transactions, seed_signature: seedSignature };
  // Generated public execution evidence only; no private keys or local auth token.
  const output = path.resolve(__dirname, `../.tools/devnet-delivery-${id}-evidence.json`);
  fs.writeFileSync(output, JSON.stringify(record, null, 2), { mode: 0o600, flag: 'wx' });
  console.log(JSON.stringify({ evidence: output, id, status: active.chain.status, transactions: active.transactions }, null, 2));
}
main().catch(e => { console.error(e.message); process.exitCode = 1; });
