const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="owp-token"]').content;
let wallet, customer, active, config, busy = false;
const base64 = bytes => btoa(String.fromCharCode(...bytes));
const bytes = encoded => Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
async function api(route, fields = {}) {
  const response = await fetch(`/api/${route}`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-owp-token': token }, body: JSON.stringify(fields) });
  const data = await response.json(); if (!response.ok) throw new Error(data.error); return data;
}
function requireCustomer(forNewOrder = false) {
  if (!wallet?.isConnected || wallet.publicKey?.toBase58() !== customer || (!forNewOrder && active && active.delivery.chain_terms.customer !== customer)) throw new Error('Connected account no longer matches this work order');
}
function render(data) {
  active = data;
  const d = data.delivery, c = data.chain;
  $('verification').textContent = d.verification_decision || 'Not verified';
  $('acceptance').textContent = d.acceptance_decision || 'Not signed';
  $('escrow').textContent = data.settlement_status;
  $('terms').textContent = JSON.stringify({ ...d.chain_terms, upgrade_authority: config.upgrade_authority, job_id: d.job_id, work_order_digest: d.work_order_digest, source_revision: d.source_revision }, null, 2);
  $('patch').textContent = d.patch?.text || 'Awaiting execution.';
  const proposal = d.proposal?.payload.proposal;
  $('tests').textContent = JSON.stringify({ tests: d.tests, proposal: proposal ? { mode: proposal.mode, requested_model: proposal.model || null, live_model: proposal.live_model, request_sha256: proposal.request_sha256 || null, response_sha256: proposal.response_sha256 || null, patch_sha256: proposal.patch_sha256, attribution: 'App-operator signed; bundled with delivery. Not a model-provider signature.' } : null, trust: d.trust_boundary }, null, 2);
  $('digests').textContent = JSON.stringify({ bundle_digest: d.bundle_digest, acceptance_digest: d.acceptance_digest, chain_terms_digest: d.chain_terms_digest, acceptance_request_expires_at: d.acceptance_request_expires_at }, null, 2);
  $('transactions').textContent = JSON.stringify({ finalized: data.transactions, pending: data.pending }, null, 2);
  buttons();
}
function buttons() {
  const walletConnected = !!customer && wallet?.isConnected && wallet.publicKey?.toBase58() === customer;
  const connected = walletConnected && (!active || active.delivery.chain_terms.customer === customer);
  const state = active?.chain.status, decision = active?.delivery.acceptance_decision;
  $('connect').disabled = busy;
  $('create').disabled = busy || !walletConnected;
  $('fund').disabled = busy || !connected || state !== 'NotFunded' || !!active?.pending?.signature;
  $('execute').disabled = busy || state !== 'Funded' || !!active?.delivery.tests?.verifier || !!active?.pending?.signature;
  $('execute').textContent = active?.delivery.patch ? 'Continue verification' : 'Execute protected work';
  for (const id of ['accept', 'reject']) $(id).disabled = busy || !connected || state !== 'Delivered' || !!decision || !!active?.pending?.signature;
  $('release').disabled = busy || !connected || state !== 'Delivered' || decision !== 'ACCEPTED' || !!active?.pending?.signature;
  $('dispute').disabled = busy || !connected || state !== 'Delivered' || decision !== 'REJECTED' || !!active?.pending?.signature;
  $('refresh').disabled = busy || !active;
  $('submit').disabled = busy || state !== 'Funded' || active?.delivery.verification_decision !== 'VERIFIED' || !!active?.pending?.signature;
  $('refund').disabled = busy || !connected || state !== 'Funded' || Number(active?.delivery.chain_terms.deadline) > Date.now() / 1000 || !!active?.pending?.signature;
  $('mutual-refund').disabled = busy || !connected || !['Delivered', 'Disputed'].includes(state) || !!active?.pending?.signature;
}
async function action(fn) {
  if (busy) return; busy = true; buttons(); $('message').textContent = 'Working — do not repeat the operation…';
  try { await fn(); $('message').textContent = 'Updated. Review evidence and finalized chain state before proceeding.'; }
  catch (e) { $('message').textContent = e.message; }
  finally { busy = false; buttons(); }
}
async function chainTransaction(kind) {
  requireCustomer();
  const prepared = await api('transaction', { id: active.id, kind });
  requireCustomer();
  const tx = solanaWeb3.Transaction.from(bytes(prepared.transaction));
  const signed = await wallet.signTransaction(tx);
  requireCustomer();
  render(await api('broadcast', { id: active.id, draft_id: prepared.draft_id, transaction: base64(signed.serialize()) }));
}
async function decision(value) {
  requireCustomer();
  const prepared = await api('decision', { id: active.id, decision: value });
  requireCustomer();
  const signed = await wallet.signMessage(bytes(prepared.message_base64), 'utf8');
  requireCustomer();
  render(await api('commit', { id: active.id, draft_id: prepared.draft_id, signature: base64(signed.signature) }));
}
$('connect').onclick = () => action(async () => {
  wallet = window.phantom?.solana;
  if (!wallet?.isPhantom) throw new Error('Install Phantom and select Devnet. No wallet private key is sent to this application.');
  await wallet.connect(); customer = wallet.publicKey.toBase58(); $('connect').textContent = `${customer.slice(0, 5)}…${customer.slice(-5)}`;
  wallet.on('accountChanged', () => { customer = null; active = null; location.reload(); });
  wallet.on('disconnect', () => { customer = null; active = null; location.reload(); });
});
$('create').onclick = () => action(async () => { requireCustomer(true); render(await api('create', { customer })); localStorage.setItem(`owp-${config.genesis}`, active.id); });
$('fund').onclick = () => action(() => chainTransaction('fund'));
$('execute').onclick = () => action(async () => render(await api('execute', { id: active.id, mode: $('worker').value })));
$('accept').onclick = () => action(() => decision('ACCEPTED'));
$('reject').onclick = () => action(() => decision('REJECTED'));
$('release').onclick = () => action(() => chainTransaction('release'));
$('dispute').onclick = () => action(() => chainTransaction('reject'));
$('refresh').onclick = () => action(async () => render(await api('view', { id: active.id })));
$('submit').onclick = () => action(async () => render(await api('submit', { id: active.id })));
$('refund').onclick = () => action(() => chainTransaction('refund'));
$('mutual-refund').onclick = () => action(() => chainTransaction('mutual-refund'));
action(async () => { config = await api('config'); $('network').textContent = `${config.network.toUpperCase()} · TEST TOKENS`; if (!config.model_configured) $('worker').options[1].disabled = true; const id = localStorage.getItem(`owp-${config.genesis}`); if (id) render(await api('view', { id })); });
