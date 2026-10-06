# Rebuild the native delivery runtime

This recipe builds new local images from public, pinned source and hash-checked dependencies. It does not require the author's private directories or the three historical image caches. It does not publish images, deploy a program, call a paid model, create a wallet or submit a transaction.

See the [October 6 local validation record](runtime-verification-2026-10-06.md): public-source images built stage by stage, followed by 90 Python and 18 application tests in a fresh checkout. Network interruptions and the absence of an uninterrupted wrapper run are recorded explicitly.

## Supported environment

- Native **ARM64 Docker engine**, tested with Docker Desktop 29.5.2 on Apple Silicon.
- Docker Buildx with the Docker driver and the **containerd image store**. Loaded archives must expose actual `RepoDigests`; the script stops if this is not true. No image-store setting is changed automatically.
- Python 3.11+, Git, tar, curl 8.4+ (bounded HTTPS downloads), and outbound HTTPS to GitHub, PyPI, Debian/Snapshot and Docker Hub.
- For the application: Node 20.12+ and the pinned Python package from `requirements-dev.txt`.

x86/QEMU, another operator's machine and production deployment are not validated by the local rebuild. The fixed runner relies on Linux process isolation and Landlock; do not bypass those controls to make an unsupported environment pass.

## Build and test

From a checkout of this repository:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHON="$PWD/.venv/bin/python" bash scripts/build-runtime.sh
source .tools/runtime-build/runtime.env
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
npm ci --ignore-scripts
npm run test:app
```

The build may take several minutes. Its output directory must be new; a failed attempt is retained for diagnosis and is not overwritten. For a later attempt, supply another ignored directory:

```sh
PYTHON="$PWD/.venv/bin/python" bash scripts/build-runtime.sh "$PWD/.tools/runtime-build-2"
source .tools/runtime-build-2/runtime.env
```

If pip's partial Git clone fails on a restricted network, build the runtime first using system Python. Its `core` directory is a fresh public checkout at the same frozen commit; it is not the author's working tree. After checking `git -C .tools/runtime-build/core rev-parse HEAD` against the pin below, install it instead:

```sh
.venv/bin/python -m pip install .tools/runtime-build/core 'pytest==9.1.1'
```

Do not substitute an arbitrary local Core directory or disable TLS verification.

With those environment variables loaded, `bash scripts/start-devnet.sh` uses the rebuilt images rather than its historical defaults. Merely starting the application is not an onchain transaction; funding, acceptance and release still require their separate wallet approvals. Use Devnet/test tokens only.

## Frozen inputs and checks

1. Fetch OpenWorkProof Core commit `0dbc32b648f31343a5f9ccabf678f1e1075e60f1` from its public GitHub repository, not an editable local checkout.
2. Fetch the exact wheels named by that revision's execution/helper requirements. Select by the locked SHA-256, not by a floating version.
3. Locate the exact Debian package/version/architecture through [Debian's official Snapshot archive](https://snapshot.debian.org/), avoiding large rolling indexes and packages removed from current mirrors. Snapshot's file address may be SHA-1, but the bytes must still match the original lock's SHA-256. Missing, ambiguous or changed inputs stop the build; no newer package is silently substituted.
4. Use Core's own `prepare_context.py` to assemble source-allowlisted, hash-checked contexts. Preserve its protected execution runner and helper entry point.
5. Pull the pinned Python ARM64 base `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`. Build the three images with network disabled and without build-layer cache reuse.
6. Convert and load each Docker archive with Core's archive converter; inspect the registered manifest digests. The Settlement verifier uses the freshly built execution archive as a local, digest-addressed [OCI build context](https://docs.docker.com/reference/cli/docker/buildx/build/#build-context). This avoids asking a registry for an unpublished local image name. Its layer adds the exact `runtime/verifier_test.py` with root ownership and read-only permissions.
7. Write the actually observed helper/verifier references to ignored `runtime.env`. Native OWP checks those immutable references and fixed-test bytes again when creating a session.

Payloads over 1 MiB are downloaded in bounded byte ranges, using the same strategy as this repository's toolchain downloader. Each range must have the requested length; the assembled payload must match both the published size and the frozen SHA-256. Read-only HTTPS requests have at most two retries; certificate validation remains enabled.

The source pin contains an Apache-2.0 license for Core. The Settlement repository's own licensing decision is separate; dependency licenses remain their respective owners' terms. The historical demo images were built from an earlier source revision and are not relabeled as this rebuild.

This is a recipe for equivalent, inspectable runtime behavior, **not a promise of bit-identical image digests across Docker versions**. New work orders freeze the rebuilt digests. Old evidence keeps its original frozen digests; a new image cannot retroactively validate an old case. Keep original images if you need to replay historical evidence.

## Limits

Image rebuilds and local tests do not establish independent third-party reproduction, production security, customer adoption or task quality. Python application dependencies are not fully transitively locked; the existing npm audit and settlement trust limitations remain open. Downloads/archives stay under ignored local build directories and must not include `.env`, keys, delivery-session caches or raw recording files in a public commit.
