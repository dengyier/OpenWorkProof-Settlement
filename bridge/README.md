# External Ed25519 signing adapter

Local prototype for handing OpenWorkProof's exact signing bytes to an external
signer and attaching its returned signature. The adapter accepts raw **public**
key bytes and raw signature bytes; it never accepts, stores, or generates private
keys. It does not call a wallet, RPC endpoint, escrow, or token transfer.

## Reproduce

From the repository root, with Python 3.10 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/test_wallet_signing.py -q
```

`requirements-dev.txt` installs Core 1.4.0 from Git commit
`0dbc32b648f31343a5f9ccabf678f1e1075e60f1` and pytest 9.1.1. The Core source is
installed from the pinned remote revision, not from a local editable checkout.
Transitive runtime dependencies are resolved by pip; this is not a complete
transitive lockfile. No adapter package is published.

If a remote Git checkout fails and an existing Git repository contains the pinned
commit, export that committed tree into a fresh directory and install it normally:

```sh
core_export="$(mktemp -d)"
git -C /path/to/OpenWorkProof archive 0dbc32b648f31343a5f9ccabf678f1e1075e60f1 | tar -x -C "$core_export"
.venv/bin/python -m pip install "$core_export" pytest==9.1.1
```

This reads committed Git objects, preserving any dirty upstream working files.
It does not use an editable install. On 2026-10-05 the direct Git install failed
with `curl 18 / early EOF`; this clean-export fallback built and installed Core
1.4.0 successfully. The installed `openworkproof/signing.py` matched the pinned
Git object's SHA-256:
`c22ca53c18d08118cfc46b6f44122650ff955541debb1b63529d178aa1fd5272`.
The adapter suite passed **61 tests**, and `pip check` reported no broken
requirements in the isolated Python 3.12.13 environment.

## Contract

```python
from bridge.owp_wallet_signing import prepare_wallet_payload, attach_wallet_signature

# public_key_bytes: exactly 32 bytes of the signer's raw Ed25519 public key.
envelope, message_bytes = prepare_wallet_payload(
    "work-order", payload, public_key_bytes, version="0.1"
)

# Outside this Python adapter, ask the signer to sign EXACTLY message_bytes.
# Convert the returned raw 64-byte Ed25519 signature to Python bytes.
signed_payload = attach_wallet_signature(envelope, public_key_bytes, signature_bytes)
```

`envelope` is a detached JSON snapshot with exactly three keys:
`object_type`, `version`, and `payload`. Its payload contains
`signature_alg="Ed25519"`, the native `signer_key_id`, and the SHA-256 hex digest
of the returned canonical bytes. It has no `signature`. Preparation follows
native signing behavior: old top-level `digest`/`signature` are removed, and the
algorithm and signer fields are replaced with the supplied public key's values.
Other payload fields are preserved and checked by the native canonicalizer.
Preparation also checks the native final signed-payload budget with a placeholder
signature field, rejecting payloads that leave no room for attaching a signature.
The placeholder is never returned and does not change the canonical bytes.

The signing message is the upstream JCS encoding of the domain wrapper, including
the algorithm and signer identity. It is **not** the digest, a UTF-8 re-encoding of
a displayed JSON object, a transaction, or a prefixed wallet message. The native
fingerprint is `ed25519:` followed by SHA-256 of the raw public key, not a Solana
base58 address. `signature` is unpadded base64url of the raw 64-byte signature.

Attachment verifies the domain/version combination, public key binding, original
digest and signature using upstream `verify_payload`. It returns a new signed
payload or raises `ValueError`; neither input is modified. Payload, signer,
domain or version changes after preparation invalidate the original signature.
If a `protocol_version` field exists in the payload, it must equal the signing
domain version. Core's package version `1.4.0` is not a signing-domain version.

The adapter supports the native signed registries for `0.1`, `0.3`, `0.4`, and
`0.5`, reusing the pinned Core's `_signed_domains_for_version` helper and
`_snapshot_json` to preserve native payload depth and node limits. These helpers
are private, so changing the Core pin requires reviewing this integration. Canonical
domains that are unsigned for the selected version are rejected. In particular,
`evaluation-scope` is unsigned in `0.1` but signed in `0.3`;
`authority-checkpoint` uses a separate native signing API and is outside this
adapter. Generic signature verification does not validate object schemas, role
authorization, task quality, replay policy, or settlement eligibility.

## Evidence boundary

The tests use locally generated software Ed25519 keys to simulate signing bytes
returned by a wallet's `signMessage` method. They check byte-for-byte equivalence
with native signatures, native verification, supported versions, mutation,
wrong keys, digest-versus-message confusion, malformed inputs, unsigned domains
and native maximum depth/node budget boundaries, including early rejection when
the final signature would exceed the node budget.
This is local compatibility evidence, without an independent verifier.

Real browser wallet support, account changes, user approval/cancellation,
wallet-specific message prefixes, hardware wallets, transaction signing, Solana
Devnet or mainnet deployment, settlement, real funds and external acceptance are
**not evidenced**. A future browser integration must demonstrate that a specific
wallet signs these exact bytes and that the returned signature verifies under
the selected raw public key before making any wallet-support claim.
