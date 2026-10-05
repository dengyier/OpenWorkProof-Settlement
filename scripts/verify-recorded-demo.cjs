// Read-only verification of the two orders in the 2026-10-05 screen recording.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { VersionedTransaction } = require('@solana/web3.js');
const { getAccount } = require('@solana/spl-token');
const chain = require('../app/chain.cjs');
const { connection } = require('../app/rpc.cjs');
const { delivery } = require('../app/server.cjs');
const root = path.resolve(__dirname, '..');

async function main() {
  const rpc = connection('https://api.devnet.solana.com');
  const genesis = await chain.assertSafeNetwork(rpc, 'devnet');
  const cases = [];
  for (const [label, id, expected, kind] of [
    ['A', '2f88f90a80f237505ac44991c38c590c', 'Settled', 'release'],
    ['B', '4425870c502015b0714410c9a5a6e761', 'Refunded', 'mutual-refund'],
  ]) {
    const state = JSON.parse(fs.readFileSync(path.join(root, '.tools/delivery-sessions', id + '.json')));
    const summary = await delivery('summary', path.join(root, '.tools/delivery-sessions', id));
    const terms = { ...state.terms, job_id: summary.job_id, work_order_digest: summary.work_order_digest,
      bundle_digest: summary.bundle_digest, acceptance_digest: summary.acceptance_digest };
    assert.equal(state.pending, null);
    const statuses = (await rpc.getSignatureStatuses(state.transactions.map(t => t.signature),
      { searchTransactionHistory: true })).value;
    for (const status of statuses) {
      assert.equal(status?.confirmationStatus, 'finalized');
      assert.equal(status.err, null);
    }
    const snap = await chain.snapshot(rpc, terms);
    assert.equal(snap.status, expected);
    assert.equal(snap.vault_balance, '0');
    assert.equal(snap.bundle_digest, terms.bundle_digest);
    assert.equal(summary.verification_decision, 'VERIFIED');
    assert.equal(summary.acceptance_decision, label === 'A' ? 'ACCEPTED' : 'REJECTED');
    assert.equal(summary.proposal.payload.proposal.live_model, label === 'A');
    if (label === 'A') assert.equal(snap.acceptance_digest, terms.acceptance_digest);
    else assert.equal(snap.acceptance_digest, '0'.repeat(64));
    const terminal = state.transactions.find(t => t.kind === kind);
    assert(terminal?.finalized && terminal.reconciled);
    const record = await rpc.getTransaction(terminal.signature, { commitment: 'finalized', maxSupportedTransactionVersion: 0 });
    assert(record?.meta && !record.meta.err);
    chain.reconcileTransfer(record, terms, label === 'A' ? 'release' : 'refund');
    const keys = record.transaction.message.accountKeys || record.transaction.message.staticAccountKeys;
    const accounts = chain.accounts(terms);
    const balances = address => {
      const index = keys.findIndex(k => k.equals(address));
      const pre = record.meta.preTokenBalances.find(b => b.accountIndex === index);
      const post = record.meta.postTokenBalances.find(b => b.accountIndex === index);
      return { pre: pre?.uiTokenAmount.amount || '0', post: post?.uiTokenAmount.amount || '0' };
    };
    const recipient = balances(label === 'A' ? accounts.destination : accounts.source);
    const vault = balances(accounts.vault);
    assert.equal(BigInt(recipient.post) - BigInt(recipient.pre), 1000000n);
    assert.equal(BigInt(vault.post) - BigInt(vault.pre), -1000000n);
    const guards = [];
    if (label === 'B') {
      assert.equal(snap.provider_balance, '5000000');
      assert.equal((await getAccount(rpc, accounts.source, 'finalized')).amount.toString(), recipient.post);
      for (const [name, instruction] of [['repeat-refund', chain.refundInstruction(terms, true)],
        ['release-after-refund', chain.releaseInstruction(terms)]]) {
        const { tx } = await chain.transaction(rpc, instruction, terms.customer);
        const simulation = await rpc.simulateTransaction(new VersionedTransaction(tx.compileMessage()),
          { sigVerify: false, commitment: 'finalized' });
        assert(simulation.value.err);
        assert(simulation.value.logs.some(line => line.includes('Error Code: InvalidState')));
        guards.push({ name, method: 'readonly simulation, sigVerify=false, not broadcast',
          error: simulation.value.err, error_code: 'InvalidState' });
      }
    }
    const proposal = summary.proposal.payload.proposal;
    const mode = Object.fromEntries(['mode', 'live_model', 'model', 'patch_sha256', 'request_sha256', 'response_sha256']
      .filter(key => proposal[key] !== undefined).map(key => [key, proposal[key]]));
    cases.push({ label, id, mode, native_verification: summary.verification_decision,
      native_decision: summary.acceptance_decision, terms, onchain: snap,
      native_terminal_digest: summary.acceptance_digest, terminal_slot: record.slot,
      terminal_fee_lamports: record.meta.fee, terminal_transfer: { recipient, vault }, guards,
      transactions: state.transactions.map(t => ({ ...t,
        url: `https://explorer.solana.com/tx/${t.signature}?cluster=devnet` })) });
  }
  const evidence = { verified_at: new Date().toISOString(), network: 'devnet', genesis,
    token: 'DemoUSD', decimals: 6, original_screen_recording: true, published: false,
    trust_boundary: 'App-owned provider and attester; upgradeable program; test tokens only; no arbitration or real-payment claim.', cases };
  const output = path.join(root, 'outputs/contest-demo-en');
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, 'recorded-demo-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
  console.log(JSON.stringify(evidence, null, 2));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
