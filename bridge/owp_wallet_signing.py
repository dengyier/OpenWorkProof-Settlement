"""Prepare native OWP signing bytes and attach an external Ed25519 signature.

This adapter receives only public keys and signatures, never private keys.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from openworkproof.signing import (
    _signed_domains_for_version,
    _snapshot_json,
    canonical_bytes,
    key_id,
    unsigned_payload,
    verify_payload,
)

SigningVersion = Literal["0.1", "0.3", "0.4", "0.5"]


def _public_key(raw: bytes) -> Ed25519PublicKey:
    if type(raw) is not bytes or len(raw) != 32:
        raise ValueError("public key must be exactly 32 raw Ed25519 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def _check_domain(object_type: str, version: SigningVersion) -> None:
    if type(version) is not str:
        raise ValueError("unknown signing version")
    # Pinned upstream registry; do not copy or broaden its versioned allowlist.
    domains = _signed_domains_for_version(version)
    if type(object_type) is not str or object_type not in domains:
        raise ValueError("object type cannot be signed in this version")


def _check_payload_version(payload: Mapping[str, Any], version: SigningVersion) -> None:
    if "protocol_version" in payload and payload["protocol_version"] != version:
        raise ValueError("payload protocol_version does not match signing version")


def prepare_wallet_payload(
    object_type: str,
    payload: Mapping[str, Any],
    public_key_bytes: bytes,
    version: SigningVersion = "0.1",
) -> tuple[dict[str, Any], bytes]:
    """Return a detached unsigned envelope and the exact bytes to sign."""
    public_key = _public_key(public_key_bytes)
    _check_domain(object_type, version)
    prepared = unsigned_payload(payload)
    _check_payload_version(prepared, version)
    prepared["signature_alg"] = "Ed25519"
    prepared["signer_key_id"] = key_id(public_key)
    message = canonical_bytes(object_type, prepared, version=version)
    prepared["digest"] = hashlib.sha256(message).hexdigest()
    # Check the native final payload budget before asking an external signer.
    _snapshot_json({**prepared, "signature": ""})
    return {"object_type": object_type, "version": version, "payload": prepared}, message


def attach_wallet_signature(
    envelope: Mapping[str, Any],
    public_key_bytes: bytes,
    signature_bytes: bytes,
) -> dict[str, Any]:
    """Return a native-verifiable signed payload, or raise ValueError."""
    public_key = _public_key(public_key_bytes)
    if type(signature_bytes) is not bytes or len(signature_bytes) != 64:
        raise ValueError("signature must be exactly 64 raw Ed25519 bytes")
    if not isinstance(envelope, Mapping) or set(envelope) != {
        "object_type", "version", "payload"
    }:
        raise ValueError("invalid prepared envelope")
    object_type = envelope["object_type"]
    version = envelope["version"]
    _check_domain(object_type, version)
    # Snapshot only the payload so the envelope consumes no native JSON budget.
    # Preserve digest/signature fields for the checks below, unlike unsigned_payload.
    signed = _snapshot_json(envelope["payload"])
    if not isinstance(signed, dict) or "signature" in signed:
        raise ValueError("envelope payload must be an unsigned object")
    _check_payload_version(signed, version)
    if signed.get("signature_alg") != "Ed25519" or signed.get("signer_key_id") != key_id(public_key):
        raise ValueError("prepared payload does not match public key or algorithm")
    message = canonical_bytes(object_type, signed, version=version)
    if signed.get("digest") != hashlib.sha256(message).hexdigest():
        raise ValueError("prepared payload digest changed")
    signed["signature"] = base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("=")
    if not verify_payload(object_type, signed, public_key, version=version):
        raise ValueError("wallet signature does not verify for the prepared payload")
    return signed
