const { createHash } = require('node:crypto');
const { PublicKey, Transaction, TransactionInstruction, SystemProgram, ComputeBudgetProgram } = require('@solana/web3.js');
const { TOKEN_PROGRAM_ID, getAssociatedTokenAddressSync, getAccount } = require('@solana/spl-token');

const PROGRAM_ID = '2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk';
const PROGRAM = new PublicKey(PROGRAM_ID);
const DEVNET_GENESIS = 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG';
const hash = s => createHash('sha256').update(s).digest();
const meta = (pubkey, isSigner = false, isWritable = false) => ({ pubkey: new PublicKey(pubkey), isSigner, isWritable });
function digest(hex) {
  if (typeof hex !== 'string' || !/^[0-9a-f]{64}$/.test(hex) || /^0+$/.test(hex)) throw new Error('Invalid nonzero evidence digest');
  return Buffer.from(hex, 'hex');
}
function integer(n, signed = false) {
  if (typeof n !== 'string' || !/^[0-9]+$/.test(n)) throw new Error('Expected integer string, not floating amount');
  const data = Buffer.alloc(8); signed ? data.writeBigInt64LE(BigInt(n)) : data.writeBigUInt64LE(BigInt(n)); return data;
}
function deriveOrder(customer, job) {
  const [order] = PublicKey.findProgramAddressSync([Buffer.from('order'), new PublicKey(customer).toBuffer(), digest(job)], PROGRAM);
  const [vault] = PublicKey.findProgramAddressSync([Buffer.from('vault'), order.toBuffer()], PROGRAM);
  return { order, vault };
}
function accounts(t) {
  const { order, vault } = deriveOrder(t.customer, t.job_id), mint = new PublicKey(t.mint);
  return { order, vault, mint, source: getAssociatedTokenAddressSync(mint, new PublicKey(t.customer)), destination: getAssociatedTokenAddressSync(mint, new PublicKey(t.provider)) };
}
function instruction(name, keys, args = []) {
  return new TransactionInstruction({ programId: PROGRAM, keys, data: Buffer.concat([hash(`global:${name}`).subarray(0, 8), ...args]) });
}
function fundInstruction(t) {
  const a = accounts(t);
  return instruction('fund_order', [meta(t.customer, true, true), meta(a.order, false, true), meta(a.vault, false, true), meta(a.mint), meta(a.source, false, true), meta(TOKEN_PROGRAM_ID), meta(SystemProgram.programId)],
    [digest(t.job_id), digest(t.work_order_digest), new PublicKey(t.provider).toBuffer(), new PublicKey(t.verifier).toBuffer(), integer(t.amount), integer(t.deadline, true)]);
}
function submitInstruction(t) {
  return instruction('submit_delivery', [meta(t.provider, true), meta(accounts(t).order, false, true)], [digest(t.bundle_digest)]);
}
function releaseInstruction(t) {
  const a = accounts(t);
  return instruction('accept_and_release', [meta(t.customer, true), meta(t.verifier, true), meta(a.order, false, true), meta(a.vault, false, true), meta(a.mint), meta(a.destination, false, true), meta(TOKEN_PROGRAM_ID)],
    [digest(t.work_order_digest), digest(t.bundle_digest), digest(t.acceptance_digest)]);
}
function rejectInstruction(t) {
  return instruction('reject_delivery', [meta(t.customer, true), meta(accounts(t).order, false, true)]);
}
function refundInstruction(t, mutual) {
  const a = accounts(t);
  return instruction(mutual ? 'refund_mutual' : 'refund_expired', [meta(t.customer, true), meta(t.provider, mutual), meta(a.order, false, true), meta(a.vault, false, true), meta(a.mint), meta(a.source, false, true), meta(TOKEN_PROGRAM_ID)]);
}
function decodeOrder(account) {
  if (!account?.owner.equals(PROGRAM)) throw new Error('Order account owner mismatch');
  const d = account.data;
  if (d.length !== 282 || !d.subarray(0, 8).equals(hash('account:Order').subarray(0, 8))) throw new Error('Order account size/discriminator mismatch');
  const states = ['Funded', 'Delivered', 'Disputed', 'Settled', 'Refunded'];
  if (!states[d[280]]) throw new Error('Unknown order state');
  const result = {};
  ['customer', 'provider', 'verifier', 'mint'].forEach((key, i) => { result[key] = new PublicKey(d.subarray(8 + i * 32, 40 + i * 32)).toBase58(); });
  ['job_id', 'work_order_digest', 'bundle_digest', 'acceptance_digest'].forEach((key, i) => { result[key] = d.subarray(136 + i * 32, 168 + i * 32).toString('hex'); });
  return { ...result, amount: d.readBigUInt64LE(264).toString(), deadline: d.readBigInt64LE(272).toString(), status: states[d[280]], bump: d[281] };
}
async function assertSafeNetwork(connection, network) {
  if (!['devnet', 'localnet'].includes(network)) throw new Error('Only devnet/localnet network is permitted');
  if (network === 'localnet') {
    const u = new URL(connection.rpcEndpoint);
    if (u.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(u.hostname)) throw new Error('Localnet must be loopback');
  }
  const genesis = await connection.getGenesisHash();
  if (['5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d', '4uhcVJyU9pJkvQyS88uRDiswHXSCkY3zQawwpjk2NsNY'].includes(genesis)) throw new Error('Mainnet/testnet genesis is forbidden');
  if ((network === 'devnet') !== (genesis === DEVNET_GENESIS)) throw new Error('Unexpected network genesis');
  return genesis;
}
async function snapshot(connection, t) {
  const a = accounts(t), account = await connection.getAccountInfo(a.order, 'finalized');
  if (!account) return { status: 'NotFunded', order: a.order.toBase58(), vault: a.vault.toBase58() };
  const order = decodeOrder(account);
  for (const field of ['customer', 'provider', 'verifier', 'mint', 'job_id', 'work_order_digest', 'amount', 'deadline']) {
    if (order[field] !== t[field]) throw new Error(`Frozen order mismatch: ${field}`);
  }
  const [vault, provider] = await Promise.all([getAccount(connection, a.vault, 'finalized'), getAccount(connection, a.destination, 'finalized')]);
  if (!vault.owner.equals(a.order) || !vault.mint.equals(a.mint) || !provider.owner.equals(new PublicKey(t.provider)) || !provider.mint.equals(a.mint)) throw new Error('Token ownership/mint mismatch');
  return { ...order, order: a.order.toBase58(), vault: a.vault.toBase58(), vault_balance: vault.amount.toString(), provider_balance: provider.amount.toString() };
}
async function transaction(connection, ix, payer) {
  const block = await connection.getLatestBlockhash('finalized');
  // Freeze Devnet fees before Phantom signing; automatic fee insertion would
  // change the exact message (and invalidate any existing attester signature).
  return { block, tx: new Transaction({ feePayer: new PublicKey(payer), ...block }).add(
    ComputeBudgetProgram.setComputeUnitLimit({ units: 200000 }),
    ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 0 }), ix) };
}
async function waitFinalized(connection, signature, timeoutMs = 90000) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    const status = (await connection.getSignatureStatuses([signature], { searchTransactionHistory: true })).value[0];
    if (status?.err && status.confirmationStatus === 'finalized') throw new Error(`Transaction failed: ${JSON.stringify(status.err)}`);
    if (status?.confirmationStatus === 'finalized') {
      const record = await connection.getTransaction(signature, { commitment: 'finalized', maxSupportedTransactionVersion: 0 });
      if (record && record.meta && !record.meta.err) return record;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`PENDING: transaction ${signature} not finalized; inspect before retry`);
}
function reconcileTransfer(record, t, kind) {
  const a = accounts(t), keys = record.transaction.message.accountKeys || record.transaction.message.staticAccountKeys;
  if (!keys.some(k => k.equals(PROGRAM))) throw new Error('Transaction does not invoke the configured program');
  const delta = address => {
    const index = keys.findIndex(k => k.equals(address));
    if (index < 0) throw new Error('Expected token account missing from transaction');
    const values = list => list?.find(b => b.accountIndex === index);
    const pre = values(record.meta.preTokenBalances), post = values(record.meta.postTokenBalances);
    if (pre && pre.mint !== t.mint || !post || post.mint !== t.mint) throw new Error('Transaction token mint mismatch');
    return BigInt(post.uiTokenAmount.amount) - BigInt(pre?.uiTokenAmount.amount || '0');
  };
  const amount = BigInt(t.amount);
  if (kind === 'fund' && (delta(a.vault) !== amount || delta(a.source) !== -amount)) throw new Error('Deposit balance delta mismatch');
  if (kind === 'release' && (delta(a.vault) !== -amount || delta(a.destination) !== amount)) throw new Error('Release balance delta mismatch');
  if (kind === 'refund' && (delta(a.vault) !== -amount || delta(a.source) !== amount)) throw new Error('Refund balance delta mismatch');
  return true;
}
module.exports = { PROGRAM_ID, DEVNET_GENESIS, deriveOrder, accounts, fundInstruction, submitInstruction, releaseInstruction, rejectInstruction, refundInstruction, decodeOrder, assertSafeNetwork, snapshot, transaction, waitFinalized, reconcileTransfer };
