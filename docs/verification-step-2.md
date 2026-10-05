# Step 2 verification — 2026-10-05

## Scope and evidence boundaries

Native OWP Core 1.4.0 is installed from unchanged commit `0dbc32b648f31343a5f9ccabf678f1e1075e60f1`. Native v0.1 WorkOrder, grants, protected repository read/patch, Docker test execution, CompositionReport, externally signed customer acceptance/rejection and offline bundle verification are used. The disposable average-function fixture is a real repository/code/test execution, not an autonomous-model claim. The reference proposal is explicitly labelled; a separately configured DeepSeek proposal adapter is present but not yet live-validated.

Native original stdio is retained as byte counts and hashes. Actual plaintext output is from a separately labelled clean Docker rerun using the same frozen test image. All noncustomer roles and both verifier environments share the application operator. No independent-adopter or independently operated verifier claim is made.

## Deployment

- Network: Solana Devnet; genesis `EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG` checked.
- Program: `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk`.
- Deployment transaction: `3amd9scJWCqJTLKvUZzyc76eEtDAKGPTVbL3dgtHpTS54UwndHp917DxJEtuXpPFLF1sUKiNMPqjj9jijeeNUfu2`.
- Finalized deployment slot: `507451479`; program size: `230312` bytes.
- Local SBF and downloaded onchain program SHA-256 both `b938389e3e85ee4fe51f28016a9939f277ded38a13277a65997bcb5f842d2f76`.
- Upgrade authority: isolated test deployer `F6kXvzWHErZMtS1K1qcisNPsEZCrrixRAVFRrc6nAT52`. The program is developer-upgradeable, not immutable.
- Official faucet supplied 2.5 **Devnet** SOL after the human completed Cloudflare/GitHub verification. No mainnet SOL or existing personal wallet was used.
- DemoUSD mint: `6MvanYas3fgdGwF2hY4QjQuTnjvH8phFkRmupwF9hJ4u`, six decimals, app-controlled mint authority, no freeze authority. This is not USDC or dollar value.

Explorer: [program](https://explorer.solana.com/address/2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk?cluster=devnet), [deployment](https://explorer.solana.com/tx/3amd9scJWCqJTLKvUZzyc76eEtDAKGPTVbL3dgtHpTS54UwndHp917DxJEtuXpPFLF1sUKiNMPqjj9jijeeNUfu2?cluster=devnet).

## Checks and recovery

The 9 local-validator escrow tests passed again after replacing the genesis fixture ID with the actual deployment keypair ID. Node checks cover account ownership/discriminator, exact dual-signer release, wallet message substitution, local host/origin/token/path guards, reconciliation-dependent terminal display, refund signers and no implicit model fallback. Native Docker regression tests cover failed/passing patch, acceptance/rejection, wrong key, replay/stale draft, work/job/terms/bundle/display metadata tampering and native-terminal crash recovery.

Broadcast signatures are saved before transport. Unknown outcomes remain pending. Finalized errors or historical non-inclusion after finalized blockheight exceeds the validity limit plus a 32-block buffer unlock explicit new preparation. A verified delivery can be resubmitted without rerunning its patch. Read-only RPC transport retries are bounded; transaction sends and paid model calls are never silently retried.

Native acceptance requests are valid for up to one hour, capped by WorkOrder deadline; cancelling a wallet prompt does not accept work. Expired requests are not reopened. The browser provides customer-only refund for expired undelivered work and provider/customer co-signed cancellation for delivered/disputed work. The app-owned demo provider explicitly consents to requested cancellation; this is not unilateral arbitration.

## Remaining gates

- Browser wallet: injected Phantom connect/signMessage/signTransaction is implemented. The automation browser has no Phantom extension; actual browser-wallet approval, cancellation and account-change behavior are not yet verified.
- Live model: no DEEPSEEK_API_KEY is present in the app process. Reference execution must not be called an autonomous LLM run. Configure the key locally, not in chat; the model adapter must pass native canonical-patch validation before producing evidence.
- Public RPC: transient TLS resets and HTTP 429 were observed. Unknown state is retained and queried; public RPC is not a production SLA.
- Runtime images are local immutable artifacts; base/helper provenance is separate from the Core pin and not a public reproducible image release. See bridge/delivery_flow_README.md and runtime/Dockerfile.
- Existing 9 npm audit findings (3 high/6 moderate), developer upgrade authority, local-only session service, role co-ownership, no independent security audit, no full transitive Python lock and no account-rent/surplus recovery remain prototype limitations.
- No public Git push, project release or contest submission was performed.

## Current Devnet evidence record

The resumed software-customer check completed with exit 0. It reloaded the same already funded case, verified native acceptance and its stable delivery digest, independently queried the finalized release record, checked the exact 1,000,000-base-unit transfer, and confirmed repeated release preparation is refused. It did not re-deposit or create another order while resolving transport failures.

Public, secret-free commitments and chain records are in [devnet-delivery-2026-10-05.json](devnet-delivery-2026-10-05.json). All three transaction records are finalized/reconciled, vault balance is 0, and provider balance is 1,000,000 base units (1 DemoUSD).

- [Customer funding](https://explorer.solana.com/tx/xppwGMewVuhiULT19cjJtoyuZ6s3tXBvfv3JNXbUpYMSXGAw21FbRuinq7sTL72Tffr7bAnwvk3JjJRk6yJZKWV?cluster=devnet)
- [Provider delivery](https://explorer.solana.com/tx/3e4pR6iCdUfg3xtaAWfoz2LdzUci88btm5UH1aefS1qDnk2XrsrZwsMyhovuwvSWsiDaFfa8fQjTXASNQzD8dfiV?cluster=devnet)
- [Customer + verifier release](https://explorer.solana.com/tx/rujxJzg5PQKu2GFcPzsbx4pjfFKezxymWTz6LiN4nGvzUH7s9MWjc75c9SUHQGpiVEeVbnGBa5kWJfLfBaxwcYF?cluster=devnet)

Final current checks: 77 Python tests passed in 59.31s (16 real Docker delivery tests + 61 signing checks); 9 app/client/RPC tests passed; `pip check` reported no broken requirements. The 9 local-validator escrow tests passed after the program-ID replacement. Browser smoke confirmed Devnet labeling, disabled live-model option without a key and an explicit missing-Phantom message. No browser signature was faked. Refund instruction construction is tested and the underlying program refund behavior is covered by local escrow tests; the new browser refund paths are not yet live-wallet tested.

An earlier failed provider-submit attempt used an unfunded provider fee account; it was not labelled a successful delivery. Isolated test identities and failed sessions remain in ignored storage; they are not commercial users. That earlier case's funded test-token order has not been refunded, and its first ephemeral software customer was not persisted; do not describe all failed test escrow balances as recovered.
