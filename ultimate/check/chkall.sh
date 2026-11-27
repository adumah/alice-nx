#!/bin/bash
# chkall.sh <tree> <base> <stubs> [out-dir]: syntax-check every engine source and the app's own sources; prints failures.
T=$1; B=$2; S=$3; O=${4:-/tmp/chk_out}; D=$(cd "$(dirname "$0")" && pwd)
rm -rf "$O"; mkdir -p "$O"
find "$T/app/src" -name '*.cpp' | sort | xargs -P "${JOBS:-8}" -I{} bash -c \
  'o='"$O"'/$(echo {} | sed "s#.*/app/src/##; s#/#_#g").log; '"$D"'/chk.sh '"$T $B $S"' {} > $o 2>&1; grep -q "error" $o || rm $o'
n=0; for f in "$O"/*.log; do [ -f "$f" ] && { echo "$(basename "$f"): $(grep -c 'error' "$f") errors"; n=$((n+1)); }; done
echo "files with errors: $n"
