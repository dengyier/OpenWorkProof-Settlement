const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createHash, randomBytes } = require('node:crypto');
const { Connection, Keypair, PublicKey, SystemProgram, Transaction, TransactionInstruction } = require('@solana/web3.js');
const { TOKEN_PROGRAM_ID, createMint, getOrCreateAssociatedTokenAccount, mintTo, getAccount } = require('@solana/spl-token');

const rpc = process.env.SETTLEMENT_TEST_RPC || 'http://127.0.0.1:18899';
const url = new URL(rpc);
if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname)) {
  throw new Error('Escrow tests must use a loopback local validator, never a public network');
}
const connection = new Connection(rpc, 'confirmed');
const PROGRAM = new PublicKey('2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk');
const amount = 1_000_000n;
const hash = () => randomBytes(32);
const discriminator = name => createHash('sha256').update(`global:${name}`).digest().subarray(0, 8);
const number = (n, signed = false) => { const b = Buffer.alloc(8); signed ? b.writeBigInt64LE(BigInt(n)) : b.writeBigUInt64LE(BigInt(n)); return b; };
const meta = (pubkey, isSigner = false, isWritable = false) => ({ pubkey, isSigner, isWritable });
const instruction = (name, keys, args = []) => new TransactionInstruction({ programId: PROGRAM, keys, data: Buffer.concat([discriminator(name), ...args]) });
async function send(ix, payer, signers = []) {
  const required = new Set(ix.keys.filter(k => k.isSigner).map(k => k.pubkey.toBase58()));
  required.add(payer.publicKey.toBase58());
  const unique = new Map([payer, ...signers].filter(k => required.has(k.publicKey.toBase58())).map(k => [k.publicKey.toBase58(), k]));
  const block = await connection.getLatestBlockhash();
  const transaction = new Transaction({ feePayer: payer.publicKey, ...block }).add(ix);
  transaction.sign(...unique.values());
  const signature = await connection.sendRawTransaction(transaction.serialize(), { preflightCommitment: 'confirmed' });
  const confirmation = await connection.confirmTransaction({ signature, ...block }, 'confirmed');
  if (confirmation.value.err) {
    const recorded = await connection.getTransaction(signature, { commitment: 'confirmed', maxSupportedTransactionVersion: 0 });
    const error = new Error(`Transaction ${signature} failed: ${JSON.stringify(confirmation.value.err)}`);
    error.logs = recorded?.meta?.logMessages;
    throw error;
  }
  return signature;
}
async function airdrop(key) {
  const signature = await connection.requestAirdrop(key.publicKey, 2_000_000_000);
  const block = await connection.getLatestBlockhash();
  await connection.confirmTransaction({ signature, ...block }, 'confirmed');
}
async function fixture(options = {}) {
  const customer = Keypair.generate(), provider = Keypair.generate(), verifier = Keypair.generate(), outsider = Keypair.generate();
  await airdrop(customer);
  await send(SystemProgram.transfer({ fromPubkey: customer.publicKey, toPubkey: outsider.publicKey, lamports: 10_000_000 }), customer);
  const mint = await createMint(connection, customer, customer.publicKey, null, 6);
  const source = (await getOrCreateAssociatedTokenAccount(connection, customer, mint, customer.publicKey)).address;
  const destination = (await getOrCreateAssociatedTokenAccount(connection, customer, mint, provider.publicKey)).address;
  const wrongDestination = (await getOrCreateAssociatedTokenAccount(connection, customer, mint, outsider.publicKey)).address;
  await mintTo(connection, customer, mint, source, customer, amount * 5n);
  const job = hash(), work = hash(), bundle = hash(), acceptance = hash();
  const [order] = PublicKey.findProgramAddressSync([Buffer.from('order'), customer.publicKey.toBuffer(), job], PROGRAM);
  const [vault] = PublicKey.findProgramAddressSync([Buffer.from('vault'), order.toBuffer()], PROGRAM);
  const clock = await connection.getBlockTime(await connection.getSlot());
  assert.notEqual(clock, null);
  const deadline = BigInt(clock + (options.deadlineOffset ?? 3600));
  return { customer, provider, verifier, outsider, mint, source, destination, wrongDestination, job, work, bundle, acceptance, order, vault, deadline };
}
function fund(c, overrides = {}) {
  return instruction('fund_order', [meta(c.customer.publicKey, true, true), meta(c.order, false, true), meta(c.vault, false, true), meta(c.mint), meta(c.source, false, true), meta(TOKEN_PROGRAM_ID), meta(SystemProgram.programId)],
    [overrides.job || c.job, overrides.work || c.work, (overrides.provider || c.provider.publicKey).toBuffer(), (overrides.verifier || c.verifier.publicKey).toBuffer(), number(overrides.amount ?? amount), number(overrides.deadline ?? c.deadline, true)]);
}
function submit(c, signer = c.provider) {
  return instruction('submit_delivery', [meta(signer.publicKey, true), meta(c.order, false, true)], [c.bundle]);
}
function release(c, options = {}) {
  return instruction('accept_and_release', [meta(c.customer.publicKey, !options.missingCustomer), meta((options.verifier || c.verifier).publicKey, !options.missingVerifier), meta(c.order, false, true), meta(c.vault, false, true), meta(c.mint), meta(options.destination || c.destination, false, true), meta(TOKEN_PROGRAM_ID)], [options.work || c.work, options.bundle || c.bundle, options.acceptance || c.acceptance]);
}
function refund(c, mutual = false, options = {}) {
  return instruction(mutual ? 'refund_mutual' : 'refund_expired', [meta(c.customer.publicKey, true), meta(c.provider.publicKey, mutual && !options.missingProvider), meta(c.order, false, true), meta(c.vault, false, true), meta(c.mint), meta(options.destination || c.source, false, true), meta(TOKEN_PROGRAM_ID)]);
}
const balance = async address => (await getAccount(connection, address)).amount;
async function state(c) {
  const account = await connection.getAccountInfo(c.order);
  assert(account);
  assert.equal(account.owner.toBase58(), PROGRAM.toBase58());
  return account.data[280]; // Account discriminator + 8 pubkeys/hashes + amount + deadline.
}
function assertChainError(error, code) {
  assert(error.logs?.some(line => line.startsWith(`Program ${PROGRAM.toBase58()} invoke`)), `Expected target program invocation, not a client/RPC failure: ${error.message}`);
  assert(error.logs.some(line => line.includes('failed: custom program error')), `Expected onchain program error: ${error.message}`);
  if (code) assert(error.logs.some(line => line.includes(`Error Code: ${code}`)), `Expected ${code}: ${error.logs.join('\n')}`);
  return true;
}
const chainReject = (promise, code) => assert.rejects(promise, error => assertChainError(error, code));
async function rejectsWithoutTransfer(c, ix, signers = [], payer = c.customer, code) {
  const before = await balance(c.vault), providerBefore = await balance(c.destination);
  await chainReject(send(ix, payer, signers), code);
  assert.equal(await balance(c.vault), before);
  assert.equal(await balance(c.destination), providerBefore);
}

