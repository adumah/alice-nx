#!/usr/bin/env bash
# Builds the code generator (rexglue) from the SDK inside this tree (the Renut base's sdk/). Replaces Alice's own
# tools/build_sdk.sh, which built sa2-nx's SDK in a tree beside this one.
# Logs: out_sdk_configure.log, out_sdk_build.log. Output: sdk/out/linux-amd64/rexglue
#
#   tools/build_sdk.sh [-j N]
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
jobs="$(nproc)"
if [[ "${1:-}" == "-j" && -n "${2:-}" ]]; then jobs="$2"; fi
cd "$root"
[[ -d sdk ]] || { echo "no sdk/ in $root" >&2; exit 1; }
# The base vendors its third-party code; only a tree that does not has a fetch script.
if [[ -f tools/fetch_thirdparty.py ]]; then python3 tools/fetch_thirdparty.py; fi
# -march=x86-64-v2: the SDK's byte-swapping helpers use SSSE3.
cmake -S sdk -B out/host -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2 \
  -DREXGLUE_ENABLE_TRACY=OFF > out_sdk_configure.log 2>&1 \
  || { tail -n 40 out_sdk_configure.log; exit 1; }
cmake --build out/host --target rexglue -j "$jobs" > out_sdk_build.log 2>&1 \
  || { grep -E 'error:|FAILED' out_sdk_build.log | head -n 40; exit 1; }
test -x sdk/out/linux-amd64/rexglue
echo "built $root/sdk/out/linux-amd64/rexglue"
