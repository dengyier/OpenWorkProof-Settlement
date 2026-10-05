"""Software signMessage simulation; not evidence of browser-wallet support."""

import base64
import copy
import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from openworkproof.signing import (
    MAX_JSON_DEPTH,
    MAX_JSON_NODES,
    canonical_bytes,
    key_id,
    sign_payload,
    verify_payload,
)


@pytest.fixture
def wallet():
    signer = Ed25519PrivateKey.generate()
    public_bytes = signer.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return signer, public_bytes


def adapter():
    from bridge.owp_wallet_signing import (
        attach_wallet_signature,
        prepare_wallet_payload,
    )

    return prepare_wallet_payload, attach_wallet_signature


def test_external_sign_message_matches_native_signature(wallet):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    payload = {"work_order_id": "a" * 64, "description": "交付 café", "items": [1, 2]}
    original = copy.deepcopy(payload)
    envelope, message = prepare("work-order", payload, public_bytes)
    assert set(envelope) == {"object_type", "version", "payload"}
    assert envelope["object_type"] == "work-order"
    assert envelope["version"] == "0.1"
    unsigned = envelope["payload"]
    assert "signature" not in unsigned
    assert unsigned["signature_alg"] == "Ed25519"
    assert unsigned["signer_key_id"] == key_id(signer.public_key())
    assert unsigned["signer_key_id"] == "ed25519:" + hashlib.sha256(public_bytes).hexdigest()
    assert message == canonical_bytes("work-order", unsigned)
    assert unsigned["digest"] == hashlib.sha256(message).hexdigest()
    before_attach = copy.deepcopy(envelope)
    raw_signature = signer.sign(message)
    signed = attach(envelope, public_bytes, raw_signature)
    assert verify_payload("work-order", signed, signer.public_key())
    assert signed == sign_payload("work-order", original, signer)
    assert signed["signature"] == base64.urlsafe_b64encode(raw_signature).decode().rstrip("=")
    assert "=" not in signed["signature"]
    assert payload == original
    assert envelope == before_attach
    signed["items"].append(3)
    assert envelope == before_attach


@pytest.mark.parametrize(
    "domain,version",
    [("manifest", "0.1"), ("evaluation-scope", "0.3"),
     ("verification-profile", "0.3"), ("action-binding-manifest", "0.4"),
     ("judgment-commitment", "0.4"), ("retraction-receipt", "0.5")],
)
def test_version_specific_signed_domains(wallet, domain, version):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    envelope, message = prepare(domain, {"protocol_version": version}, public_bytes, version)
    signed = attach(envelope, public_bytes, signer.sign(message))
    assert verify_payload(domain, signed, signer.public_key(), version=version)
    assert signed == sign_payload(domain, {"protocol_version": version}, signer, version=version)


@pytest.mark.parametrize(
    "domain,version",
    [("sidecar-event", "0.1"), ("verification-decision", "0.1"),
     ("scope-member", "0.3"), ("scope-requirement", "0.3"),
     ("scope-population", "0.3"), ("verification-decision", "0.3"),
     ("authority-checkpoint", "0.4"), ("verification-decision", "0.5"),
     ("evaluation-scope", "0.1"), ("manifest", "0.3"),
     ("retraction-receipt", "0.4"), ("work-order", "0.2"),
     ("work-order", "1.4.0"), ("unknown", "0.1")],
)
def test_prepare_rejects_unsigned_or_incompatible_domains(wallet, domain, version):
    prepare, _ = adapter()
    with pytest.raises(ValueError):
        prepare(domain, {}, wallet[1], version)


@pytest.mark.parametrize("public_bytes", [b"", b"x" * 31, b"x" * 33, "x" * 32, None])
def test_malformed_public_key_is_rejected(public_bytes):
    prepare, attach = adapter()
    with pytest.raises(ValueError, match="public key"):
        prepare("manifest", {}, public_bytes)
    with pytest.raises(ValueError, match="public key"):
        attach({}, public_bytes, b"x" * 64)


def test_no_private_key_object_is_accepted(wallet):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    with pytest.raises(ValueError, match="public key"):
        prepare("manifest", {}, signer)
    envelope, message = prepare("manifest", {}, public_bytes)
    with pytest.raises(ValueError, match="public key"):
        attach(envelope, signer, signer.sign(message))


@pytest.mark.parametrize("signature", [b"", b"x" * 63, b"x" * 65, "x" * 64, None])
def test_malformed_raw_signature_is_rejected(wallet, signature):
    prepare, attach = adapter()
    envelope, _ = prepare("manifest", {}, wallet[1])
    with pytest.raises(ValueError, match="signature"):
        attach(envelope, wallet[1], signature)


