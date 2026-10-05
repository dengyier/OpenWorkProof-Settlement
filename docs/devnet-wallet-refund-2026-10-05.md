# Actual Phantom cancellation, account-change and refund checks

Date: 2026-10-05, Asia/Shanghai. This record is separate from the earlier accepted/settled live-model delivery.

## Scope and current checkpoint

This is a human-controlled Phantom wallet, a local application and Solana Devnet test tokens only. The customer private key, seed phrase and password are not read or supplied to the application. This case uses the labelled reference patch, not a new paid model invocation. Noncustomer roles remain app-owned; mutual cancellation is the app-owned provider's disclosed consent policy, not arbitration or independent provider approval.

- Case: `f97ebf41851968618472a7ec1a265b0c`.
- Customer: `5kvYUz9h8Zhdvvd4iSaXWV8iDxapN7X2YUxsZJrapSJH`.
- Program: `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk`.
- RPC genesis independently checked: `EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG` (Devnet).
- Mint: `6MvanYas3fgdGwF2hY4QjQuTnjvH8phFkRmupwF9hJ4u` (six-decimal DemoUSD; not USDC or money).
- Frozen amount: 1,000,000 raw units, or 1 DemoUSD.
- Order: `6nGAmxqAzUij9gnPS4nN6pVC534gfu9S5zD2mfA1PnTu`.
- Vault: `Atoks8n5jyJP581ZLoV2w3uu1dgd8eGtKvdZ1HaesKxv`.
- Job: `6b3af3512394bf41ad44185a64fa55f32601f50b0241395874e81347be8090d8`.
- Work-order digest: `141ee1e39447517d0cbc428be9e4711622d8cc566bd78c75aa88ccd3c19ecb79`.
- Frozen bundle: `d486dce4860f2be0a548a7b71ee6384e759a8c129390cb5c7199fcd0f4fb777d`.

Final verified checkpoint: **VERIFIED / REJECTED / REFUNDED**. The original customer received the exact 1 DemoUSD refund; the vault is empty and the provider received nothing from this case. Acceptance cancellation, between-prompt account switching, signed rejection, dispute and mutual refund are checked.

## Expired funding request was reconciled, not replayed

Phantom was initially locked; the human unlocked it. The first funding request was approved after its blockhash expired. The node returned `Blockhash not found`. The application persisted signature `54Tk9a76uLUejnZttoATEdwzgT793T4SxSnwxNfoAztjDLjuRK8wY7RU4xdoWZdBgXFy9hRLsjTQTfprKrU3345a` as uncertain before transport, without automatically retrying it.

Independent RPC checks found no signature status in historical search and no order account; finalized height 494728387 exceeded last-valid height 494727976 by more than the application's safety margin. The customer's balance remained 16,413,760 lamports. The existing refresh/reconciliation path retained an `expired without finalized inclusion` record and cleared pending. A new transaction with a fresh blockhash was then requested and separately approved by the human. This is not two successful deposits.

## Funding and verified delivery