test('customer deposit, immutable delivery and dual authorization transfer the exact frozen amount', async () => {
  const c = await fixture();
  await send(fund(c), c.customer);
  assert.equal(await balance(c.vault), amount);
  assert.equal(await balance(c.source), amount * 4n);
  assert.equal(await state(c), 0);
  await send(submit(c), c.customer, [c.provider]);
  assert.equal(await state(c), 1);
  await send(release(c), c.customer, [c.verifier]);
  assert.equal(await state(c), 3);
  assert.equal(await balance(c.vault), 0n);
  assert.equal(await balance(c.destination), amount);
  await rejectsWithoutTransfer(c, release(c), [c.verifier]);
  await rejectsWithoutTransfer(c, refund(c, true), [c.provider]);
});

test('release fails closed for missing/wrong authorities, wrong hashes and substituted token account', async () => {
  const c = await fixture();
  await send(fund(c), c.customer);
  await rejectsWithoutTransfer(c, release(c), [c.verifier]); // Not delivered.
  await chainReject(send(submit(c, c.outsider), c.customer, [c.outsider]), 'ConstraintHasOne');
  await send(submit(c), c.customer, [c.provider]);
  await chainReject(send(submit(c), c.customer, [c.provider]), 'InvalidState');
  for (const options of [{ missingVerifier: true }, { missingCustomer: true }, { verifier: c.outsider }, { work: hash() }, { bundle: hash() }, { acceptance: Buffer.alloc(32) }, { destination: c.wrongDestination }]) {
    await rejectsWithoutTransfer(c, release(c, options), [c.verifier, c.outsider], options.missingCustomer ? c.outsider : c.customer);
    assert.equal(await state(c), 1);
  }
  await send(release(c), c.customer, [c.verifier]);
  assert.equal(await balance(c.destination), amount);
});

