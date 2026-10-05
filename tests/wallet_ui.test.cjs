// Browser API test doubles exercise client guards, not a real Phantom signature.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
async function harness(signMessage, account = 'customer-A') {
  const elements = new Map(), calls = [], events = {};
  const element = id => { if (!elements.has(id)) elements.set(id, { textContent: '', options: [{}, {}], value: 'reference' }); return elements.get(id); };
  const record = { id: 'a'.repeat(32), delivery: { chain_terms: { customer: 'customer-A' }, acceptance_decision: null }, chain: { status: 'Delivered' }, settlement_status: 'Delivered', transactions: [] };
  const wallet = { isPhantom: true, isConnected: true, publicKey: { toBase58: () => account }, connect: async () => {}, on: (name, fn) => { events[name] = fn; }, signMessage };
  const context = { document: { getElementById: element, querySelector: () => ({ content: 'local-token' }) }, window: { phantom: { solana: wallet } }, location: { reload: () => {} }, localStorage: { getItem: () => record.id }, btoa: value => Buffer.from(value, 'binary').toString('base64'), atob: value => Buffer.from(value, 'base64').toString('binary'),
    fetch: async (url, options) => { calls.push({ url, body: JSON.parse(options.body) }); return { ok: true, json: async () => url.endsWith('/config') ? { genesis: 'test', network: 'devnet', model_configured: false } : url.endsWith('/decision') ? { draft_id: 'test-draft', message_base64: 'eA==' } : record }; }
  };
  vm.runInNewContext(fs.readFileSync(require.resolve('../app/public/app.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  await element('connect').onclick();
  return { elements, calls, events, wallet, record };
}
test('cancelling a wallet signature never commits acceptance', async () => {
  const h = await harness(async () => { throw new Error('User rejected signature'); });
  await h.elements.get('accept').onclick();
  assert(h.calls.some(call => call.url.endsWith('/decision')));
  assert(!h.calls.some(call => call.url.endsWith('/commit')));
  assert.match(h.elements.get('message').textContent, /User rejected/);
  assert.equal(h.elements.get('acceptance').textContent, 'Not signed');
});
test('account changes during wallet prompt cannot commit to another customer', async () => {
  let h;
  h = await harness(async () => { h.wallet.publicKey = { toBase58: () => 'customer-B' }; h.events.accountChanged(); return { signature: new Uint8Array(64) }; });
  await h.elements.get('accept').onclick();
  assert(!h.calls.some(call => call.url.endsWith('/commit')));
  assert.match(h.elements.get('message').textContent, /no longer matches/);
  assert.equal(h.elements.get('accept').disabled, true);
});
test('a connected wallet for a different work order cannot request a signature', async () => {
  const h = await harness(async () => { throw new Error('must not sign'); });
  h.wallet.publicKey = { toBase58: () => 'customer-B' };
  await h.elements.get('accept').onclick();
  assert(!h.calls.some(call => call.url.endsWith('/decision')));
  assert.equal(h.elements.get('accept').disabled, true);
});
test('a new account can create its own order while an old account case is restored', async () => {
  const h = await harness(async () => {}, 'customer-B');
  assert.equal(h.elements.get('create').disabled, false);
  assert.equal(h.elements.get('accept').disabled, true);
  await h.elements.get('create').onclick();
  assert(h.calls.some(call => call.url.endsWith('/create') && call.body.customer === 'customer-B'));
});
test('an applied patch can continue verification but completed tests cannot be rerun', async () => {
  const h = await harness(async () => {});
  h.record.chain.status = 'Funded';
  h.record.delivery.patch = { digest: 'a'.repeat(64) };
  h.record.delivery.tests = {};
  await h.elements.get('refresh').onclick();
  assert.equal(h.elements.get('execute').disabled, false);
  await h.elements.get('execute').onclick();
  assert(h.calls.some(call => call.url.endsWith('/execute')));
  h.record.delivery.tests.verifier = { exit_code: 1 };
  await h.elements.get('refresh').onclick();
  assert.equal(h.elements.get('execute').disabled, true);
});
