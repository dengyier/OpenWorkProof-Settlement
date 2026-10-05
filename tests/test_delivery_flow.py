import base64
import json
from datetime import datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@pytest.fixture
def session(tmp_path):
    from bridge.delivery_flow import DeliverySession

    customer = Ed25519PrivateKey.generate()
    terms = {"network_genesis": "local", "program_id": "program", "provider": "provider",
             "verifier": "verifier", "mint": "mint", "amount": "100", "deadline": "9999999999",
             "customer": "customer"}
    return DeliverySession.create(tmp_path / ".tools" / "case", customer.public_key().public_bytes_raw(), terms), customer


def fixed_patch(session, replacement="return sum(values) / len(values)"):
    from openworkproof.repo_tools import git_blob_oid
    old = b"def average(values):\n    return sum(values)\n"
    new = f"def average(values):\n    {replacement}\n".encode()
    return ("diff --git a/src/app.py b/src/app.py\n"
            f"index {git_blob_oid(old)}..{git_blob_oid(new)} 100644\n"
            "--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,2 @@\n"
            " def average(values):\n-    return sum(values)\n"
            f"+    {replacement}\n")


def test_native_session_reload_and_patch(session):
    from bridge.delivery_flow import DeliverySession
    flow, _ = session
    before = flow.summary()
    assert before["tests"]["baseline"]["exit_code"] != 0
    assert "2 failed, 1 passed" in before["tests"]["baseline"]["stdout"]
    after = flow.execute(fixed_patch(flow))
    assert after["tests"]["verifier"]["exit_code"] == 0
    observation = after["tests"]["verifier"]["native_execution_observation"]
    assert observation["result"]["actual_exit_code"] == 0
    assert observation["result"]["stdout_bytes"] > 0
    assert "3 passed" in after["tests"]["clean_rerun"]["stdout"]
    assert after["patch"]["receipt_digest"]
    reloaded = DeliverySession.load(flow.root)
    assert reloaded.summary()["work_order_digest"] == before["work_order_digest"]
    assert reloaded.work_order.key_bindings == flow.work_order.key_bindings
    assert not (flow.root / "keys" / "acceptor.key").exists()
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in (flow.root / "keys").glob("*.key"))


def test_delayed_wallet_funding_does_not_backdate_verifier_grant(session, monkeypatch):
    from bridge import delivery_flow
    flow, _ = session
    later = delivery_flow._now() + timedelta(minutes=6)
    monkeypatch.setattr(delivery_flow, "_now", lambda: later)
    assert flow.execute(fixed_patch(flow))["verification_decision"] == "VERIFIED"


def test_interrupted_verifier_issuance_resumes_without_reapplying_patch(session, monkeypatch):
    from bridge import delivery_flow
    flow, _ = session
    issue = delivery_flow.evidence.issue_child_grant
    def interrupted(*args, **kwargs):
        raise RuntimeError("interrupted verifier issuance")
    monkeypatch.setattr(delivery_flow.evidence, "issue_child_grant", interrupted)
    with pytest.raises(RuntimeError, match="interrupted verifier issuance"):
        flow.execute(fixed_patch(flow))
    before = flow.summary()["patch"]
    monkeypatch.setattr(delivery_flow.evidence, "issue_child_grant", issue)
    resumed = delivery_flow.DeliverySession.load(flow.root)
    result = resumed.verify()
    assert result["verification_decision"] == "VERIFIED"
    assert result["patch"] == before
    receipts = flow._context(delivery_flow._now()).ledger_prefix.receipts
    assert len([r for r in receipts if getattr(r, "tool_name", None) == "owp.apply_patch"]) == 1
    with pytest.raises(ValueError, match="unverified applied patch"):
        resumed.verify()


