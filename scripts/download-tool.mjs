// Fetch a public release artifact in bounded ranges and verify its published digest.
// This avoids slow single-connection downloads; it never installs or executes it.
import { spawn } from 'node:child_process';
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const [url, destination, sizeText, digest] = process.argv.slice(2);
const size = Number(sizeText);
if (!['github.com', 'static.rust-lang.org'].includes(new URL(url).hostname) || !url.startsWith('https://') || !destination?.startsWith('.tools/') ||
    !Number.isSafeInteger(size) || size <= 0 || !/^[a-f0-9]{64}$/.test(digest || '')) {
  throw new Error('Expected official GitHub URL, project .tools path, artifact size and SHA-256');
}
const pieces = Math.max(32, Math.ceil(size / 2_500_000)), chunk = Math.ceil(size / pieces), directory = `${destination}.parts`;
await mkdir(directory, { recursive: true });
await Promise.all(Array.from({ length: pieces }, async (_, i) => {
  const start = i * chunk, end = Math.min(size - 1, start + chunk - 1);
  if (start >= size) return;
  const file = `${directory}/${i}`;
  try {
    if ((await stat(file)).size === end - start + 1) return;
  } catch { /* Missing range: fetch it below. Whole-artifact digest is checked later. */ }
  await new Promise((resolve, reject) => {
    const child = spawn('curl', ['-fsSL', '--max-time', '150', '--retry', '2', '--retry-all-errors', '--range', `${start}-${end}`, '-o', file, url]);
    child.on('error', reject);
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Range ${i} failed: ${code}`)));
  });
  if ((await stat(file)).size !== end - start + 1) throw new Error(`Range ${i} was not respected`);
}));
const data = Buffer.concat(await Promise.all(Array.from({ length: pieces }, (_, i) => readFile(`${directory}/${i}`))));
if (data.length !== size || createHash('sha256').update(data).digest('hex') !== digest) throw new Error('Artifact checksum mismatch');
await writeFile(destination, data);
console.log(`Verified ${destination}: ${size} bytes, SHA-256 ${digest}`);
