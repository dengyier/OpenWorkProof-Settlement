import copy
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from bridge.proposal_evidence import replacement_patch, attest_proposal, verify_proposal


def fixture_proposal():
    # Recorded API shape is a test double, not evidence of a real API call.
    content = 'def average(values):\n    return sum(values) / len(values)\n'
    patch = replacement_patch({'path': 'src/app.py', 'content': content})
    request = json.dumps({'model': 'test-model', 'response_format': {'type': 'json_object'}})
    response = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'path': 'src/app.py', 'content': content})}}]})
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    return patch, {'schema_version': 'owp-settlement-proposal/1', 'mode': 'deepseek', 'model': 'test-model', 'live_model': True,
                   'patch_sha256': digest(patch), 'request_body': request, 'response_body': response, 'request_sha256': digest(request), 'response_sha256': digest(response)}


def test_signed_operator_proposal_binds_work_and_patch():
    patch, proposal = fixture_proposal()
    key = Ed25519PrivateKey.generate()
    record = attest_proposal(proposal, patch, 'a' * 64, key)
    verify_proposal(record, patch, 'a' * 64, key.public_key())
    for field in ('mode', 'model', 'response_body', 'patch_sha256'):
        changed = copy.deepcopy(record)
        changed['payload']['proposal'][field] = 'tampered'
        with pytest.raises(ValueError):
            verify_proposal(changed, patch, 'a' * 64, key.public_key())
    for wrong_patch, wrong_work, wrong_key in [(patch + '\n', 'a' * 64, key.public_key()), (patch, 'b' * 64, key.public_key()), (patch, 'a' * 64, Ed25519PrivateKey.generate().public_key())]:
        with pytest.raises(ValueError):
            verify_proposal(record, wrong_patch, wrong_work, wrong_key)


def test_adapter_rejects_response_patch_mismatch_even_before_signing():
    patch, proposal = fixture_proposal()
    with pytest.raises(ValueError):
        attest_proposal(proposal, patch + '\n', 'a' * 64, Ed25519PrivateKey.generate())
    proposal['response_body'] = proposal['response_body'].replace('src/app.py', 'tests/test.py')
    proposal['response_sha256'] = hashlib.sha256(proposal['response_body'].encode()).hexdigest()
    with pytest.raises(ValueError):
        attest_proposal(proposal, patch, 'a' * 64, Ed25519PrivateKey.generate())
