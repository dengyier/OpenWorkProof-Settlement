#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CARGO_HOME="$PWD/.tools/cargo"
export RUSTUP_HOME="$PWD/.tools/rustup"
export PATH="$PWD/.tools/bin:$PWD/.tools/solana-release/bin:$CARGO_HOME/bin:$PATH"
command -v cargo-build-sbf >/dev/null || { echo 'Project-local Solana tooling is not installed.' >&2; exit 1; }
if lsof -nP -iTCP:18899 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'Port 18899 is occupied; refusing to test another validator or stop its process.' >&2
  exit 1
fi
cargo build-sbf --skip-tools-install --no-rustup-override --manifest-path programs/owp_settlement/Cargo.toml
if lsof -nP -iTCP:18899 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'Port 18899 became occupied during compilation; refusing to use another validator.' >&2
  exit 1
fi
ledger_dir=$(mktemp -d "$PWD/.tools/test-ledger.XXXXXX")
solana-test-validator --ledger "$ledger_dir" --bind-address 127.0.0.1 --rpc-port 18899 \
  --faucet-port 18951 --gossip-port 18952 --dynamic-port-range 18900-18950 --quiet \
  --bpf-program 2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk target/deploy/owp_settlement.so \
  > "$ledger_dir/validator.log" 2>&1 &
validator_pid=$!
trap 'kill "$validator_pid" 2>/dev/null || true; wait "$validator_pid" 2>/dev/null || true' EXIT
for ((i=0; i<120; i++)); do
  kill -0 "$validator_pid" 2>/dev/null || { echo "Validator failed; inspect $ledger_dir/validator.log" >&2; exit 1; }
  if curl -fsS --max-time 1 -H 'Content-Type: application/json' \
      -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' http://127.0.0.1:18899 | rg -q '"ok"'; then
    SETTLEMENT_TEST_RPC=http://127.0.0.1:18899 npm run test:escrow
    exit $?
  fi
  sleep 0.5
done
echo "Local validator did not become ready; inspect $ledger_dir/validator.log" >&2
exit 1
