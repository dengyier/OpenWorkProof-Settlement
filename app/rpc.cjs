const fetch = require('node-fetch');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { Connection } = require('@solana/web3.js');
const agents = new Map();
function isReadRpc(options) {
  try { return /^get|^isBlockhashValid$/.test(JSON.parse(options.body).method); } catch { return false; }
}
async function fetchWithProxy(url, options = {}) {
  const target = new URL(url);
  const proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
  if (proxy && !agents.has(proxy)) agents.set(proxy, new HttpsProxyAgent(proxy, { keepAlive: true, maxSockets: 4 }));
  const agent = target.protocol === 'https:' && !['127.0.0.1', 'localhost'].includes(target.hostname) && proxy ? agents.get(proxy) : undefined;
  const attempts = isReadRpc(options) ? 3 : 1;
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const response = await fetch(url, { ...options, agent, timeout: options.timeout ?? 15000 });
      if (response.status !== 429 || attempt === attempts - 1) return response;
      await response.text();
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    catch (e) { if (attempt === attempts - 1) throw e; await new Promise(resolve => setTimeout(resolve, (attempt + 1) * 500)); }
  }
}
function connection(rpc) {
  const result = new Connection(rpc, { commitment: 'finalized', fetch: fetchWithProxy, disableRetryOnRateLimit: true });
  // SPL setup helpers otherwise confirm over an unproxied WebSocket. Poll the same
  // public HTTP RPC instead; even a confirmed helper operation waits for finality.
  result.confirmTransaction = async strategy => {
    const signature = typeof strategy === 'string' ? strategy : strategy.signature;
    const deadline = Date.now() + 90000;
    while (Date.now() < deadline) {
      const status = await result.getSignatureStatuses([signature], { searchTransactionHistory: true });
      const value = status.value[0];
      if (value?.confirmationStatus === 'finalized') return { context: status.context, value: { err: value.err } };
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error(`PENDING: ${signature}; HTTP finality not observed, reconcile before retry`);
  };
  return result;
}
module.exports = { connection, fetchWithProxy, isReadRpc };