def test_wrong_wallet_and_wrong_signature_are_rejected(wallet):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    other = Ed25519PrivateKey.generate()
    other_bytes = other.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    envelope, message = prepare("manifest", {"items": [1]}, public_bytes)
    with pytest.raises(ValueError):
        attach(envelope, other_bytes, signer.sign(message))
    with pytest.raises(ValueError):
        attach(envelope, public_bytes, other.sign(message))
    with pytest.raises(ValueError):
        attach(envelope, public_bytes, signer.sign(hashlib.sha256(message).digest()))


@pytest.mark.parametrize(
    "domain,version",
    [("sidecar-event", "0.1"), ("scope-member", "0.3"),
     ("authority-checkpoint", "0.4"), ("verification-decision", "0.5")],
)
def test_attach_rejects_valid_raw_signature_for_unsigned_domain(wallet, domain, version):
    _, attach = adapter()
    signer, public_bytes = wallet
    payload = {"signature_alg": "Ed25519", "signer_key_id": key_id(signer.public_key())}
    message = canonical_bytes(domain, payload, version=version)
    payload["digest"] = hashlib.sha256(message).hexdigest()
    envelope = {"object_type": domain, "version": version, "payload": payload}
    with pytest.raises(ValueError):
        attach(envelope, public_bytes, signer.sign(message))


@pytest.mark.parametrize(
    "field,value",
    [("items", [2]), ("signature_alg", "other"), ("signer_key_id", "ed25519:" + "b" * 64),
     ("digest", "0" * 64), ("signature", "existing"), ("protocol_version", "0.5")],
)
def test_mutated_prepared_payload_is_rejected(wallet, field, value):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    envelope, message = prepare("manifest", {"items": [1]}, public_bytes)
    envelope["payload"][field] = value
    with pytest.raises(ValueError):
        attach(envelope, public_bytes, signer.sign(message))


@pytest.mark.parametrize(
    "field,value",
    [("object_type", "work-order"), ("object_type", "sidecar-event"),
     ("version", "0.5"), ("extra", "unbound")],
)
def test_mutated_envelope_is_rejected(wallet, field, value):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    envelope, message = prepare("manifest", {}, public_bytes)
    envelope[field] = value
    with pytest.raises(ValueError):
        attach(envelope, public_bytes, signer.sign(message))


def test_preparation_is_a_snapshot_and_matches_native_canonical_order(wallet):
    prepare, _ = adapter()
    payload = {"z": {"b": 2, "a": 1}, "a": ["café"]}
    envelope, message = prepare("manifest", payload, wallet[1])
    payload["a"].append("changed")
    assert envelope["payload"]["a"] == ["café"]
    _, reordered = prepare("manifest", {"a": ["café"], "z": {"a": 1, "b": 2}}, wallet[1])
    assert message == reordered


@pytest.mark.parametrize("boundary", ["depth", "nodes"])
def test_attachment_preserves_native_json_budget_boundaries(wallet, boundary):
    prepare, attach = adapter()
    signer, public_bytes = wallet
    if boundary == "depth":
        nested = 0
        for _ in range(MAX_JSON_DEPTH):
            nested = [nested]
        payload = {"nested": nested}
    else:
        # Root, list and four signature metadata values occupy six nodes.
        payload = {"items": [0] * (MAX_JSON_NODES - 6)}
    native = sign_payload("manifest", payload, signer)
    assert verify_payload("manifest", native, signer.public_key())
    envelope, message = prepare("manifest", payload, public_bytes)
    before = copy.deepcopy(envelope)
    signed = attach(envelope, public_bytes, signer.sign(message))
    assert signed == native
    assert verify_payload("manifest", signed, signer.public_key())
    assert envelope == before


@pytest.mark.parametrize("item_count", [MAX_JSON_NODES - 5, MAX_JSON_NODES - 4])
def test_prepare_rejects_payload_without_room_for_final_signature(wallet, item_count):
    prepare, _ = adapter()
    signer, public_bytes = wallet
    payload = {"items": [0] * item_count}
    with pytest.raises(ValueError, match="node budget"):
        sign_payload("manifest", payload, signer)
    with pytest.raises(ValueError, match="node budget"):
        prepare("manifest", payload, public_bytes)


@pytest.mark.parametrize("payload", [[], {"amount": -1}, {"amount": True}, {"x": 1.5}])
def test_native_payload_constraints_are_preserved(wallet, payload):
    prepare, _ = adapter()
    with pytest.raises(ValueError):
        prepare("manifest", payload, wallet[1])


def test_protocol_version_field_must_match_signing_domain(wallet):
    prepare, _ = adapter()
    with pytest.raises(ValueError, match="version"):
        prepare("manifest", {"protocol_version": "0.5"}, wallet[1], "0.1")


@pytest.mark.parametrize("envelope", [None, [], {}, {"object_type": "manifest", "version": "0.1", "payload": []}])
def test_malformed_envelope_is_rejected(wallet, envelope):
    _, attach = adapter()
    with pytest.raises(ValueError):
        attach(envelope, wallet[1], b"x" * 64)
