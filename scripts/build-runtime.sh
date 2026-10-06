#!/usr/bin/env bash
# Rebuild from public pinned inputs; no wallet, model API, registry push or Devnet write.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
build_root="${1:-$project_root/.tools/runtime-build}"
core_revision=0dbc32b648f31343a5f9ccabf678f1e1075e60f1
base_image=docker.io/library/python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
python_bin="${PYTHON:-python3}"
for command_name in git docker curl tar "$python_bin"; do command -v "$command_name" >/dev/null; done
docker buildx version >/dev/null
engine_arch="$(docker info --format '{{.Architecture}}')"
if [[ "$engine_arch" != aarch64 && "$engine_arch" != arm64 ]]; then
  echo 'This recipe requires a native ARM64 Docker engine; x86/QEMU is not validated.' >&2
  exit 1
fi
if [[ -e "$build_root" ]]; then
  echo "Use a fresh build directory; refusing to overwrite $build_root" >&2
  exit 1
fi
mkdir -p "$build_root"
build_root="$(cd "$build_root" && pwd)"
git init "$build_root/core"
git -C "$build_root/core" remote add origin https://github.com/dengyier/OpenWorkProof.git
git -C "$build_root/core" fetch --depth=1 origin "$core_revision"
git -C "$build_root/core" checkout --detach "$core_revision"
"$python_bin" "$project_root/scripts/fetch-runtime-inputs.py" --core "$build_root/core" --output "$build_root/inputs"
"$python_bin" "$build_root/core/supply-chain/images/prepare_context.py" \
  --repo "$build_root/core" --source-revision "$core_revision" \
  --wheelhouse "$build_root/inputs/wheels" --deb-closure "$build_root/inputs/debs" \
  --output-root "$build_root/contexts"
docker pull --platform linux/arm64 "$base_image"

build_image() {
  local role="$1" context="$2"
  shift 2
  local tag="owp-settlement/rebuild-$role:core-${core_revision:0:12}"
  docker buildx build --platform linux/arm64 --network none --pull=false --no-cache \
    --provenance=false --build-arg "OWP_SOURCE_REVISION=$core_revision" \
    "$@" --tag "$tag" --output "type=docker,dest=$build_root/$role.tar" "$context"
  "$python_bin" "$build_root/core/supply-chain/images/convert_docker_archive.py" "$build_root/$role.tar"
  docker load --input "$build_root/$role.tar"
}

image_reference() {
  # Docker load must actually register the manifest digest. No fabricated digest aliases.
  docker image inspect "owp-settlement/rebuild-$1:core-${core_revision:0:12}" | "$python_bin" -c '
import json, sys
image = json.load(sys.stdin)[0]
refs = image.get("RepoDigests", [])
if len(refs) != 1 or "@sha256:" not in refs[0]:
    raise SystemExit("Expected one loaded immutable RepoDigest; Docker 29 containerd image store is required")
print(refs[0])'
}

build_image execution "$build_root/contexts/execution"
execution_reference="$(image_reference execution)"
build_image helper "$build_root/contexts/trusted-helper"
helper_reference="$(image_reference helper)"
# Give BuildKit the actual local manifest, rather than querying an unpublished registry name.
mkdir "$build_root/execution-layout"
tar -xf "$build_root/execution.tar" -C "$build_root/execution-layout"
build_image verifier "$project_root/runtime" \
  --build-context "owp_execution=oci-layout://$build_root/execution-layout@${execution_reference##*@}" \
  --build-arg OWP_EXECUTION_IMAGE=owp_execution
verifier_reference="$(image_reference verifier)"
printf "export OWP_VERIFIER_IMAGE='%s'\nexport OWP_HELPER_IMAGE='%s'\n" \
  "$verifier_reference" "$helper_reference" > "$build_root/runtime.env"
echo "Runtime ready. Source $build_root/runtime.env before testing or starting the app."
