# Public-source runtime rebuild: October 6, 2026

This is a local reproduction and packaging record, separate from the historical Phantom/Devnet recordings and the confirmed contest submission. No paid model request, wallet signature or onchain transaction was performed for this check.

## Inputs and environment

- Settlement source: the staged changes based on commit `4c5c3f54a990bd692fa8032a9199123f3baf8bdf`, exported to a new checkout without the author's `.env`, wallets or delivery caches.
- Core: a fresh fetch from <https://github.com/dengyier/OpenWorkProof>, detached at `0dbc32b648f31343a5f9ccabf678f1e1075e60f1` (package 1.4.0). The editable upstream working tree was not used or changed.
- Thirteen unique wheels from public PyPI and 31 Debian packages from official Snapshot, checked against the frozen Core SHA-256 locks. Core's own context assembler rechecked directory closure, hashes and allowlisted Git blobs.
- Python ARM64 base: `docker.io/library/python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
- Native Apple Silicon Docker engine 29.5.2, containerd image store, Buildx 0.34.0-desktop.1; clean application environment Python 3.14.5 and Node 23.11.0.
- Fresh application dependencies: pinned Core installed from that public checkout and pytest 9.1.1; `npm ci --ignore-scripts` installed the existing lock. Python transitive dependencies are not fully locked.

## Build result

Execution, helper and Settlement verifier were rebuilt without build-layer cache reuse and with build-step network access disabled. The public base image was pulled by digest. The fixed runner, source allowlist, read-only test file and unprivileged runtime user were preserved. Archives were converted by the pinned Core converter and loaded into Docker; the following are observed `RepoDigests`, not fabricated aliases:

```text
execution: owp-settlement/rebuild-execution@sha256:6ca82ac9c3e1d4b82425b4aa4fd7cffe5cf75fac13f14b768537597bb230ec57
helper:    owp-settlement/rebuild-helper@sha256:5f72bd98c86863af1b818e84981e2386b439e96d18d4f004a9ecace345e0a6d5
verifier:  owp-settlement/rebuild-verifier@sha256:1145481b4d883c152931332761448a0c3bc6e2d2536bd501a383f25a7a21e5e7
```

These images remain local, not publicly pullable registry images. Reviewers build their own using the [recipe](runtime-reproduction.md); resulting digests can differ across environments. Historical demo records retain their original digests.

Public download attempts encountered TLS interruptions and a large-package timeout. Verified files from the fresh public-download attempt were retained; the missing Git package was downloaded in bounded ranges and matched the original SHA-256. Checksum manifests were assembled and revalidated by Core before building. The final build was completed stage by stage, **not as an uninterrupted successful invocation of the wrapper**. No private wheelhouse or historical OWP image was substituted.

An initial verifier build tried to resolve the unpublished execution name through a registry mirror. The corrected recipe supplies its freshly built archive directly as a local OCI context addressed by the observed manifest digest; that actual build succeeded. TLS validation and digest checks were not disabled.

## Fresh-checkout checks

With the rebuilt immutable helper/verifier references and no model API key:

- `python -m pytest -q`: **90 passed in 113.45 seconds**, with no skips. This includes the seven new downloader checks and the native delivery, customer acceptance, rejection, evidence tampering and signature-boundary tests.
- `python -m pip check`: **No broken requirements found**.
- `npm run test:app`: **18 passed**, no failures or skips. Wallet/RPC behavior is automated here, not a fresh Phantom interaction.
- `bash -n scripts/build-runtime.sh` and Git whitespace checks passed.

The original Solana program was not changed. No new local-validator or Devnet test run is claimed by this record; previous chain verification remains in its dated records.

## Publication and remaining boundaries

The staged-publication scanner found no configured credentials or known local private-key representations in the selected public files. Only scoped code, tests and documentation were selected; pre-existing uncommitted materials and raw recordings were left out. This is a targeted secret scan, not proof that every conceivable secret pattern is absent.

The existing npm installation still reports nine dependency alerts (three high and six moderate). No automatic major-version upgrade, production-security approval, independent-machine/operator reproduction or commercial customer adoption is claimed. Settlement licensing remains awaiting owner confirmation; the pinned Core has Apache-2.0. The [submitted entry](contest-submission-2026-10-06.md) is already entered for judging and must not be resubmitted.