def test_operator_proposal_is_frozen_and_customer_accepts_same_bundle(session):
    from test_proposal_evidence import fixture_proposal
    flow, customer = session
    patch, proposal = fixture_proposal()
    result = flow.execute(patch, proposal)
    assert result['verification_decision'] == 'VERIFIED'
    bundle = json.loads((flow.root / 'delivery-bundle.json').read_bytes())
    assert bundle['review_snapshot']['proposal'] == result['proposal']
    original = flow._state['proposal']
    flow._state['proposal'] = json.loads(json.dumps(original))
    flow._state['proposal']['payload']['proposal']['response_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='signature'):
        flow.prepare_decision()
    flow._state['proposal'] = original
    del flow._state['proposal']
    with pytest.raises(ValueError, match='metadata changed'):
        flow.summary()
    flow._state['proposal'] = original
    draft = flow.prepare_decision()
    accepted = flow.commit_decision(draft['draft_id'], customer.sign(base64.b64decode(draft['message_base64'])))
    assert accepted['bundle_digest'] == result['bundle_digest']
    assert flow.release_authorization()['bundle_digest'] == result['bundle_digest']


def test_well_formed_model_response_does_not_imply_correct_work(session):
    import hashlib
    from bridge.proposal_evidence import replacement_patch
    from test_proposal_evidence import fixture_proposal
    flow, _ = session
    _, proposal = fixture_proposal()
    body = json.loads(proposal['response_body'])
    replacement = {'path': 'src/app.py', 'content': 'def average(values):\n    return 0\n'}
    body['choices'][0]['message']['content'] = json.dumps(replacement)
    proposal['response_body'] = json.dumps(body)
    proposal['response_sha256'] = hashlib.sha256(proposal['response_body'].encode()).hexdigest()
    patch = replacement_patch(replacement)
    proposal['patch_sha256'] = hashlib.sha256(patch.encode()).hexdigest()
    result = flow.execute(patch, proposal)
    assert result['verification_decision'] == 'REFUTED'
    assert result['bundle_digest'] is None
    with pytest.raises((ValueError, RuntimeError)):
        flow.prepare_decision()


def test_customer_decision_and_release(session):
    flow, customer = session
    delivery = flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    assert flow.summary()["bundle_digest"] == delivery["bundle_digest"]
    assert flow.summary()["acceptance_request_expires_at"] == draft["request_expires_at"]
    expiry = datetime.fromisoformat(draft["request_expires_at"].replace("Z", "+00:00"))
    prepared = datetime.fromisoformat(draft["prepared_at"].replace("Z", "+00:00"))
    assert expiry <= flow.work_order.deadline
    assert expiry - prepared == timedelta(hours=1)
    result = flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    assert result["acceptance_decision"] == "ACCEPTED"
    assert result["bundle_digest"] == delivery["bundle_digest"]
    from bridge.delivery_flow import DeliverySession
    assert DeliverySession.load(flow.root).summary()["bundle_digest"] == delivery["bundle_digest"]
    assert flow.release_authorization()["acceptance_digest"] == result["acceptance_digest"]
    with pytest.raises(ValueError):
        flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))


def test_failed_tests_block_acceptance_and_release(session):
    flow, _ = session
    result = flow.execute(fixed_patch(flow, "return 0"))
    assert result["tests"]["verifier"]["exit_code"] != 0
    with pytest.raises((ValueError, RuntimeError)):
        flow.prepare_decision()
    with pytest.raises((ValueError, RuntimeError)):
        flow.release_authorization()


def test_wrong_customer_and_stale_draft(session):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    first = flow.prepare_decision()
    with pytest.raises(ValueError):
        flow.commit_decision(first["draft_id"], Ed25519PrivateKey.generate().sign(base64.b64decode(first["message_base64"])))
    second = flow.prepare_decision()
    with pytest.raises(ValueError):
        flow.commit_decision(first["draft_id"], customer.sign(base64.b64decode(first["message_base64"])))
    flow.commit_decision(second["draft_id"], customer.sign(base64.b64decode(second["message_base64"])))


