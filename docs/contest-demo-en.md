# OpenWorkProof Settlement — English product demo

Prepared and recorded: October 5, 2026 (Asia/Shanghai). Final runtime: **2:47.93**, hard limit: **3:00**.

**Production status:** [local final MP4](../outputs/contest-demo-en/openworkproof-settlement-demo-en.mp4), English stock neural narration and aligned subtitles are complete. Actual recording uses two new cases, `2f88f90a80f237505ac44991c38c590c` and `4425870c502015b0714410c9a5a6e761`. See the [recording verification](contest-demo-recording-2026-10-05.md) and [recorded-case evidence](../outputs/contest-demo-en/recorded-demo-evidence.json). The [YouTube upload](https://youtu.be/iY_NE8bBbyI) is unlisted and saved in the contest draft; final contest submission has not occurred.

## Audience and takeaway

For judges who do not know OWP: a customer buys a bounded agent task, reviews evidence, and explicitly decides whether to release escrow. A passing test is not customer acceptance, and acceptance is not a token transfer.

Opening title: **OpenWorkProof Settlement**

Subtitle: **Review the work. Authorize the transfer.**

Persistent corner label: **Solana Devnet · DemoUSD test tokens · Local prototype**

Use two clearly identified work orders, not one order with two contradictory outcomes:

```text
Order A · Live DeepSeek proposal
Funded → Delivered → Customer ACCEPTED → Separate release → SETTLED

Order B · Reference patch, no LLM
Funded → Delivered → Customer REJECTED → Disputed
                                      → Customer + provider consent → REFUNDED
```

The first audience is coding-agent service providers and small software teams purchasing bounded fixes. This is the intended use case, not evidence of customers or revenue.

## Rules checked for this preparation

The [official FAQ](https://colosseum.com/hackathon) was checked on October 5, 2026. The authenticated submission form, checked later that day, specifies a product demo of up to three minutes and a **separate pitch video of up to two minutes**, overriding the FAQ's generic two-to-three-minute presentation guidance. It accepts YouTube, Loom or Vimeo links. This package covers the product demonstration, not the separate founder/business presentation. Relevant prior development must be disclosed.

## Storyboard and recording timeline

The storyboard timings below preserve the original preparation target. The final measured section timings are in `outputs/contest-demo-en/edit-decision-list.json`. Use `contest-demo-narration-en.txt` for the spoken copy, in paragraph order.

The narration contains 322 words in eight paragraphs. Measured final audio is 167.928 seconds; final video is approximately 167.93 seconds, including readable pauses.

| Time | Picture / action | Essential visible text | Narration paragraph |
| --- | --- | --- | --- |
| 0:00–0:15 | Product title, then the actual review desk and bounded arithmetic task | Review the work. Authorize the transfer. / Devnet | 1 |
| 0:15–0:33 | Order A: frozen task, source revision, permitted `src/app.py`, immutable tests, customer/provider and 1 DemoUSD; funding confirmation/outcome | Order A · Live DeepSeek proposal / 1 DemoUSD | 2 |
| 0:33–0:56 | The real patch, execution receipts and Docker test output; submit-delivery outcome | `return sum(values) / len(values)` / VERIFIED | 3 |
| 0:56–1:15 | Customer reviews patch and evidence; acceptance-message signing; ACCEPTED, with no release yet | VERIFIED ≠ ACCEPTED ≠ SETTLED | 4 |
| 1:15–1:36 | Separate release transaction; SETTLED; Explorer balance changes | Provider +1 DemoUSD / Vault 0 / Finalized | 5 |
| 1:36–2:00 | Explicit cut to Order B; reference-patch attribution, passing tests, signed rejection, separately recorded dispute, disabled release | Order B · Reference patch — no LLM / REJECTED → Disputed | 6 |
| 2:00–2:23 | Provider-consent disclosure, separate customer refund confirmation, REFUNDED, Explorer token deltas | Customer +1 DemoUSD / Vault 0 / Provider unchanged | 7 |
| 2:23–2:45 | Trust-boundary card, then two terminal outcomes and evidence links | Trusted app attester / App-owned provider / No arbitration / Test tokens only | 8 |

### Recording choice: fresh execution or evidence walkthrough

**Recommended final footage:** record two fresh orders from start to finish using the actual application, then cut to the selected moments. Wallet confirmation must remain human-controlled. New orders will have new IDs, hashes, deadlines and transaction links; replace the manifest only after finalized reconciliation. Do not re-execute or refund the terminal orders below. A new live-model run may incur API usage; a reference run must keep its visible no-LLM label.

**Available without another transaction:** record a review of the existing terminal evidence and Explorer records. Label it **Recorded-run evidence walkthrough**. The current application restores the latest order and has no case-picker for switching between historical orders. Use source records/Explorer to review Order A; do not alter browser storage or manufacture intermediate UI states. This is less visually complete than fresh end-to-end footage, but honestly demonstrates already finalized results.

No original continuous screen recording of these earlier runs is available in this package. A recording made now of a historical record is not footage of the original approval. Do not fabricate wallet popups, fill in animation as live transaction footage, or cut different cases together without labels.

### Exact actions for fresh footage

Before creating a new order, confirm Phantom Testnet Mode / Solana Devnet, the displayed customer and the program/mint in frozen terms. Use only Devnet SOL and DemoUSD. Obtain enough test fees; do not transfer real SOL.

Order A:

1. `Create work order` → inspect `Frozen terms & identity`.
2. Select `Live DeepSeek proposal` → `Fund 1 DemoUSD` → human confirms funding → wait for finalized Funded.
3. `Execute protected work` → review patch, attribution and test evidence. If interrupted, inspect state first; `Continue verification` is not permission to repeat a paid model call or already-started verifier.
4. Use `Submit verified delivery` only if delivery is not already submitted. Wait for Delivered.
5. `Sign acceptance` → human signs the OWP acceptance message. Capture ACCEPTED while still Delivered.
6. `Authorize test-token release` → human confirms the separate transaction. Show SETTLED only after finalized token reconciliation.

Order B:

1. `Create work order` → select `Reference patch — no LLM` → fund a separate 1 DemoUSD escrow.
2. Execute and verify; submit delivery if necessary. Passing verification should be visible.
3. `Sign rejection` → human confirms the **rejection message**, not acceptance.
4. `Record dispute onchain` → human confirms the separate transaction → wait for Disputed. Show that release is disabled; do not spend fees attempting an unnecessary prohibited transfer.
5. Read the disclosed app-owned provider consent policy → `Request agreed cancellation` → human co-signs the refund.
6. Show REFUNDED only after finalized reconciliation, exact +1 DemoUSD to this order's customer, empty vault and unchanged provider balance.

For short wallet excerpts, keep the source, account, action and amount legible. Phantom may show the unregistered mint as `Unknown`; add **DemoUSD test mint — not USDC** next to that footage. For message signatures, show the relevant OWP domain and explain that no transfer occurs at that step.

## Existing evidence to display

Fresh checks on October 5 confirmed both terminal states, the native decisions, empty vaults, absent pending transactions and successful terminal transactions. Transaction pre/post token balances were reconciled, not inferred from a displayed signature.

| Evidence | Order A — accepted and settled | Order B — rejected and refunded |
| --- | --- | --- |
| Case ID | `287edefe1abe5162715eab319f05af35` | `f97ebf41851968618472a7ec1a265b0c` |
| Execution mode | Actual DeepSeek proposal, app-operator-signed attribution | Reference patch, no model invocation |
| Native decision | ACCEPTED | REJECTED |
| Finalized chain state | Settled | Refunded |
| Frozen amount | 1 DemoUSD | 1 DemoUSD |
| Terminal token movement | Vault −1; provider +1 DemoUSD | Vault −1; original customer +1 DemoUSD |
| Final vault | 0 | 0 |
| Terminal signature | [Release](https://explorer.solana.com/tx/4SJy3g1DZCuPy5VqX9iE2Hzgn8a74GzqKhG8c7Ri7ijtnEwAshpFmm9Bw7uQNsaNSGQ5TDANJHDPkmh4twE8CJiG?cluster=devnet) | [Refund](https://explorer.solana.com/tx/3mEhJetATWn6MQwGNP2PfQsEMe6rtgyw4BhLhUisCPaS6sqc1nfZhDa9zZdQ2iFiUmNQxjMjvz72Rysv5TMjdN92?cluster=devnet) |
| Detailed record | [Phantom settlement](devnet-phantom-2026-10-05.md) | [Wallet exceptions and refund](devnet-wallet-refund-2026-10-05.md) |

Order B also retained one expired funding attempt, which was **not included onchain**. A later fresh transaction funded the order once. Do not call the expired signature a successful transaction. The provider's cumulative balance of four DemoUSD is not this order's payout; use the per-transaction +1 or unchanged delta.

The machine-readable [preparation evidence manifest](contest-demo-evidence.json) describes earlier rehearsal cases, not the two new orders in the final recording. The [recorded-case evidence](../outputs/contest-demo-en/recorded-demo-evidence.json) contains the final recording's public addresses, commitments, verified token deltas and transaction links. Neither manifest contains keypairs or API credentials.

## English overlays

- **One task. Frozen scope. One test-token budget.**
- **Live model proposal · App-operator-signed attribution**
- **Tests passed. The customer still decides.**
- **Acceptance message ≠ release transaction**
- **SETTLED · Provider +1 DemoUSD · Vault 0**
- **Separate order · Reference patch — no LLM**
- **REJECTED · No automatic payout**
- **Disputed · Release blocked**
- **Mutual consent required after delivery**
- **REFUNDED · Customer +1 DemoUSD · Vault 0**
- **Trusted application attester · No automatic arbitration**
- **Pre-existing OWP Core + new settlement integration**

## Claims and limitations that must survive editing

The chain enforces identities, commitments, state and token transfers. The application attester checks OWP evidence semantics; the chain does not judge code quality. The provider and attester are app-owned in this demo, and the program retains a developer-controlled upgrade authority.

Rejection does not automatically refund a delivered order: the customer records the dispute, and the subsequent refund requires both customer and provider signatures. Without agreement, funds may remain locked. Refund does not return network fees or account rent. There is no independent arbitration, security-audit claim, production clearance, real-money payment, customer adoption or revenue claim.

OWP Core 1.4.0 predates the competition. The new work demonstrated here is its integration with the settlement program, review application, Phantom signing and finalized reconciliation. See [development disclosure](baseline-and-disclosure.md). The [public OWP repository](https://github.com/dengyier/OpenWorkProof) is the pre-existing protocol, **not a substitute link for the new settlement application's source**. Confirm a separate reviewable settlement source link before submitting.

## Recording and export checklist

- [ ] Choose and label fresh end-to-end footage or recorded-run evidence review.
- [ ] English narration and subtitles; retain the two order/mode labels.
- [ ] Keep text readable at 1080p; crop the application/Explorer rather than recording the whole desktop with unrelated email or tabs.
- [ ] Never show `.env`, keypair files, seed phrases, passwords, internal auth tokens or unrelated personal data.
- [ ] Wallet confirmations remain human-controlled; do not enable Auto-Confirm to shorten filming.
- [ ] Trim finality waiting with **Waiting for finality · time compressed**; keep any approvals and sequence honest.
- [ ] Prefer a calm, conversational English voice, about 135–145 words per minute. Say “Open Work Proof” and “demo U-S-D”; no dramatic sales delivery. Use only an authorized stock voice or the founder's own recording, not an unconsented voice clone.
- [ ] Synchronize subtitles to the actual finished audio, not these estimated storyboard times.
- [ ] Export MP4 (H.264/AAC), preferably 1920×1080, 30 fps; these are production defaults, not claimed mandatory official codecs.
- [ ] Measure duration ≤180 seconds, decode the full output, and inspect all key screens at final size.
- [ ] Verify that displayed transaction IDs, decisions, modes and deltas match the footage's actual orders.
- [ ] Verify the hosted link without login; do not submit a local file path or a placeholder URL.
- [ ] Complete the separate 2–3 minute presentation video and final portal checks before submission.

## Suggested video description

> OpenWorkProof Settlement: a Solana Devnet prototype connecting signed agent-work evidence and explicit customer decisions to test-token escrow. This demo shows two separate outcomes: accepted delivery followed by release, and rejected delivery followed by a dispute and mutually approved refund. DemoUSD is a test token, not USDC or a real payment. The application attester is trusted, noncustomer roles are app-owned, and no independent arbitration is provided. OpenWorkProof Core is pre-existing work; the settlement integration is disclosed separately.

Add the **actual exported video's** evidence/source links after recording. Do not describe an evidence walkthrough as a new live run.