- [Funding](https://explorer.solana.com/tx/iiEDeG9vWgbRSekC8LpG9APXXUvqE85zdb3n5xiEHnpEfEKEZ4aoM6hN4rjM4oXiCZLTwRwvbPSooweh5srENWe?cluster=devnet) finalized; its exact deposit was independently reconciled against transaction token-balance deltas.
- Reference-patch execution ran through native OWP protection and actual immutable Docker verification; the application reported VERIFIED.
- [Submit delivery](https://explorer.solana.com/tx/2Seat2KMmuTZGrr9NZsU2dic693vFQQopwxsgDbPs4LvvQBm7KsRE9wa6xDR5RhyJR2JfuYAZNWehvNJyGes8Qat?cluster=devnet) finalized and reconciled by the application.
- Independent RPC snapshot confirmed Delivered, zero onchain acceptance digest, vault 1,000,000 raw units, provider cumulative 4,000,000 raw units and customer token balance zero after funding.

## Actual acceptance-message cancellation

The actual Phantom `Sign Message` popup was observed for `127.0.0.1:3188`, with signing domain `openworkproof/acceptance-receipt/v0.1`. The human clicked **Cancel**, not Confirm. The application displayed `User rejected the request.`

Fresh native reload and independent RPC checks confirmed:

- Native state: `awaiting_human`; customer decision and acceptance digest absent.
- No `customer-decision.json` terminal receipt exists for this case.
- The uncommitted acceptance request remains available; cancellation is not a signed rejection.
- Chain state remains Delivered, vault 1,000,000 raw units and provider 4,000,000 raw units.
- No release transaction and no pending chain transaction exist.
- Direct application negative checks refused release (`Accepted native delivery and Delivered chain order required`) and unilateral expired refund (`Undelivered expired order required`). These API refusals are not additional onchain failed transactions.

## Fresh automated checks

- `npm run test:app`: **18 passed**, including client cancellation/account guards and refund instruction bindings.
- `.venv/bin/python -m pytest tests/test_wallet_signing.py -q`: **61 passed**.
- `npm run test:local`: SBF build succeeded; **9 local-validator escrow tests passed**, including rejection, consent, wrong destination, expiry and terminal/replay checks. These use generated software keys and a local validator, not Phantom or public Devnet.
- Existing Anchor cfg warnings and the SDK pure-JS bigint fallback remain. No dependency remediation or production-security claim is made.

## Actual between-prompt account switch

The human initially had one account, then personally created and selected an empty Account 2. No key/seed import or funding was requested. The Phantom sidebar showed Account 2 in Testnet Mode. The application reacted by reloading and clearing its connected-customer state; the old case was restored for review without enabled signing actions.

The human approved a connection of Account 2 to `127.0.0.1:3188`. The application then displayed a different connected address, `JDW7q…yeJBa`, while the frozen order still named `5kvYU…apSJH`. Native accessibility state explicitly marked acceptance, rejection, release, dispute and mutual cancellation buttons disabled. A visible click on the disabled acceptance button left the page unchanged and produced no signing popup. No new work order was created for Account 2.

This is a real account change **between wallet prompts**, not an actual in-flight account-change attack. The latter remains covered by the automated client test only.

## Signed rejection and finalized dispute

The human switched back to Account 1 and reconnected the original customer. The human confirmed the native rejection message in Phantom, with domain `openworkproof/acceptance-rejection-receipt/v0.1`. Fresh native reload verified `rejected / REJECTED` and terminal rejection digest `1f43130d5ea3df41a9874086d16ed538f82a33dc17d3841dc4a047bca5816fe6`. This is a rejection receipt, not an acceptance or payment authorization.

The human separately confirmed [recording the dispute](https://explorer.solana.com/tx/38VWpSwsPsUFibpwi3nyQFPCCjrDZuRDchCKPttqLmiEodeoCfdd2ys9LLaku6HVqq8dJvtxRxwKiNGfFrVYaiR2?cluster=devnet). The application reconciled its finalized inclusion; independent RPC confirmed Disputed with 1,000,000 raw units still in the vault. The release button was disabled and the application API refused release. A read-only Devnet simulation of the release instruction returned Anchor `InvalidState` (6003). That simulation used `sigVerify: false`: it checks the deployed state-machine guard, not real wallet signature verification, and did not broadcast a failed transaction.

## Finalized mutual refund and terminal guards

The application disclosed that its app-owned provider consents to cancellation and partially signed the refund. The human confirmed the separate Phantom transaction for Account 1, `127.0.0.1:3188`, showing `+1 Unknown` (the DemoUSD test mint) and a 0.00001 Devnet SOL network fee. This is not independent-provider adoption or arbitration.

[Refund transaction](https://explorer.solana.com/tx/3mEhJetATWn6MQwGNP2PfQsEMe6rtgyw4BhLhUisCPaS6sqc1nfZhDa9zZdQ2iFiUmNQxjMjvz72Rysv5TMjdN92?cluster=devnet) finalized at slot 507486524 with no transaction error and a fee of 10,000 lamports. The application recorded it as finalized and reconciled. Independent finalized RPC reads and transaction pre/post token balances confirmed:

| Check | Observed result |
| --- | --- |
| Native customer decision | REJECTED; no acceptance was substituted |
| Chain order | Refunded |
| Original customer's token delta | +1,000,000 raw units (+1 DemoUSD) |
| Vault token delta / final balance | -1,000,000 / 0 raw units |
| Provider cumulative balance | 4,000,000 raw units, unchanged from before this case |
| Onchain acceptance digest | Zero |
| Successful refund records / release records | One / zero |
| Pending transaction | None |

The UI showed **REFUNDED** and disabled acceptance, rejection, release, dispute and refund actions. Direct API requests for another mutual refund, release, rejection and expired refund all returned 400. Read-only deployed-program simulations for repeat mutual refund and release each returned `InvalidState` (6003); `sigVerify: false` means these are terminal-state guard checks, not newly signed transactions. Final snapshots after these checks were unchanged.

## Coverage boundaries

- Actual Phantom checks: expired funding recovery without duplicate deposit, acceptance-message cancellation, between-prompt account change, rejection, dispute and exact mutual refund.
- In-flight account switching and undelivered-expiry refund remain automated checks, not actual Phantom exercises in this run.
- The case used the reference patch and real Docker verification; it does not evidence another live-model call.
- Refund returns the escrowed token amount, not transaction fees or order/account rent. There is no unilateral post-delivery refund, independent dispute arbitration or real-payment claim.

No upstream source change, Git commit/push, mainnet operation or contest submission is part of this check.
