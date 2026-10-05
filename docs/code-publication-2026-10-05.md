# Competition source publication checks

User-authorized destination: https://github.com/dengyier/OpenWorkProof-Settlement, a new public repository under `dengyier`. The initial source commit `13e2d587983ac0d2f6ca452377674a2576666539` was pushed to `main` on October 5, 2026. GitHub reported `isPrivate=false`, default branch `main`; remote branch SHA matched the local commit. The authenticated contest form recognized the repository as public, and saved its URL plus the prior-work/trust-limit context. This is source publication for review, not final contest submission, production readiness or an independent security audit.

## Included scope

Settlement program, local review application, Python OWP integration, immutable-test fixture source, tests, pinned dependency/toolchain descriptions, English demo/captions and public Devnet evidence. The `.env.example` template contains an empty API-key value only. OWP Core predates the entry and is linked/pinned, not represented as newly authored competition code.

## Excluded and preserved locally

- `.env` and nonexample environment files.
- App-owned provider, verifier, deployer and software-customer private keys; native OWP signing keys; generated validator/deployment keypairs.
- `.tools`, `.venv`, `node_modules`, `target`, validator ledgers, Python caches and browser-automation outputs.
- Original raw screen recording and production working files. Only the previously reviewed final MP4, SRT and public case evidence are included; the audio sidecar and local edit-decision list are excluded.

No private files were deleted or credentials rotated. The code does generate private files at runtime in ignored local directories; those code paths are not literal published keys.

## Key/credential scan

Before the initial commit, a local-only scanner examined the exact staged Git blobs, forbidden paths and symlink modes. It compared them with the local configured API credential and public encodings of 72 local private-key files (307 distinct secret representations), without printing any values. Additional patterns checked private-key PEM blocks, provider/GitHub/AWS credentials, credential-bearing URLs, literal private credentials and Solana 64-byte key arrays.

The initial commit contains 68 explicitly selected files. No candidate secret match remained. One flagged string in `tests/worker.test.cjs` was manually confirmed as an explicit dummy value in a test that replaces the network fetch function; only that exact fixture was allowed. This is a bounded publication preflight, not a guarantee against every possible secret format, encrypted payload or visual disclosure. The final video was previously visually reviewed and its raw private production material is excluded.

## Fresh checks of this source candidate

- `npm run test:app`: **18 passed, 0 failed**.
- Python suite with the actual immutable helper/verifier images: **83 passed**.
- `npm run test:local`: SBF build succeeded; **9 local-validator escrow tests passed**, including authority/digest/account substitution, expiry, repeat actions and competing terminal transitions.
- `git diff --cached --check`: no whitespace errors.

These checks did not make another paid model call, request customer signatures, spend mainnet funds or rerun Devnet settlement. Existing Anchor cfg/LTO warnings and the SDK pure-JavaScript bigint fallback remain disclosed. Dependency audit findings and unpublished/local-only Docker runtime provenance remain limitations described in the README; publishing source does not clear them.

Public access alone does not assert an open-source license grant, third-party adoption, organizer acceptance or final submission. No new license terms were chosen on the user's behalf.