def test_rejection_never_releases(session):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision("REJECTED")
    result = flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    assert result["acceptance_decision"] == "REJECTED"
    with pytest.raises((ValueError, RuntimeError)):
        flow.release_authorization()


def test_mutated_evidence_blocks_release(session):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    evidence_file = next(flow.evidence_root.glob("verifier-result/*.json"))
    evidence_file.write_text("{}")
    with pytest.raises((ValueError, RuntimeError)):
        flow.release_authorization()


def test_mutated_terms_block_release(session):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    flow.chain_terms["amount"] = "101"
    with pytest.raises(ValueError, match="chain terms"):
        flow.release_authorization()


def test_mutated_wallet_draft_is_rejected(session):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    flow._state["draft"]["envelope"]["payload"]["accepted_at"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))


def test_frozen_bundle_tampering_blocks_acceptance(session):
    flow, _ = session
    flow.execute(fixed_patch(flow))
    bundle = flow.root / "delivery-bundle.json"
    bundle.chmod(0o600)
    bundle.write_bytes(b"{}")
    with pytest.raises(ValueError, match="bundle changed"):
        flow.prepare_decision()


def test_persisted_job_id_must_match_native_work_order(session):
    from bridge.delivery_flow import DeliverySession
    flow, _ = session
    state_path = flow.root / "session.json"
    state = json.loads(state_path.read_text())
    state["job_id"] = "0" * 64
    state_path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="job"):
        DeliverySession.load(flow.root)
    flow.job_id = "0" * 64
    with pytest.raises(ValueError, match="job"):
        flow.summary()
    with pytest.raises(ValueError, match="job"):
        flow.release_authorization()


@pytest.mark.parametrize("field", ["patch", "native_test", "clean_output"])
def test_review_metadata_tampering_blocks_display_decision_and_release(session, field):
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    if field == "patch":
        flow._state["patch"]["text"] = "fake patch"
    elif field == "native_test":
        flow._state["tests"]["verifier"]["exit_code"] = 7
    else:
        flow._state["tests"]["clean_rerun"]["stdout"] = "fake output"
    for call in (flow.summary, flow.prepare_decision, flow.release_authorization):
        with pytest.raises((ValueError, RuntimeError)):
            call()


@pytest.mark.parametrize("decision", ["ACCEPTED", "REJECTED"])
def test_reload_recovers_native_terminal_after_cache_write_crash(session, decision):
    from bridge.delivery_flow import DeliverySession
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision(decision)
    result = flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    state_path = flow.root / "session.json"
    state = json.loads(state_path.read_text())
    state["terminal"] = None
    state["draft"] = draft
    state_path.write_text(json.dumps(state))
    (flow.root / "customer-decision.json").unlink()
    reloaded = DeliverySession.load(flow.root)
    recovered = reloaded.summary()
    assert recovered["acceptance_digest"] == result["acceptance_digest"]
    assert recovered["acceptance_decision"] == decision
    persisted = json.loads(state_path.read_text())
    assert persisted["terminal"]["digest"] == result["acceptance_digest"]
    assert persisted["draft"] is None
    assert json.loads((flow.root / "customer-decision.json").read_text())["digest"] == result["acceptance_digest"]
    if decision == "ACCEPTED":
        assert reloaded.release_authorization()["acceptance_digest"] == result["acceptance_digest"]
    else:
        with pytest.raises(ValueError):
            reloaded.release_authorization()


def test_reload_refuses_terminal_cache_mismatch(session):
    from bridge.delivery_flow import DeliverySession
    flow, customer = session
    flow.execute(fixed_patch(flow))
    draft = flow.prepare_decision()
    flow.commit_decision(draft["draft_id"], customer.sign(base64.b64decode(draft["message_base64"])))
    state_path = flow.root / "session.json"
    state = json.loads(state_path.read_text())
    state["terminal"]["digest"] = "0" * 64
    state_path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="terminal"):
        DeliverySession.load(flow.root)
