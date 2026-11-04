#!/usr/bin/env bash
# Translates Default.xex to C++ with the sa2-nx host code generator (Linux counterpart of sa2-nx tools/codegen.ps1).
#
#   tools/codegen.sh [--flavor classic|optimised] [extra rexglue codegen options, e.g. --ignore-stamp]
#
# --flavor (default: keep what app/codegen_flavor.toml says): optimised copies app/perf_overrides.toml to
# app/codegen_flavor.toml; classic empties it. Then tools/post_codegen.py runs the flavour's post-codegen steps.
#
# Input:   assets/game_root/Default.xex, app/alice_manifest.toml
# Output:  app/generated/ (not committed), out/codegen.log, out/default_image.bin (the decrypted image)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
sa2="${SA2_NX:-$root/../sa2-nx}"
rexglue="${REXGLUE:-$sa2/sdk/out/linux-amd64/rexglue}"
[[ -x "$rexglue" ]] || { echo "rexglue not found at $rexglue; build it first" >&2; exit 1; }
flavor=""
if [[ "${1:-}" == "--flavor" ]]; then flavor="${2:?--flavor classic|optimised}"; shift 2; fi
case "$flavor" in
  optimised) { echo "# optimised codegen: written by tools/codegen.sh --flavor optimised from perf_overrides.toml."; \
               cat "$root/app/perf_overrides.toml"; } > "$root/app/codegen_flavor.toml" ;;
  classic) printf '# classic codegen: no extra options (tools/codegen.sh --flavor classic writes this file; --flavor optimised\n# copies perf_overrides.toml here).\n' > "$root/app/codegen_flavor.toml" ;;
  "") ;;
  *) echo "unknown flavor $flavor" >&2; exit 1 ;;
esac
mkdir -p "$root/out"
export REX_MAX_JUMP_TABLE_ENTRIES=1024
export REXGLUE_DUMP_IMAGE="$root/out/default_image.bin"
cd "$root/app"
set +e
"$rexglue" codegen alice_manifest.toml "$@" > "$root/out/codegen.log" 2>&1
code=$?
set -e
tail -n 30 "$root/out/codegen.log"
[[ $code -eq 0 ]] || exit $code
REXSDK_DIR="$sa2/sdk" python3 "$root/tools/post_codegen.py"
