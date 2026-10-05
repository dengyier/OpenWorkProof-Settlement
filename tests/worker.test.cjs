const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { propose, replacementPatch, SOURCE } = require('../app/worker.cjs');
const rpc = require('../app/rpc.cjs');
const content = 'def average(values):\n    return sum(values) / len(values)\n';
const hash = raw => createHash('sha256').update(raw).digest('hex');
test('the adapter computes blob hashes and a canonical patch, not the model', () => {
  const patch = replacementPatch({ path: 'src/app.py', content });
  assert(patch.includes('200e736bc469f31a2b61fbab09914aed14f1215a..3d50b5909e0cedf57d5c51ce66a72091c8059782'));
  assert(patch.includes('@@ -1,2 +1,2 @@'));
  for (const invalid of [{ path: 'tests/test.py', content }, { path: 'src/app.py', content, extra: 'file' }, { path: 'src/app.py', content: 'x\r\n' }, { path: 'src/app.py', content: SOURCE }, { path: 'src/app.py', content: '' }]) assert.throws(() => replacementPatch(invalid), /proposal/);
});
test('live API response is preserved with hashes; invalid responses never fall back or retry', async () => {
  const previous = process.env.DEEPSEEK_API_KEY, original = rpc.fetchWithProxy;
  process.env.DEEPSEEK_API_KEY = 'test-only-do-not-publish';
  let calls = 0, sent;
  const response = JSON.stringify({ id: 'test-response', model: 'deepseek-flash', choices: [{ finish_reason: 'stop', message: { content: JSON.stringify({ path: 'src/app.py', content }) } }] });
  rpc.fetchWithProxy = async (_url, options) => { calls++; sent = options.body; return { ok: true, text: async () => response }; };
  try {
    const result = await propose('deepseek');
    assert.equal(result.live_model, true); assert.equal(calls, 1);
    assert.equal(JSON.parse(sent).response_format.type, 'json_object');
    assert.equal(result.evidence.request_sha256, hash(sent));
    assert.equal(result.evidence.response_sha256, hash(response));
    assert.equal(result.evidence.patch_sha256, hash(result.patch));
    assert(!JSON.stringify(result.evidence).includes(process.env.DEEPSEEK_API_KEY));
    for (const data of [{ choices: [] }, { choices: [{ finish_reason: 'length', message: { content: '{}' } }] }, { choices: [{ finish_reason: 'stop', message: { content: '' } }] }, { choices: [{ finish_reason: 'stop', message: { content: JSON.stringify({ path: 'elsewhere', content }) } }] }]) {
      rpc.fetchWithProxy = async () => { calls++; return { ok: true, text: async () => JSON.stringify(data) }; };
      const before = calls;
      await assert.rejects(propose('deepseek'), /Model|proposal/); assert.equal(calls, before + 1);
    }
    rpc.fetchWithProxy = async () => ({ ok: false, status: 402 });
    await assert.rejects(propose('deepseek'), /HTTP 402/);
  } finally {
    rpc.fetchWithProxy = original;
    if (previous === undefined) delete process.env.DEEPSEEK_API_KEY; else process.env.DEEPSEEK_API_KEY = previous;
  }
});
