"""App-owned attribution, not a provider signature or a new native OWP claim."""
import base64
import hashlib
import json

import rfc8785
from cryptography.exceptions import InvalidSignature

SOURCE = 'def average(values):\n    return sum(values)\n'
DOMAIN = b'openworkproof-settlement/proposal-attestation/v1\0'


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def replacement_patch(proposal):
    content = proposal.get('content') if isinstance(proposal, dict) else None
    if not isinstance(proposal, dict) or set(proposal) != {'path', 'content'} or proposal['path'] != 'src/app.py' or not isinstance(content, str) or not content.endswith('\n') or '\r' in content or '\0' in content or len(content.encode()) > 8192 or content == SOURCE:
        raise ValueError('Invalid bounded single-file proposal')
    blob = lambda text: hashlib.sha1(f'blob {len(text.encode())}\0'.encode() + text.encode()).hexdigest()
    lines = content[:-1].split('\n')
    return (f'diff --git a/src/app.py b/src/app.py\nindex {blob(SOURCE)}..{blob(content)} 100644\n'
            f'--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,{len(lines)} @@\n'
            + ''.join(f'-{line}\n' for line in SOURCE.rstrip('\n').split('\n')) + ''.join(f'+{line}\n' for line in lines))


def _validate(proposal, patch):
    fields = {'schema_version', 'mode', 'live_model', 'patch_sha256'}
    if not isinstance(proposal, dict):
        raise ValueError('Invalid proposal evidence')
    live = proposal.get('mode') == 'deepseek'
    if live:
        fields |= {'model', 'request_body', 'response_body', 'request_sha256', 'response_sha256'}
    if set(proposal) != fields or proposal['schema_version'] != 'owp-settlement-proposal/1' or proposal['mode'] not in ('reference', 'deepseek') or proposal['live_model'] is not live or proposal['patch_sha256'] != _sha(patch):
        raise ValueError('Proposal identity or patch changed')
    if not live:
        return
    if not isinstance(proposal['model'], str) or not 1 <= len(proposal['model']) <= 128:
        raise ValueError('Invalid proposal model')
    for name in ('request', 'response'):
        body = proposal[f'{name}_body']
        if not isinstance(body, str) or len(body.encode()) > 131072 or _sha(body) != proposal[f'{name}_sha256']:
            raise ValueError('Proposal API body changed')
    try:
        request = json.loads(proposal['request_body'])
        response = json.loads(proposal['response_body'])
        choices = response['choices']
        if request['model'] != proposal['model'] or request['response_format'] != {'type': 'json_object'} or len(choices) != 1 or choices[0]['finish_reason'] != 'stop':
            raise ValueError('Incomplete proposal response')
        if replacement_patch(json.loads(choices[0]['message']['content'])) != patch:
            raise ValueError('Proposal response does not produce this patch')
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid proposal response') from error


def attest_proposal(proposal, patch, work_order_digest, private_key):
    _validate(proposal, patch)
    payload = {'schema_version': 'owp-settlement-operator-proposal-attestation/1', 'work_order_digest': work_order_digest, 'proposal': proposal}
    signature = private_key.sign(DOMAIN + rfc8785.dumps(payload))
    return {'payload': payload, 'signature_base64': base64.b64encode(signature).decode()}


def verify_proposal(record, patch, work_order_digest, public_key):
    try:
        payload = record['payload']
        if set(record) != {'payload', 'signature_base64'} or set(payload) != {'schema_version', 'work_order_digest', 'proposal'} or payload['schema_version'] != 'owp-settlement-operator-proposal-attestation/1' or payload['work_order_digest'] != work_order_digest:
            raise ValueError('Proposal attestation identity changed')
        public_key.verify(base64.b64decode(record['signature_base64'], validate=True), DOMAIN + rfc8785.dumps(payload))
        _validate(payload['proposal'], patch)
    except (InvalidSignature, KeyError, TypeError) as error:
        raise ValueError('Invalid operator proposal signature') from error
