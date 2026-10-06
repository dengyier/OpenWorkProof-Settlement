# OpenWorkProof Settlement

Research baseline: **2026-10-05**, Asia/Shanghai. Submission status verified: **2026-10-06**.

Competition code-review repository: [dengyier/OpenWorkProof-Settlement](https://github.com/dengyier/OpenWorkProof-Settlement). This is the settlement integration, separate from the pre-existing OWP Core repository. Public source access is not a production release or an independent security audit.

OpenWorkProof Settlement connects verifiable AI-agent delivery and explicit customer acceptance to a funded onchain escrow. OpenWorkProof supplies the work contract and signed evidence; this new application is being developed to manage wallet approval, escrow state and token transfers.

**Status: submitted for judging; step-3 Devnet prototype.** The [Crypto World's Fair entry](https://colosseum.com/arena/projects/openworkproof-settlement) was formally submitted on **2026-10-06 at 19:18 Asia/Shanghai**. See the [submission record](docs/contest-submission-2026-10-06.md). Submission is not a judging result, award, security certification or production release.

Native OWP work orders, protected code execution, Docker verification, exact-byte customer signatures and SPL escrow are connected through a local English delivery-review application. The settlement program is deployed on Devnet. Actual DeepSeek execution and Phantom customer funding, acceptance and release were verified in a bounded test-token delivery; real release-transaction cancellation was also checked. A separate reference-patch case verified actual acceptance-message cancellation, between-prompt account switching, rejection, dispute and an exact 1 DemoUSD mutual refund. In-flight account switching remains automated-only. See the [actual Phantom execution record](docs/devnet-phantom-2026-10-05.md), [wallet-exception and refund record](docs/devnet-wallet-refund-2026-10-05.md) and [earlier step-2 verification](docs/verification-step-2.md). No mainnet, real payment, independent-customer adoption or production release is evidenced.

## Open the delivery review application

With Docker running and immutable runtime images installed (new reviewers should first use the [public-source runtime rebuild](docs/runtime-reproduction.md)):

```sh
bash scripts/start-devnet.sh
```

Open `http://127.0.0.1:3188` in a browser with Phantom, select Devnet and connect your wallet. Freeze a work order, fund 1 DemoUSD, execute the protected reference patch, review actual evidence, sign the native acceptance, then separately authorize release. Your wallet needs Devnet SOL for transaction fees and order rent; do not send real SOL. DemoUSD is minted by this isolated application, not USDC or money. The backend never requests a customer private key.

The default reference proposal is not an LLM. The optional DeepSeek path requires `DEEPSEEK_API_KEY` in a local, ignored `.env` (see `.env.example`); restart the server after configuring it. Requires Node 20.12+. Never put credentials in chat or committed files. The model proposes one file as JSON; local code computes canonical patch hashes, then native OWP execution and immutable tests verify the work. New bundles bind an app-operator-signed API attribution record to customer acceptance; this is not a signature by the model provider or independent verification. See [step 3 contract](docs/implementation-step-3.md), [official API documentation](https://api-docs.deepseek.com/), [native runtime setup](bridge/delivery_flow_README.md) and [runtime rebuild recipe](docs/runtime-reproduction.md). Historical default image references are local-only; the rebuild creates new immutable references, not a published deployment.

A first actual DeepSeek proposal → native OWP validation → software-test-customer acceptance → finalized Devnet release was observed on 2026-10-05. See the [live-model execution record](docs/devnet-live-model-2026-10-05.md). This is not independent adoption or browser-wallet approval.

A separate [actual Phantom run](docs/devnet-phantom-2026-10-05.md) then completed real model execution, browser-wallet acceptance and finalized Devnet settlement. Prepared transactions freeze the compute budget and zero priority price before signing; wallet changes are still refused. If verification-grant issuance is interrupted after the patch is applied, `Continue verification` uses that saved patch without repeating the paid model call. An already-started verifier or completed test cannot be blindly rerun.

```sh
npm run test:app
# Requires actual immutable images, as exported by scripts/start-devnet.sh:
OWP_VERIFIER_IMAGE='<actual fixture reference>' OWP_HELPER_IMAGE='<actual helper reference>' .venv/bin/python -m pytest -q
# Explicitly spends only this application's isolated Devnet test coins:
OWP_ALLOW_DEVNET_TEST=1 npm run test:devnet
```

## Run the local checks

The [October 6 clean-checkout verification](docs/runtime-verification-2026-10-06.md) rebuilt the runtime from public pinned inputs, then passed **90 Python tests and 18 application tests**. It is a local stage-by-stage reproduction, not an independent-machine audit or a new Devnet transaction.

Install the pinned tooling described in [toolchain setup](docs/toolchain-step-1.md), then run from this repository:

```sh
npm ci --ignore-scripts
npm run test:local
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
# Fresh ARM64 runtime build; source its actual immutable image references:
PYTHON="$PWD/.venv/bin/python" bash scripts/build-runtime.sh
source .tools/runtime-build/runtime.env
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

The escrow runner builds SBF, starts its own local validator, accesses it through `127.0.0.1:18899`, funds locally generated identities with faucet SOL and freshly minted test tokens, runs transaction/balance assertions and stops its own validator. It refuses an occupied RPC port and the tests reject public-network URLs. **Agave 4.3's test-validator RPC still listens on all interfaces despite the loopback bind argument. Run only on a trusted development host/network with inbound access restricted; do not expose it to the Internet.** It does not connect to Devnet or spend real funds. Test ledgers and keypairs are ignored by Git; do not publish them.

The signing adapter's setup, exact-byte contract and compatibility limitations are in [bridge/README.md](bridge/README.md). Upstream Core is pinned to commit `0dbc32b648f31343a5f9ccabf678f1e1075e60f1`; this project does not modify the upstream checkout.

## Escrow rules and trust boundary

`fund_order` freezes customer, provider, designated verifier, mint, amount, delivery deadline and work digest. The provider commits one delivery digest before the deadline. Release requires the customer and designated verifier to sign the same transaction, matching work/delivery digests and a nonzero acceptance digest. The frozen amount goes only to an account of the frozen mint owned by the frozen provider; the exact token-account address is not frozen.

An undelivered, expired order can be refunded by the customer. Once delivered, cancellation requires both customer and provider; rejection enters a disputed state and blocks release. Settlement and refund are terminal. There is no admin withdrawal or unilateral post-delivery timeout refund.

The program checks identities, commitments and transfers, **not task quality or OWP evidence semantics**. The application attester re-verifies native evidence, customer acceptance and frozen chain bindings before partially signing release; it is a trusted backend, not trustless proof of quality. Local escrow unit fixtures and real native delivery records remain distinct. Disputes can lock funds without mutual agreement; the app-owned demo provider consents to requested cancellation, not arbitration. Account rent and unsolicited surplus tokens have no recovery flow. Only legacy SPL Token is supported, not Token-2022 or transfer-hook assets. Do not use this prototype with real money.

Program `2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk` is deployed on **Devnet only** with a developer-controlled upgrade authority; the deployed bytecode matches the current local build. Dependencies and integration/security review are not production-cleared.

## Dependency limitations

`Cargo.lock` and `package-lock.json` pin resolved dependencies. Python pins OWP and pytest but does not yet lock all transitive packages. The 2026-10-05 npm audit reported **9 alerts (3 high, 6 moderate)** in the local test SDK dependency tree. Native npm install scripts are disabled; the SDK uses a JavaScript fallback for bigint bindings. Audit findings remain unresolved, not waived as safe. Automated major-version downgrades/upgrades are not applied to this prototype.

## Licensing

Settlement does not yet include its own `LICENSE` file; project-owner confirmation is pending. The pinned OpenWorkProof Core source includes Apache-2.0. Dependencies retain their respective licenses; public source availability and licensing status are separate from contest submission.

## Research documents

- [English product demo on YouTube](https://youtu.be/iY_NE8bBbyI) — 2:48 edited actual Phantom/Devnet recording, English neural narration and captions; unlisted and included in the formal submission. [Local MP4](outputs/contest-demo-en/openworkproof-settlement-demo-en.mp4).
- [English project pitch on YouTube](https://youtu.be/srXH7TC70_w) — approximately 1:58, included in the formal submission.
- [Confirmed submission and material links](docs/contest-submission-2026-10-06.md)
- [English judging interview preparation](docs/judging-qa-en.md)
- [Recording verification and trust boundaries](docs/contest-demo-recording-2026-10-05.md) · [Script and storyboard](docs/contest-demo-en.md) · [Recorded-case chain evidence](outputs/contest-demo-en/recorded-demo-evidence.json)
- [Source publication checks and exclusions](docs/code-publication-2026-10-05.md)
- [Contest rules and submission checklist](docs/contest-research-2026-10-05.md)
- [Product scope, blockchain design and delivery plan](docs/product-and-chain-plan.md)
- [Existing OWP baseline and development disclosure](docs/baseline-and-disclosure.md)

The Chinese documents above are internal planning notes, not English contest submission materials.

## Proposed first loop

```text
Freeze a coding task and its acceptance conditions
→ Customer funds a test-token escrow
→ Agent performs the bounded task and exports OWP evidence
→ Verifier reviews the evidence and reruns required checks
→ Customer reviews and explicitly accepts the delivery
→ Customer and designated verifier authorize escrow release
→ Confirm the transfer onchain and reconcile the delivery record
```

Recommendation: one Solana Devnet integration, one task, one customer, one provider, and a separately authorized verifier. Testnet tokens have no real-payment meaning. The verification bridge is a disclosed trust dependency, not a trustless proof of work quality.

Upstream protocol: [dengyier/OpenWorkProof](https://github.com/dengyier/OpenWorkProof). Existing code and earlier development must be disclosed; only work completed during the contest period is judged.

## Contest references

- [Crypto World's Fair](https://colosseum.com/worldsfair)
- [Official rules](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf)
- [Hackathon FAQ](https://colosseum.com/hackathon)
- [Registration](https://colosseum.com/arena/hackathon/register?entry=worldsfair)

Submission deadline: **2026-10-12 23:59 America/Los_Angeles**, equivalent to **2026-10-13 14:59 Asia/Shanghai**. This entry was submitted on October 6; do not submit it again. Keep submitted review links accessible and check the portal for organizer requests.
