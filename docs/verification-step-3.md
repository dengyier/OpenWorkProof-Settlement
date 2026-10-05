# Step 3 verification — 2026-10-05 (Asia/Shanghai)

## Implemented and observed

- JSON-only single-file DeepSeek proposal adapter; local Git blob hashes and full replacement patch generation. No automatic model fallback or paid-call retry.
- Exact request/response body hashes, app-owned Developer proposal signature, optional frozen review snapshot field, and response-to-patch validation. Customer acceptance and chain delivery bind the same bundle digest.
- Old snapshots retain their hash and remain readable: the previously settled reference case loaded in the updated browser, with separate VERIFIED / ACCEPTED / SETTLED states.
- Cancelled signatures, wrong accounts and an account change during a prompt cannot commit customer acceptance in browser-code tests. A new account can create its own order while the previous customer's saved case is displayed.
- HTTP confirmation ignores nonfinal fork errors and waits for finalized status.
- Project-local ignored `.env` support added; no user/global DSH or proxy configuration modified. No upstream OWP files edited, commit, push, release or contest submission performed.

## Fresh verification results

- `npm run test:app`: **16 passed**, zero failures. Wallet and model API doubles are explicitly labelled tests, not real provider/browser evidence.
- Full Python suite with immutable verifier/helper Docker image references: **81 passed in 67.27 seconds**, zero failures. Includes real native OWP Docker execution, proposal tampering/deletion rejection, successful proposal acceptance and incorrect proposal REFUTED.
- `.venv/bin/python -m pip check`: no broken requirements.
- Node syntax checks for server, worker and Devnet test client; Python bridge compilation passed.
- Playwright inspected the live review desk at `http://127.0.0.1:3188/`. No Phantom extension is available in this automation browser; Connect reports the installation requirement and does not fabricate a signature. Local screenshot: `output/playwright/step3-review-2026-10-05.png` (ignored).
- Independent read-only review found one account-switch/Create issue; regression test reproduced it, fix passed review. No remaining important findings in the reviewed slice. This is not a security certification.

## Fresh Devnet reference delivery

Recorded at **2026-10-05 02:59:00 Asia/Shanghai** (raw timestamp `2026-10-04T18:59:00.689Z`).

Case: `e7af2dc036b32fcf428afa1f315fd99c`.
Customer: `CCyYWiTV9s8PnntqKAaMLf8fxSV9QbNQcNyxhx6Su3Vf` — isolated software test wallet, not an independent customer or Phantom signature.
Program: `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk` (unchanged Devnet program).

| Commitment | SHA-256 |
| --- | --- |
| Native work order | `07144f359657cc7d03624d4c3deeb96aec95fa8f113a2f9bd628eaf5967cbf13` |
| Frozen bundle including signed reference attribution | `7b077c198449c07b9f3b07f14b03f7f886e2400cd5fae1d56eb08d595352162e` |
| Customer acceptance | `2f4e5eb2a5c8b7ff7646ee617e1b802754bbb7954ff36f889ace6a42dc8db436` |
| Applied reference patch | `388bbf662088945a0f1af5c57e94afad97d444b6a2b22f60154afb058586c97e` |

Transactions each finalized and token/account state reconciled:

- [Fund](https://explorer.solana.com/tx/3koU5wXechU6BoPrtmFTtWSSSK7cNaXCpDqrb3Nyfm3o5agquyjc5gP2decjtR9KehyQg5bqwyi6qnuibMD78KGg?cluster=devnet)
- [Submit delivery](https://explorer.solana.com/tx/4yeTE7XgTTJ4TRCv6GeLA4AQc1X9Mp8sNgrK5odR3wPRAducGgbu14YQZtwUMUQJvND2BnmsM4MdLon8PQXAqmrp?cluster=devnet)
- [Release](https://explorer.solana.com/tx/3LqEWCyrzc4rVpvEakECh9CsUvBSpy3MDM4zHk5pX9YSp8G9EsdpQUHkZVgcd4K49tJzYxJG5W3Ybjjzi4tE26UW?cluster=devnet)

Released amount: **1,000,000 raw units = 1 DemoUSD**, vault balance **0**. Provider cumulative balance after this second prototype delivery: 2,000,000 raw units, not the single-transfer amount. Test token only, not USDC or real payment.

Raw local evidence is retained without overwriting the earlier run at `.tools/devnet-delivery-e7af2dc036b32fcf428afa1f315fd99c-evidence.json`; private test keys remain ignored and separate. Proposal mode is explicitly `reference`, `live_model: false`.

## Remaining gates

At the earlier reference-run checkpoint above no project-root `.env` or process API key was available, so no actual DeepSeek call had yet been observed. **Update:** after the user configured the key locally, a new live-model case completed at 2026-10-05 03:05:54 Asia/Shanghai; see the separate [live-model verification record](devnet-live-model-2026-10-05.md). Do not reinterpret the older reference run as a live-model run. The model is still a proposal generator for one frozen task, not an autonomous tool-using agent.

For a separately authorized software-test live run after restarting the server with a valid key:

```sh
OWP_ALLOW_DEVNET_TEST=1 OWP_WORKER_MODE=deepseek npm run test:devnet
```

This explicitly spends isolated Devnet test fees/tokens and uses a generated software customer to test acceptance; it does not demonstrate human browser approval. If a transaction outcome is unknown, reconcile the existing case with `OWP_RESUME_CASE=<case-id>` instead of creating/funding another case. Never relabel a reference case as a model run. Evidence is per-case; a second export of an already exported case refuses to overwrite its original evidence file.

Real Phantom signature/cancellation tests and contest packaging/presentation remain separate next steps. Prior dependency audit alerts, local-only runtime image provenance, operator-controlled verification/upgrade authority, dispute limitations and nonproduction status still apply. No mainnet or personal-wallet operation is performed.
