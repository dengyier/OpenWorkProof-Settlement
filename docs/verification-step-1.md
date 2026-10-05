# Step-1 verification record

Date: 2026-10-05, Asia/Shanghai. Scope: local development prototype only.

## Results

- OWP adapter: `.venv/bin/python -m pytest -q` — **61 passed**; `pip check` — no broken requirements.
- Escrow: `npm run test:local` — SBF release build succeeded, followed by **9 passed / 0 failed / 0 skipped** integration tests in 80.718 seconds on a fresh local validator. A separate reviewer independently repeated the command: 9/9 passed in 80.239 seconds; the SBF digest matched and no RPC listener remained after runner exit.
- Static specification review: passed after fixing occupied-port isolation, causal onchain-rejection assertions and the winning delivery-digest race assertion.
- Adapter code review: passed after correcting native JSON depth/node-budget handling and rejecting preparation that leaves no room for the final signature.
- Escrow code review: no consequential defects identified; separate reviewer checked account/role constraints, dependency macro implementation and test assertions. This is not an independent security audit.
- JavaScript and Bash syntax checks passed.
- npm audit: **9 alerts, 3 high / 6 moderate**; unresolved test SDK dependency findings.

## Evidence boundaries

The adapter uses locally generated software Ed25519 keys and OWP's own canonicalizer/verifier. This verifies native compatibility, not an independent cryptographic audit or a browser-wallet approval flow. OWP Core is installed non-editably from the pinned committed tree, not from dirty upstream files.

The escrow suite targets a fresh local Solana validator through a loopback client endpoint with legacy SPL test tokens. It asserts deposit/release/refund balances, account/role checks, immutable evidence digests, terminal states, failure rollback and competing transactions. Failure tests must contain the target program invocation and custom program error in logs, not merely a client/RPC failure. These fixtures do not constitute real task evidence, customer acceptance, or payment.

The RPC **client endpoint** is loopback. `lsof` showed the Agave 4.3 validator RPC listener bound to `*:18899` despite `--bind-address 127.0.0.1`; no CLI RPC-bind override was available. Use only on a trusted development host/network with inbound access restricted. The runner stops its own temporary validator after testing, including on failure. No firewall configuration was changed.

SBF artifact: `target/deploy/owp_settlement.so`, 230,312 bytes, SHA-256 `e17fa1293f495a6cdd9e275e8c992c71c16c6c5514f0d4d111966d807ad80ff8`. The program was loaded directly into the local genesis at the fixed test address; this is not a public deployment transaction. Test identities and token mints are locally generated fixtures.

Resolved lockfile SHA-256: Cargo `9cf72e51641310e14170592db823152bcd08def1fcacfed422d6ee0db41913cb`; npm `721a58319f5a6e7b7cca0ccaedb7cd2d1175d4787c2f2ea803203f1b9b564cfc`. Compiler macro/LTO warnings and pure-JavaScript bigint fallback remain visible; they were not hidden to obtain a green result.

No behavioral RED run of a missing escrow implementation was observed: compiler setup was not ready when the test scaffold was written. The adapter's missing-module and budget-regression RED runs were observed before their corresponding fixes. Do not describe the escrow implementation as a completed strict RED/GREEN TDD cycle.

Not evidenced: full agent-work execution linked to escrow, evidence eligibility bridge, production attestation policy, real browser wallets, Devnet/mainnet deployment, dispute resolution, independent security audit, real funds, external acceptance, publication, registration or contest submission.
