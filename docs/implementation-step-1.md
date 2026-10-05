# Step 1: local escrow and OWP signing compatibility

Status: local prototype implemented and tested. This is not a deployed payment service.

Goal: verify funded SPL-token escrow and customer/verifier authorization in a local Solana runtime, plus wallet-style Ed25519 signatures checked by unmodified OWP.

Architecture: an Anchor program owns a per-order token vault. A distinct customer and verifier must sign the same release transaction after delivery. An independent Python adapter prepares OWP canonical bytes and attaches externally produced signatures without accepting private keys. These components do not yet form the complete delivery application.

Constraints: all code stays in this project; preserve upstream OWP's dirty checkout. No mainnet, real funds, publishing, or submission. Use local-only generated identities; ignore secret files. Do not modify global shell, Solana or wallet configuration. Pin dependencies. Keep the designated directory as the working checkout; no additional worktree is needed for this new standalone repository.

## Task 1 — Escrow feasibility

Files: root Cargo/Anchor/package configuration, `programs/owp_settlement/src/lib.rs`, `tests/escrow.test.cjs`, `scripts/test-local.sh`.

Instructions: `fund_order` atomically freezes job ID, WorkOrder hash, provider, verifier, mint, amount, delivery deadline and funds a PDA vault. Require distinct nonzero role keys, amount > 0, nonzero digests and future deadline. `submit_delivery` is provider-only, before deadline, binds a nonzero immutable bundle hash and moves Funded to Delivered. `accept_and_release` requires customer and verifier transaction signers, exact work/bundle hashes and nonzero acceptance hash; sends the frozen amount only to the frozen provider's mint account and terminally settles. `reject_delivery` is customer-only and marks Disputed. `refund_expired` returns funds to the customer only from Funded after deadline; `refund_mutual` requires customer and provider from Delivered/Disputed. No arbitrary withdrawals, post-delivery timeout refund, re-delivery or repeated release.

- [x] Install isolated Rust, Solana and Anchor from official sources; record versions/checksums and the required external SDK cache symlink.
- [x] Write observable local-runtime tests. Initial missing-program behavioral RED was not observed because the compiler was not ready; this exception is disclosed in the verification record.
- [x] Implement instructions, PDA/account constraints, state checks and token CPI.
- [x] Compile SBF and execute deposit/release balance checks, wrong/missing signers, wrong evidence/accounts, duplicate calls, rejection and refund tests — 9 integration tests passed.

## Task 2 — OWP signature compatibility

Files: `bridge/owp_wallet_signing.py`, `tests/test_wallet_signing.py`, `requirements-dev.txt`, `bridge/README.md`.

Interfaces: `prepare_wallet_payload(object_type, payload, public_key_bytes, version='0.1')` returns unsigned envelope and exact bytes; `attach_wallet_signature(..., signature_bytes)` returns an OWP-valid signed envelope or raises. Return no private keys. Use OWP canonical_bytes/key_id/verify_payload; do not duplicate JCS.

- [x] Pin OWP to the existing baseline, install in a project virtualenv from committed objects.
- [x] Write tests for valid externally signed payload, changed payload, wrong key, malformed signature and domains.
- [x] Implement narrow adapter and run tests with native OWP verification — 61 tests passed.
- [x] Record that software signing compatibility is not evidence of a real browser wallet integration.

## Review and handoff

- [x] Specification review; close consequential findings.
- [x] Code review; rerun regressions after fixes. This is not an independent security audit.
- [x] Update README with exact reproducible commands and actual checks.

Review focus: malicious token accounts, wrong verifier, state races, repeated settlement/refund, unsigned/mutated OWP envelopes. All checks cover only this prototype, not security audit, production readiness or actual customer acceptance.
