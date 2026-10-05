#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OWP_NETWORK=devnet
export OWP_RPC=https://api.devnet.solana.com
export OWP_VERIFIER_IMAGE="${OWP_VERIFIER_IMAGE:-owp-settlement/verifier@sha256:bb0e6761c1251dc85ac3a2f78ebfd15df2f94f7a2922bf6dfe7430d8b93f9fa5}"
export OWP_HELPER_IMAGE="${OWP_HELPER_IMAGE:-openworkproof/trusted-helper-candidate@sha256:76538b596e28503fdf6f0a69a889a824f3a0603807ddb74d55077e0e1e3e0ae5}"
docker info >/dev/null
docker image inspect "$OWP_VERIFIER_IMAGE" >/dev/null
docker image inspect "$OWP_HELPER_IMAGE" >/dev/null
exec node app/server.cjs
