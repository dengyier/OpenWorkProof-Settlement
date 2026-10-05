const { test } = require('node:test');
const assert = require('node:assert/strict');
const { isReadRpc } = require('../app/rpc.cjs');
const { propose } = require('../app/worker.cjs');
test('only read-only RPC can retry; transaction send and paid model requests cannot', () => {
  assert(isReadRpc({ body: JSON.stringify({ method: 'getSignatureStatuses' }) }));
  assert(!isReadRpc({ body: JSON.stringify({ method: 'sendTransaction' }) }));
  assert(!isReadRpc({ body: JSON.stringify({ model: 'deepseek-flash' }) }));
});
test('reference proposal is labelled; missing live key does not simulate an LLM', async () => {
  const reference = await propose('reference');
  assert.equal(reference.live_model, false); assert(reference.patch.includes('index 200e736'));
  if (!process.env.DEEPSEEK_API_KEY) await assert.rejects(propose('deepseek'), /not configured/);
});
test('HTTP confirmation does not return a nonfinal error from a fork', async () => {
  const connection = require('../app/rpc.cjs').connection('http://127.0.0.1:18899');
  let calls = 0;
  connection.getSignatureStatuses = async () => ({ context: { slot: ++calls }, value: [calls === 1 ? { err: { InstructionError: [0, 'fork-error'] }, confirmationStatus: 'confirmed' } : { err: null, confirmationStatus: 'finalized' }] });
  const result = await connection.confirmTransaction('test-signature');
  assert.equal(calls, 2); assert.equal(result.value.err, null); assert.equal(result.context.slot, 2);
});
