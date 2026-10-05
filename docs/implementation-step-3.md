# Step 3: model proposals bound to verifiable delivery

Scope: continue the existing coding-task fixture and Devnet escrow. No new settlement program, mainnet, release, contest submission, independent-customer claim or broad agent platform.

## Contract

1. A model proposes one complete replacement for `src/app.py` as JSON. The adapter computes Git blob hashes and a canonical single-file patch locally. Invalid/empty/truncated/oversized responses stop; there is no reference fallback or automatic paid-call retry.
2. The operator records exact UTF-8 API request and response bodies (without authorization headers), their SHA-256 hashes and the patch hash. Native OWP protected execution and immutable Docker tests still determine whether work succeeds. Valid JSON alone is not successful work.
3. The app-owned Developer key signs a separate, application-specific proposal attestation. Its message is `openworkproof-settlement/proposal-attestation/v1\0` followed by RFC 8785 canonical payload bytes. This is **not** a native OWP claim type or a signature by DeepSeek. It proves the operator's attribution, not that the API provider independently certified an invocation.
4. New delivery snapshots include that record in `review_snapshot`; the existing bundle digest binds it to exact customer acceptance and chain delivery. Verify signature, work order, response-to-patch mapping and body hashes before review/acceptance/release. Old snapshots without a proposal retain their old shape and hashes.
5. Wallet rejection or an account change must not commit a signature; verification, acceptance and finalized token reconciliation remain separate states. Wallet test doubles are not actual browser-wallet approval evidence.

The task and frozen tests are still fixtures. `autonomous_model: false` remains accurate: the model proposes code; it does not independently control the workflow, run tools or accept its own work. All noncustomer roles remain controlled by the application operator.

## Local configuration

Copy `.env.example` to `.env` locally and set `DEEPSEEK_API_KEY`. Restrict the file to mode 0600. Never paste secrets into chat or commit the file. The server uses Node's built-in `process.loadEnvFile` (requires Node 20.12 or newer) and only reads the project-root `.env`; existing exported environment variables take precedence. Restart the server after changing it. `OWP_MODEL` defaults to `deepseek-flash`.

The model sees only this fixture's source and expected results, not wallet keys, application credentials, other repositories or customer files. No existing DSH profile or global proxy configuration is modified. The existing DSH headless profile contains a preflight-test plugin and is not reused as an ordinary production model worker.

API behavior follows [DeepSeek's JSON mode documentation](https://api-docs.deepseek.com/guides/json_mode/): request `response_format: {"type":"json_object"}`, include JSON instructions, and reject empty/truncated responses. Request time and response size are bounded.

## Acceptance checks

- Node worker tests: computed hashes, scope, bad responses, no fallback/retry, body digests, no API key in evidence.
- Python attribution tests: signature, work order, patch mapping and tampering checks.
- Native Docker tests: good proposal becomes VERIFIED; incorrect code becomes REFUTED; proposal deletion/tampering blocks customer acceptance; exact accepted bundle authorizes release; legacy snapshots remain usable.
- Browser-code tests: cancellation, wrong account and account change during prompt cannot commit acceptance. A real Phantom test still needs a browser with the extension and explicit user signature.
- RPC regression: a nonfinal error cannot be mistaken for a finalized failure.

No chain program changes are needed. Prior deployed Devnet evidence remains a **reference-patch/software-customer** run. A real DeepSeek run must be separately recorded after credentials are available; never relabel older evidence.
