# Step 2 — delivery, human acceptance, wallet and Devnet

Authorized 2026-10-05. Goal: one real bounded coding delivery connected to test-token escrow. Preserve the upstream checkout and existing local prototype; no mainnet, real-money transfer, public release, registration, or automatic customer acceptance.

## Contract and sequence

1. Connect a browser Solana wallet or use an explicitly labelled software customer in automated tests. Freeze its raw public key as the OWP Acceptor and its address as chain customer. Freeze Devnet/local genesis hash, program, provider/verifier addresses, demo mint, integer amount, deadline, job ID and WorkOrder digest before funding.
2. Create a genuine native OWP WorkOrder, role bindings, grants, ledger and a disposable example repository containing a failing acceptance test. Only the authorized application file may be patched; tests and criteria stay frozen.
3. After confirmed funding, a bounded worker supplies a proposed patch; execute it through native OWP protected tools and record actual output. Run independent verification in a clean workspace through OWP, produce signed proof/delivery artifacts. No fabricated tool outputs or `VERIFIED` labels. A deterministic reference worker is explicitly a fixture, not autonomous LLM execution; a configured live model path is separate.
4. Display source revision, scope, actual patch, test results, evidence and exact settlement terms. Customer explicitly requests ACCEPT or REJECT and signs OWP's exact message bytes. Commit the native acceptance/rejection and verify its bindings. Backend never holds customer private keys. Reject changed evidence, another customer/key, stale draft, failed tests and reused acceptance.
5. Designated attester re-verifies native evidence and acceptance plus chain order binding immediately before partially signing a release transaction. It signs only the configured program/instruction/accounts/amount/digests for the current order, after native ACCEPTED. Customer wallet signs the same transaction. Finalized status, terminal order and token balances must reconcile before displaying SETTLED; uncertainty remains UNKNOWN/PENDING and is queried before retry.
6. Devnet deployment and test-token setup use isolated generated demo identities, explicit RPC URL and checked Devnet genesis; never use an existing personal wallet or change global config. Upgrade authority remains developer-controlled and is disclosed. Test wallets are operator-controlled, not independent customers.

## Bounded tasks / verification

- Native OWP delivery module and focused adversarial tests → native valid WorkOrder/receipts, real failing/passing tests, exact-byte external acceptance, tamper/refuted/rejected/wrong-key/replay refusal.
- Shared chain client and genuine delivery integration → actual deposit, provider submission, no release before acceptance, exact dual-signed release, balance/state reconciliation, rejected/tampered flow no attester signature.
- Local browser application → user-initiated wallet connect/signMessage/signTransaction, account-change and cancellation fail closed, no private-key API, English review interface, local-only authenticated state-changing endpoints.
- Devnet feasibility/deployment → confirm genesis, faucet balance, deployment executable/authority/program bytecode, record deployment/fund/submit/release transaction evidence. If faucet, model key or browser wallet is missing, finish independent preparation and report the exact missing gate; do not label test doubles as completed external integrations.

## Trust and constraints

OWP and chain are not atomic. Rejection blocks attester signing but cannot undo a previously signed/confirmed chain transaction. No arbitration; delivered disputed funds require mutual refund. Only legacy SPL DemoUSD; no USDC/real dollar claim. Attester is a trusted backend; separate role keys/processes do not establish independent operators. RPC listeners must be restricted to a trusted development environment. Existing SDK audit alerts remain a production blocker, not a test bypass.
