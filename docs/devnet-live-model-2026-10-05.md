# First observed live-model Devnet delivery

Verified at **2026-10-05 03:05:54 Asia/Shanghai** (`2026-10-04T19:05:54.020Z`). This is a new case, not a relabelled reference run.

## Observed outcome

One actual `deepseek-flash` API invocation proposed a replacement for the frozen `src/app.py` arithmetic-mean task. The application constructed the canonical patch locally, applied it through native OWP, ran immutable Docker tests, froze the signed operator attribution with the delivery, obtained exact-byte acceptance from the isolated software test customer, and finalized/reconciled Devnet escrow release.

- API response ID: `eacf71fc-4c17-4266-8ef5-9eab1c4883e8`; requested/returned model: `deepseek-flash`; finish reason: `stop`.
- Provider-reported usage: 194 prompt + 154 completion = 348 total tokens (127 completion tokens reported as reasoning). This is usage metadata, not a financial billing reconciliation.
- Native test execution: `succeeded`, exit code 0. Clean Docker rerun: **3 passed**, plus one expected read-only pytest cache warning. Actual native result bytes/counts/hashes remain in the frozen evidence; clean rerun plaintext is separately labelled.
- Native conclusion: **VERIFIED**; customer decision: **ACCEPTED**; reconciled onchain status: **SETTLED**.
- Released exactly **1 DemoUSD** (1,000,000 raw units, 6 decimals); vault balance **0**. Provider cumulative balance is 3 DemoUSD after three deliveries; it is not this run's transfer amount.
- Follow-up native reload verified the frozen bundle, signed proposal, response-to-patch mapping, tests and acceptance. The API credential was checked for absence in this run's raw evidence and frozen bundle.

The model's change was `return sum(values) / len(values)`, replacing the incorrect `return sum(values)`. The model did not edit tests, execute tools directly, sign acceptance or choose settlement. The task and acceptance conditions remain a deliberately small fixture.

## Public commitments

Case: `321573cd9667c51e186627e14add76a0`.
Customer: `7duv2Nv6EvQWk3g6PNHUJ2hMM6APBhmnEam4uMm2Afcg` — app-operator-generated software test wallet.
Program: `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk` on Solana Devnet.
Genesis: `EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG`.
Mint: `6MvanYas3fgdGwF2hY4QjQuTnjvH8phFkRmupwF9hJ4u` — isolated DemoUSD, not USDC or real money.

| Commitment | SHA-256 |
| --- | --- |
| Work order | `4ece5910d96860983ad2ef0f48975f7ac1991339fa699a5ba12f7652b58f40fe` |
| Frozen delivery bundle | `88976ae4090f00aade453e7aa22610841a60ad53b28f1e05aac957a542f2b702` |
| Customer acceptance | `485829500d2e39317ece60dba7bdb24b994af39d4ce602a25d4e91a0d627944b` |
| Patch | `f914bdb19219e4f5c588bfdacab1d2f03475cd1ee30914749d36babc7da13bf3` |
| Exact API request body | `e5b0d1c72c021d89b1fe1471ac9f0cf25e5ea14e584ed557c1e763d474d8a1a5` |
| Exact API response body | `c353dcf552acd8baaa877d884298583517c35120f2181fcfa50ada1871600b72` |

All three transactions finalized and reconciled:

- [Fund](https://explorer.solana.com/tx/2ibfaJLtgnRKcWXCBeNKSLbiMHjhfFMCS8t1ZdP6b7EWYv6URfUHXkSPL4PiBdym6Bj5o8UnrxLH19XczBD5AXfD?cluster=devnet)
- [Submit verified delivery](https://explorer.solana.com/tx/3yMUT9myDipN4V6nFyFTZYud18c7eFrGimy8c371hK4d7GRpwQQYMBYDu53gsi1EdnstFrxtoS5anxGcwn8kh7Rr?cluster=devnet)
- [Release](https://explorer.solana.com/tx/5i3PdfEPzCAyVPsphHNQuYXDNWatdDL5ipV73kbnSvSjFWCRvFJvkoMHvXmbJaiUKKCLHnsYpRLfdQqJfSmCqLQw?cluster=devnet)

Raw local evidence: `.tools/devnet-delivery-321573cd9667c51e186627e14add76a0-evidence.json` (ignored, separate from prior runs). Native frozen bundle: `.tools/delivery-sessions/321573cd9667c51e186627e14add76a0/delivery-bundle.json`. Private test keys are not part of this document or bundle.

## Verification and limits

Fresh checks in this run: **16 Node tests passed**, **2 proposal-evidence Python tests passed**, native frozen-session reload passed, and the full live Devnet test client exited 0. The earlier full 81-test Docker/Python result remains recorded in [step 3 verification](verification-step-3.md); it was not rerun in this live-call checkpoint.

The model/API shape follows [official DeepSeek JSON mode guidance](https://api-docs.deepseek.com/guides/json_mode/). Model-call attribution is signed by the application operator, **not by DeepSeek**; provider response ID/usage are not independent attestations. This run was observed locally with real HTTP service access and real Devnet transactions, not a trustless proof of API invocation or task quality.

All noncustomer roles remain app-owned, and this customer is also an isolated software test identity. No independent customer adoption, browser Phantom approval, production payments, model autonomy, mainnet use, public release or contest submission is established. Actual browser-wallet signatures/cancellation and presentation remain outstanding.

The project-local `.env` is now mode 0600 and Git-ignored. The local server was restarted to load it; it does not hot-reload credentials. No credential content was printed or added to documents. No upstream OWP source, global DSH profile or global proxy configuration was changed.
