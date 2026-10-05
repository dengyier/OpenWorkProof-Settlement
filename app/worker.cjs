// The reference proposal is explicitly a fixture, never a simulated model call.
const REFERENCE_PATCH = 'diff --git a/src/app.py b/src/app.py\nindex 200e736bc469f31a2b61fbab09914aed14f1215a..3d50b5909e0cedf57d5c51ce66a72091c8059782 100644\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,2 @@\n def average(values):\n-    return sum(values)\n+    return sum(values) / len(values)\n';
const { createHash } = require('node:crypto');
const SOURCE = 'def average(values):\n    return sum(values)\n';
const hash = raw => createHash('sha256').update(raw).digest('hex');
const blob = raw => createHash('sha1').update(`blob ${Buffer.byteLength(raw)}\0`).update(raw).digest('hex');
function replacementPatch(proposal) {
  if (!proposal || Object.keys(proposal).sort().join(',') !== 'content,path' || proposal.path !== 'src/app.py' || typeof proposal.content !== 'string' || !proposal.content.endsWith('\n') || /[\r\0]/.test(proposal.content) || Buffer.byteLength(proposal.content) > 8192 || proposal.content === SOURCE) throw new Error('Invalid bounded single-file proposal');
  const lines = proposal.content.slice(0, -1).split('\n');
  return `diff --git a/src/app.py b/src/app.py\nindex ${blob(SOURCE)}..${blob(proposal.content)} 100644\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,${lines.length} @@\n` + SOURCE.trimEnd().split('\n').map(line => `-${line}\n`).join('') + lines.map(line => `+${line}\n`).join('');
}
async function propose(mode) {
  if (mode === 'reference') return { patch: REFERENCE_PATCH, mode, model: null, live_model: false, evidence: { schema_version: 'owp-settlement-proposal/1', mode, live_model: false, patch_sha256: hash(REFERENCE_PATCH) } };
  if (mode !== 'deepseek') throw new Error('Select reference fixture or configured deepseek worker');
  if (!process.env.DEEPSEEK_API_KEY) throw new Error('DEEPSEEK_API_KEY is not configured locally; no live model call made');
  const model = process.env.OWP_MODEL || 'deepseek-flash';
  const requestBody = JSON.stringify({ model, temperature: 0, max_tokens: 1536, response_format: { type: 'json_object' }, messages: [
    { role: 'system', content: 'Return one json object only, with exactly the keys path and content. Example: {"path":"src/app.py","content":"complete replacement Python file with final newline"}. No markdown, other files, tools, diff or blob hashes. Fix arithmetic mean for nonempty arrays. The immutable original src/app.py is:\n' + SOURCE + '\nFrozen tests: average([2,4,6])=4, average([7])=7, average([-3,2])=-0.5. Tests cannot be changed. Keep the change minimal.' },
    { role: 'user', content: 'Propose the replacement file. The local adapter constructs the patch; protected execution and tests decide whether it is valid.' }
  ] });
  const response = await require('./rpc.cjs').fetchWithProxy('https://api.deepseek.com/chat/completions', {
    method: 'POST', signal: AbortSignal.timeout(60000), headers: { authorization: `Bearer ${process.env.DEEPSEEK_API_KEY}`, 'content-type': 'application/json' },
    body: requestBody, size: 131072, timeout: 60000
  });
  if (!response.ok) throw new Error(`Model service returned HTTP ${response.status}; no execution proof created`);
  const responseBody = await response.text();
  if (Buffer.byteLength(responseBody) > 131072) throw new Error('Model response exceeds evidence limit');
  let data, proposal;
  try {
    data = JSON.parse(responseBody);
    if (data.choices?.length !== 1 || data.choices[0].finish_reason !== 'stop' || typeof data.choices[0].message?.content !== 'string') throw new Error();
    proposal = JSON.parse(data.choices[0].message.content);
  } catch { throw new Error('Model response is empty, truncated or not a single completed json proposal'); }
  const patch = replacementPatch(proposal);
  return { patch, mode, model, live_model: true, evidence: { schema_version: 'owp-settlement-proposal/1', mode, model, live_model: true,
    patch_sha256: hash(patch), request_body: requestBody, response_body: responseBody, request_sha256: hash(requestBody), response_sha256: hash(responseBody) } };
}
module.exports = { propose, REFERENCE_PATCH, replacementPatch, SOURCE };
