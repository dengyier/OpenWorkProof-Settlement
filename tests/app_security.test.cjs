const { test } = require('node:test');
const assert = require('node:assert/strict');
const { Keypair, Transaction } = require('@solana/web3.js');
const { validateSignedTransaction, validateCaseId, guardRequest, settlementLabel } = require('../app/security.cjs');
const chain = require('../app/chain.cjs');
test('wallet cannot replace prepared program, accounts, evidence or fee payer', () => {
  const customer = Keypair.generate(), verifier = Keypair.generate();
  const t = { customer: customer.publicKey.toBase58(), verifier: verifier.publicKey.toBase58(), provider: Keypair.generate().publicKey.toBase58(), mint: Keypair.generate().publicKey.toBase58(), job_id: 'a'.repeat(64), work_order_digest: 'b'.repeat(64), bundle_digest: 'c'.repeat(64), acceptance_digest: 'd'.repeat(64) };
  const tx = new Transaction({ feePayer: customer.publicKey, recentBlockhash: Keypair.generate().publicKey.toBase58() }).add(chain.releaseInstruction(t));
  tx.partialSign(verifier);
  const prepared = tx.serialize({ requireAllSignatures: false }).toString('base64');
  assert.throws(() => validateSignedTransaction(prepared, prepared), /signatures/);
  tx.partialSign(customer);
  assert(validateSignedTransaction(prepared, tx.serialize().toString('base64')).verifySignatures());
  tx.instructions[0].data[8] ^= 1;
  tx.partialSign(verifier, customer);
  assert.throws(() => validateSignedTransaction(prepared, tx.serialize().toString('base64')), /changed/);
});
test('observed Settled is not presented as settled before transfer reconciliation', () => {
  assert.equal(settlementLabel('Settled', []), 'PENDING reconciliation');
  assert.equal(settlementLabel('Settled', [{ kind: 'release', finalized: true, reconciled: false }]), 'PENDING reconciliation');
  assert.equal(settlementLabel('Settled', [{ kind: 'release', finalized: true, reconciled: true }]), 'SETTLED');
});
test('reject missing signatures, unsafe session paths and cross-origin requests', () => {
  assert.throws(() => validateCaseId('../private'), /case/);
  assert.equal(validateCaseId('a'.repeat(32)), 'a'.repeat(32));
  assert.throws(() => guardRequest({ headers: { host: 'evil.test', 'x-owp-token': 'abc' } }, 3188, 'abc'), /host/);
  assert.throws(() => guardRequest({ headers: { host: '127.0.0.1:3188', origin: 'https://evil.test', 'x-owp-token': 'abc' } }, 3188, 'abc'), /origin/);
  assert.throws(() => guardRequest({ headers: { host: '127.0.0.1:3188' } }, 3188, 'abc'), /token/);
  guardRequest({ headers: { host: '127.0.0.1:3188', origin: 'http://127.0.0.1:3188', 'x-owp-token': 'abc' } }, 3188, 'abc');
});
