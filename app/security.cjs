const { Transaction } = require('@solana/web3.js');
function validateCaseId(id) {
  if (typeof id !== 'string' || !/^[a-f0-9]{32}$/.test(id)) throw new Error('Invalid case identifier');
  return id;
}
function guardRequest(req, port, token) {
  const hosts = [`127.0.0.1:${port}`, `localhost:${port}`];
  if (!hosts.includes(req.headers.host)) throw new Error('Invalid host');
  if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) throw new Error('Invalid origin');
  if (req.headers['x-owp-token'] !== token) throw new Error('Invalid local token');
}
function validateSignedTransaction(prepared, signed) {
  const original = Transaction.from(Buffer.from(prepared, 'base64'));
  const returned = Transaction.from(Buffer.from(signed, 'base64'));
  if (!original.serializeMessage().equals(returned.serializeMessage())) throw new Error('Prepared transaction changed');
  if (!returned.verifySignatures()) throw new Error('Transaction signatures missing or invalid');
  return returned;
}
function settlementLabel(observed, transactions) {
  if (!['Settled', 'Refunded'].includes(observed)) return observed;
  const kind = observed === 'Settled' ? 'release' : 'refund';
  return transactions.some(t => (t.kind === kind || kind === 'refund' && t.kind === 'mutual-refund') && t.finalized && t.reconciled) ? observed.toUpperCase() : 'PENDING reconciliation';
}
module.exports = { validateCaseId, guardRequest, validateSignedTransaction, settlementLabel };
