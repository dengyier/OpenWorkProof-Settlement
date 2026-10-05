# Actual Phantom wallet delivery and Devnet settlement

**Outcome:** actual Phantom funding, native customer acceptance and final release completed; real release-transaction cancellation verified. Acceptance-message cancellation remains untested in Phantom and is not included in this success claim.

## Confirmed checkpoint

Observed locally in the Hypo Chrome profile on 2026-10-05, using the installed Phantom extension (`bfnaelmomeimhlpmgjnjophhpkkoljpa`). The human completed wallet initialization and the localhost connection approval. No customer private key, seed phrase or password was read by the application or verification tooling.

- Phantom Testnet Mode was enabled; the Solana Devnet checkbox was selected. Auto-Confirm on localhost remained off.
- Connected customer public key: `5kvYUz9h8Zhdvvd4iSaXWV8iDxapN7X2YUxsZJrapSJH`.
- New case: `287edefe1abe5162715eab319f05af35`. This is separate from earlier software-customer runs.
- RPC genesis was independently checked: `EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG` (Devnet).
- A project-owned isolated deployer supplied 20,000,000 lamports (0.02 Devnet SOL) for test fees. Finalized customer balance changed from 0 to 20,000,000 lamports.
- Fee provisioning transaction: [Devnet explorer](https://explorer.solana.com/tx/FKBS9dz26ogei1UEZrKPuT1pmLbALbkew541tCkgyq6tepVqmZ4bue8UvcvyHU77oFktioYEBHyiwvF27Vg8d9g?cluster=devnet).
- The frontend selected `Live DeepSeek proposal`; this selection does not itself establish a model invocation.

## First signing attempt and compatibility checkpoint

The Phantom confirmation window was observed for `127.0.0.1:3188`. The prepared transaction contains one `fund_order` instruction to program `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk`, with this customer as signer and fee payer. Frozen amount is 1,000,000 raw units of six-decimal DemoUSD mint `6MvanYas3fgdGwF2hY4QjQuTnjvH8phFkRmupwF9hJ4u` (1 test token).

Phantom displays this unregistered test token as `-1 Unknown` and estimates approximately 0.003571 SOL for account creation. These are test-network assets, not USDC or real-payment claims. A popup estimate is not a finalized transfer.

After the first confirmation window closed, the application displayed `Prepared transaction changed`. The exact-message guard rejected the returned transaction before broadcasting; fresh RPC inspection showed `NotFunded`, no broadcast signature and no finalized case transactions. The signed returned bytes were not retained, so the precise first-attempt instruction diff was not directly captured.

The original unsigned request had no compute-budget instructions. [Phantom's current developer documentation](https://docs.phantom.com/developer-powertools/solana-priority-fees) specifies automatic priority-fee insertion for such unsigned requests. This is the source-backed compatibility hypothesis, not a captured byte-level diff.

The builder now freezes a 200,000 CU limit and zero priority price before signing, retaining exact-message validation. The new regression test failed before the change (missing budget instructions), then passed; all **17 application Node tests passed**. It also verifies that changing the frozen priority price is still refused. Native bigint bindings are unavailable on this machine; the dependency reports its existing pure-JS fallback warning.

The scoped local server was restarted, the same Phantom account reconnected, and a fresh funding draft requested for the same case. The human confirmed this second request. The exact-message guard accepted it; the unsigned request no longer acquired incompatible wallet-side changes.

## Actual Phantom escrow funding confirmed

- [Fund transaction](https://explorer.solana.com/tx/3u7YcZVcTgPGSJoSUEZK8L8JizbsGWhcznvo1GTczBkVwPdtgaFH7yZRibNbnz9hnJGxPo8bCuvW7P5xFqwHFfMw?cluster=devnet) finalized and reconciled.
- Fresh independent RPC inspection confirmed the frozen customer, `Funded` status and vault balance of 1,000,000 raw DemoUSD units.
- Actual network fee: 5,000 lamports. The finalized transaction has three instructions: frozen compute limit, frozen zero priority price and the escrow instruction.
- Order: `BvrgQ5btW1bBbhkXqvPzEvAYY9wQshBW8buKB5aCMJGx`; vault: `FGhH6DCNxi8ufw3HuJi9WuacAXNfGkbc9udutBHDTrGW`.

A subsequent attempt to simulate the pending draft found `pending` already cleared because funding had finalized; no simulation was performed or claimed. The real finalized RPC transaction was inspected instead.

## Delayed human approval exposed verifier-grant timestamp defect

Actual model execution started from the browser in `Live DeepSeek proposal` mode. The real response proposed `return sum(values) / len(values)`, and native repository-read and patch receipts succeeded. Model: `deepseek-flash`; response ID: `ae5e572c-961d-4c93-869a-d34fa116f6fc`; reported usage: 194 prompt + 232 completion = 426 tokens. Attribution is app-operator signed, not model-provider signed.

Verification stopped when a new verifier grant was denied with `CAPABILITY_DENIED`. The adapter copied the manager's work-order creation timestamp into that new grant. Human interaction had taken approximately nine minutes; the pinned OWP child-issuance policy requires a candidate's issuance time within 300 seconds. The native ledger correctly retained this denied attempt; no verification or acceptance was invented.

The adapter now issues new verifier grants at the actual verification time, within the unchanged parent/work-order deadline. It can continue verification of an already applied patch before any effective verifier grant or completed test exists. It checks the saved patch against native evidence, preserves the denied receipt, does not reapply the patch, and does not invoke the paid model again. Already-started verifier execution is refused for inspection rather than blindly repeated.

Regression tests reproduced the delayed-grant denial and missing continuation path before the fix. The new frontend regression also failed before enabling continuation. After the changes, **18 application Node tests passed** and the full real-Docker Python suite passed: **83 tests in 76.39 seconds**. The first resumed-flow test iteration used a stale pre-reload test object for a message assertion; it was corrected to check the actual resumed object, without relaxing the production guard.

## Actual native verification and customer acceptance

The same case continued verification through the browser. Native execution succeeded with exit code 0; the separate clean Docker rerun reported **3 passed**, with the expected read-only pytest cache warning. Native reload verified the displayed patch, signed proposal, frozen bundle and acceptance. The ledger contains exactly one patch receipt and retains the one denied verifier-grant attempt.

- [Submit delivery](https://explorer.solana.com/tx/5ojgS5nVoVqGPLBe3njC78teop7AbULTYT2gMjP7RyRszxo4rTrTb8v9y4h3vXE6r1doZqyJLQ4NUdkAhvGN5sZq?cluster=devnet) finalized and reconciled; order status became `Delivered`.
- Work-order digest: `f065ceb079bd18b0d0a99d00f96839c51ea045dd96f60fd83bc30ffea8dc78db`.
- Frozen bundle digest: `0d2577703e05ff7dac801d1fc87251a4059362cb2b28e29db24dbbfb91abf472`.
- Acceptance digest: `6ce070dabf0213ac036be30e38b25d01a6960668d9c7a2850597773eea102796`.
- Chain terms digest: `ca3ccd4e5f2f138e6d40b17c9820ab5e7ffdfe83dd6d4219e6f1b9967e4a4db7`.
- Model response SHA-256: `916d27adf87d74c859bf4f089c200872732453019b63b9666d8c9a665f2ff33b`.

After `Sign acceptance` was requested from the connected Phantom client, a valid exact-byte native customer signature was received and committed; the frontend and native reload both showed `ACCEPTED`. No software customer was substituted. The acceptance popup closed before its accessibility tree was captured, so the evidence consists of the observed client flow plus native signature verification, not a retained popup screenshot.

The intended **acceptance-message cancellation** did not occur: acceptance was signed. It must not be presented as a passing real-Phantom cancellation test. Automated client cancellation tests are separate evidence.

## Actual transaction-signature cancellation

An initial UI attempt was interrupted by concurrent user interaction and created no backend request; it was not counted. After reacquiring Chrome, a real release-signature request was created. The user cancelled it; the frontend displayed `User rejected the request.`

Fresh backend and Devnet checks showed an unsigned release draft (no broadcast signature), no release transaction, exactly the prior fund/submit transactions, chain state `Delivered`, and vault balance 1,000,000 raw DemoUSD units. The provider still held its pre-release cumulative 3,000,000 raw units. Thus this is a real **transaction cancellation** check, not an acceptance-message cancellation check.

A fresh final release request was opened and the human confirmed it. The app showed `SETTLED`; fresh independent native reload and Devnet RPC checks confirmed the result.

## Finalized release and reconciled result

- [Release transaction](https://explorer.solana.com/tx/4SJy3g1DZCuPy5VqX9iE2Hzgn8a74GzqKhG8c7Ri7ijtnEwAshpFmm9Bw7uQNsaNSGQ5TDANJHDPkmh4twE8CJiG?cluster=devnet) finalized and reconciled. Fee: 10,000 lamports for two signatures.
- Exact release transfer: 1,000,000 raw DemoUSD units (1 test token); vault balance: **0**.
- Provider cumulative balance changed from 3,000,000 to 4,000,000 raw units. Four DemoUSD is the cumulative balance, not this case's release amount.
- Order status: `Settled`; application status: `SETTLED`; pending transaction: none. All three case transactions finalized and reconciled.
- The onchain work-order, frozen-bundle and acceptance digests matched native evidence. Native release authorization was independently reloaded and checked after settlement.

## Limits and remaining checks

This is a local, bounded fixture with a real browser wallet and real Devnet transactions, not an independent customer adoption or real-payment claim. All noncustomer roles remain app-owned; the trusted application attester checks native evidence semantics. The program remains upgradeable and the runtime images remain local-only. Existing dependency audit findings are unchanged.

Acceptance-message cancellation was covered by automated client guards but not actually cancelled in this Phantom run. Account-switch behavior was also only covered by automated tests, not separately exercised with the human wallet. No mainnet assets, customer private keys, upstream source changes, Git commit/push, public release or contest submission were involved.
