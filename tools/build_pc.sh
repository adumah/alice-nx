#!/usr/bin/env bash
# Configures (first time) and builds the Linux PC build: out/pc/alice. Logs: out/pc_configure.log, out/pc_build.log.
#
#   tools/build_pc.sh [-j N]
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
sa2="${SA2_NX:-$root/../sa2-nx}"
build="$root/out/pc"
jobs="${2:-$(nproc)}"
# Renut's renderer is linked (ALICE_RENUT=OFF leaves it out); it then runs with --sa2_renderer=renut, and the emulated
# GPU stays the PC's default and reference. Each new shader it meets is captured to out/pc/shader_capture/ and
# translated by the next build.
renut="${ALICE_RENUT:-ON}"
mkdir -p "$root/out"
if [[ ! -f "$build/build.ninja" ]]; then
  cmake -S "$root/app" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DALICE_RENUT_RENDERER="$renut" \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2 \
    -DREXSDK_DIR="$sa2/sdk" > "$root/out/pc_configure.log" 2>&1 \
    || { tail -n 30 "$root/out/pc_configure.log"; exit 1; }
fi
set +e
cmake --build "$build" --target alice -j "$jobs" > "$root/out/pc_build.log" 2>&1
code=$?
set -e
grep -E 'error:|FAILED' "$root/out/pc_build.log" | head -n 40 || true  # no match is the good case
tail -n 3 "$root/out/pc_build.log"
exit $code