test('rejection blocks release; refund requires provider consent and cannot replay', async () => {
  const c = await fixture();
  await send(fund(c), c.customer);
  await send(submit(c), c.customer, [c.provider]);
  await send(instruction('reject_delivery', [meta(c.customer.publicKey, true), meta(c.order, false, true)]), c.customer);
  assert.equal(await state(c), 2);
  await rejectsWithoutTransfer(c, release(c), [c.verifier]);
  await rejectsWithoutTransfer(c, refund(c));
  await rejectsWithoutTransfer(c, refund(c, true, { missingProvider: true }));
  await rejectsWithoutTransfer(c, refund(c, true, { destination: c.wrongDestination }), [c.provider]);
  await send(refund(c, true), c.customer, [c.provider]);
  assert.equal(await state(c), 4);
  assert.equal(await balance(c.source), amount * 5n);
  await rejectsWithoutTransfer(c, refund(c, true), [c.provider]);
});

test('delivered order may mutually cancel without automatically awarding either party', async () => {
  const c = await fixture();
  await send(fund(c), c.customer);
  await send(submit(c), c.customer, [c.provider]);
  await rejectsWithoutTransfer(c, refund(c));
  await send(refund(c, true), c.customer, [c.provider]);
  assert.equal(await state(c), 4);
});

test('invalid funding leaves no order or vault', async () => {
  for (const overrides of [{ amount: 0n }, { job: Buffer.alloc(32) }, { work: Buffer.alloc(32) }, { deadline: 1n }, { provider: PublicKey.default }, { verifier: PublicKey.default }, { amount: amount * 6n }]) {
    const c = await fixture();
    // The zero job must use the matching zero-job PDA, reaching our explicit digest check.
    if (overrides.job) {
      c.order = PublicKey.findProgramAddressSync([Buffer.from('order'), c.customer.publicKey.toBuffer(), overrides.job], PROGRAM)[0];
      c.vault = PublicKey.findProgramAddressSync([Buffer.from('vault'), c.order.toBuffer()], PROGRAM)[0];
    }
    const before = await balance(c.source);
    await chainReject(send(fund(c, overrides), c.customer));
    assert.equal(await connection.getAccountInfo(c.order), null);
    assert.equal(await connection.getAccountInfo(c.vault), null);
    assert.equal(await balance(c.source), before);
  }
  const c = await fixture();
  for (const overrides of [{ verifier: c.provider.publicKey }, { verifier: c.customer.publicKey }, { provider: c.customer.publicKey }]) {
    await chainReject(send(fund(c, overrides), c.customer), 'InvalidRoles');
  }
  assert.equal(await connection.getAccountInfo(c.order), null);
});

