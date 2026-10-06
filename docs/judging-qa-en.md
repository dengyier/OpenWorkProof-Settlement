# Judging interview: concise answers

Preparation notes, not a new submission or evidence of an interview invitation.

## What does the product do?

OpenWorkProof Settlement connects a bounded AI-agent delivery to customer-approved escrow settlement. A work order freezes the scope and acceptance conditions; signed evidence records execution and verification. The customer reviews the delivery and explicitly accepts or rejects it. Payment is a separate onchain action, not a consequence of the agent saying “done.”

## Who is the first intended user?

A developer team or agent-service provider delivering a small, scoped coding task to another party. Our current reproducible example fixes an `average(values)` function under restricted paths and immutable tests. Broader services and paying external customers are future validation, not demonstrated adoption.

## Why use Solana rather than only an activity log?

An activity log records what happened but does not enforce the escrow's frozen recipients and terminal token transfers. The Solana program binds identities and delivery commitments to a funded order, blocks release after a dispute, and prevents repeated settlement/refund. It does not judge software quality; that still depends on evidence checks, the designated verifier and customer acceptance.

## What is already demonstrated?

The submitted video shows two separate Solana Devnet orders. Order A uses a live DeepSeek proposal, protected OWP execution, verification, a Phantom acceptance message, and a separate release transaction. Order B uses a reference patch, not an LLM: verification succeeds, the customer rejects, a transaction records the dispute, and customer/provider agreement returns exactly 1 DemoUSD. These are operator-run test-token cases, not independent commercial customers.

## Is this trustless or an independent escrow institution?

No. The application operates the demo provider and designated verifier. Its backend rechecks evidence and partially signs a release. The program enforces identities and transfers but cannot prove task quality by itself. The Devnet deployment also has a developer-controlled upgrade authority. This prototype does not replace a bank, regulated custodian or independent arbitrator.

## Can the customer reject and automatically get a refund?

No. Rejection blocks release and can be recorded as a dispute. After delivery, cancellation requires both customer and provider. Our demo provider consents to cancellation; this is not arbitration or a guarantee that real parties will agree. Without agreement, disputed funds may remain locked. An undelivered order has a separate expired-order refund path.

## How much existed before the hackathon?

OpenWorkProof Core existed before this entry and is publicly linked and pinned. The entry is the separate Settlement application: the Solana escrow, delivery-review integration and wallet settlement/refund flows. We disclose earlier work rather than describing Core as newly created during the competition. The developer reported no prior blockchain development before this hackathon.

## What should a reviewer run, and what is still missing?

Start with the [runtime rebuild recipe](runtime-reproduction.md), then run the Python delivery tests and `npm run test:app`. The reference-patch path needs no model API key. Actual Devnet transactions require test tokens and personal wallet approvals; never use mainnet or real money.

Remaining limitations include dependency audit findings, incomplete Python transitive locking, no independent security audit or customer adoption, no autonomous dispute resolution, no Token-2022 support and no account-rent/surplus-token recovery flow. The next useful validation is an independently reproduced, narrowly scoped delivery—not a claim of production readiness.

## Evidence links

- [Submitted project](https://colosseum.com/arena/projects/openworkproof-settlement)
- [Code](https://github.com/dengyier/OpenWorkProof-Settlement)
- [Actual product demonstration](https://youtu.be/iY_NE8bBbyI)
- [Founder pitch](https://youtu.be/srXH7TC70_w)
- [Historical Phantom execution](devnet-phantom-2026-10-05.md)
- [Historical rejection/refund checks](devnet-wallet-refund-2026-10-05.md)
