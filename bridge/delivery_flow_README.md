# Native fixture delivery

`DeliverySession` runs the installed, pinned OpenWorkProof Core 1.4.0 package.
It does not import an upstream working tree or upstream test fixtures.

The caller must enforce confirmed funding before `execute`. This module has
no blockchain client and does not move tokens. `chain_terms` are copied and
their canonical digest is bound into the Maintainer-signed native WorkOrder.

The disposable source contains a buggy `average(values)` function. The patch
may change only `src/app.py`; fixed tests cover multiple values, a single value,
and negative/fractional results. A patch is supplied by the caller. This is a
fixture demonstration, not evidence of an autonomous model.

Native operations are root activation, delegated grants, protected repo read,
protected patch, native Docker test transaction, native proof composition,
native acceptance request, externally signed acceptance/rejection, and native
offline composition/acceptance verification. The frozen Docker image must
contain the exact `FIXED_TEST_SOURCE` bytes. Its actual immutable reference is
required in `OWP_VERIFIER_IMAGE`; the real helper reference is required in
`OWP_HELPER_IMAGE`.

For a new checkout, use the [public-source rebuild recipe](../docs/runtime-reproduction.md)
and source its generated `runtime.env` before testing or starting the app.
It preserves the native runner and constructs both images without private caches.

The following historical command is only for machines that already have the
old base image. Build the fixture image from `runtime/Dockerfile`. The base image is an existing
local immutable image; its source provenance is distinct from the Core pin.
The legacy builder can use that local image without querying a remote registry:

```sh
DOCKER_BUILDKIT=0 docker build --pull=false -t owp-settlement/verifier:step2 runtime
docker image inspect owp-settlement/verifier:step2
```

Use the actually inspected immutable digest reference, with a registry host
(the adapter normalizes Docker Hub short names). No image upload is needed.

`tests.verifier` exposes the actual native receipt, signed test result, and
native result envelope with stdio hashes. Upstream removes the original stdio
text; `tests.clean_rerun` separately exposes actual output from a fresh Docker
workspace using the same immutable image and fixed tests. Both environments
have the same app operator. The native WorkOrder uses `disclose_only` and four
evidence dimensions. No independent operator is asserted.

`delivery-bundle.json` contains the exact frozen native composition objects,
receipts, grants, evidence bytes, source archive, and fixed tests. Its hash is
stable through acceptance preparation, customer commitment, and session reload.
`customer-decision.json` holds the externally signed native terminal receipt.
This is a native v0.1 composition snapshot verified by Core, not a v0.5
AcceptanceBundle directory or VerificationDecision claim.

All noncustomer private keys are app-owned runtime files with mode 0600.
The customer private key is never accepted or stored. The parent application
keeps session roots under its ignored `.tools` directory. A second draft
invalidates the first; signature, ledger tip, current evidence, signed authority,
and unchanged chain terms are checked before committing or releasing.
The job ID must equal the signed native WorkOrder ID. Summary validates the
displayed patch and test verdict against native receipts and evidence. The
app-owned review snapshot (including separate clean-rerun output) and its SHA
are frozen inside the submitted bundle; later metadata drift is refused.
Reload reconstructs a missing terminal cache from the validated native
acceptance/rejection tables and clears the consumed draft; a conflicting cache
is rejected. Cache writes use atomic replacement. Recovery never requests or
creates another customer signature.

The native API limits final-acceptance requests to one hour. Request expiry is
`min(now + one hour, native WorkOrder deadline)` and is exposed in the signing
draft and summary. Canceling the wallet prompt leaves the native request open;
the customer can prepare a fresh draft within that window. Once it expires,
the application must use its existing mutual-cancellation path. This adapter
does not reopen an expired native request or bypass native state transitions.

Validation:

```sh
OWP_VERIFIER_IMAGE='<actual immutable fixture image>' \
OWP_HELPER_IMAGE='<actual immutable helper image>' \
.venv/bin/python -m pytest -q tests/test_delivery_flow.py tests/test_wallet_signing.py
```