test('an undelivered expired order refunds once; early refunds are rejected', async () => {
  const c = await fixture({ deadlineOffset: 8 });
  await send(fund(c), c.customer);
  await rejectsWithoutTransfer(c, refund(c));
  // Wait for validator chain time, not workstation wall clock.
  const limit = Date.now() + 30_000;
  while (BigInt((await connection.getBlockTime(await connection.getSlot())) || 0) < c.deadline) {
    if (Date.now() > limit) throw new Error('Local validator clock did not advance');
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  await chainReject(send(submit(c), c.customer, [c.provider]), 'Expired');
  await send(refund(c), c.customer);
  assert.equal(await state(c), 4);
  assert.equal(await balance(c.source), amount * 5n);
  await rejectsWithoutTransfer(c, refund(c));
});

test('substituted funding accounts and token accounts fail without deposits', async () => {
  const c = await fixture();
  for (const [index, publicKey] of [[1, Keypair.generate().publicKey], [2, Keypair.generate().publicKey], [4, c.wrongDestination]]) {
    const ix = fund(c);
    ix.keys[index] = meta(publicKey, false, true);
    await chainReject(send(ix, c.customer));
    assert.equal(await connection.getAccountInfo(c.order), null);
    assert.equal(await connection.getAccountInfo(c.vault), null);
    assert.equal(await balance(c.source), amount * 5n);
  }
  await send(fund(c), c.customer);
  const zeroBundle = submit(c);
  zeroBundle.data = Buffer.concat([discriminator('submit_delivery'), Buffer.alloc(32)]);
  await rejectsWithoutTransfer(c, zeroBundle, [c.provider], c.customer, 'InvalidDigest');
  await send(submit(c), c.customer, [c.provider]);
  const otherMint = await createMint(connection, c.customer, c.customer.publicKey, null, 6);
  for (const [index, publicKey, signer] of [[0, c.outsider.publicKey, true], [3, c.source, false], [4, otherMint, false]]) {
    const ix = release(c);
    ix.keys[index] = meta(publicKey, signer, index === 3);
    await rejectsWithoutTransfer(c, ix, [c.outsider, c.verifier]);
  }
});

test('expired Delivered and Disputed orders still prohibit unilateral refunds', async () => {
  const c = await fixture({ deadlineOffset: 8 });
  await send(fund(c), c.customer);
  await send(submit(c), c.customer, [c.provider]);
  const limit = Date.now() + 30_000;
  while (BigInt((await connection.getBlockTime(await connection.getSlot())) || 0) < c.deadline) {
    if (Date.now() > limit) throw new Error('Local validator clock did not advance');
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  await rejectsWithoutTransfer(c, refund(c), [], c.customer, 'InvalidState');
  await send(instruction('reject_delivery', [meta(c.customer.publicKey, true), meta(c.order, false, true)]), c.customer);
  await rejectsWithoutTransfer(c, refund(c), [], c.customer, 'InvalidState');
});

test('competing delivery hashes commit once; release versus refund has exactly one winner', async () => {
  const c = await fixture();
  await send(fund(c), c.customer);
  const otherBundle = hash(), second = submit(c);
  second.data = Buffer.concat([discriminator('submit_delivery'), otherBundle]);
  const submissions = await Promise.allSettled([send(submit(c), c.customer, [c.provider]), send(second, c.customer, [c.provider])]);
  assert.equal(submissions.filter(r => r.status === 'fulfilled').length, 1);
  submissions.filter(r => r.status === 'rejected').forEach(r => assertChainError(r.reason, 'InvalidState'));
  const committed = (await connection.getAccountInfo(c.order)).data.subarray(200, 232);
  const winningBundle = submissions[0].status === 'fulfilled' ? c.bundle : otherBundle;
  assert(committed.equals(winningBundle));
  c.bundle = committed;
  const terminal = await Promise.allSettled([send(release(c), c.customer, [c.verifier]), send(refund(c, true), c.customer, [c.provider])]);
  assert.equal(terminal.filter(r => r.status === 'fulfilled').length, 1);
  terminal.filter(r => r.status === 'rejected').forEach(r => assertChainError(r.reason, 'InvalidState'));
  const terminalState = await state(c);
  assert([3, 4].includes(terminalState));
  assert.equal(await balance(c.vault), 0n);
  assert.equal((await balance(c.source)) + (await balance(c.destination)), amount * 5n);
  assert.equal(await balance(c.destination), terminalState === 3 ? amount : 0n);
});
