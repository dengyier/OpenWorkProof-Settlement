"""Private local subprocess boundary; customer supplies only public keys/signatures."""
import base64
import json
import sys
from pathlib import Path
from bridge.delivery_flow import DeliverySession

def main():
    request = json.load(sys.stdin)
    root = Path(request['root'])
    operation = request['operation']
    if operation == 'create':
        result = DeliverySession.create(root, bytes.fromhex(request['customer_public_key']), request['chain_terms']).summary()
    else:
        session = DeliverySession.load(root)
        if operation == 'summary':
            result = session.summary()
        elif operation == 'execute':
            result = session.execute(request['patch'], request.get('proposal'))
        elif operation == 'verify':
            result = session.verify()
        elif operation == 'prepare':
            result = session.prepare_decision(request['decision'])
        elif operation == 'commit':
            result = session.commit_decision(request['draft_id'], base64.b64decode(request['signature'], validate=True))
        elif operation == 'authorize':
            result = session.release_authorization()
        else:
            raise ValueError('Unknown delivery operation')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
