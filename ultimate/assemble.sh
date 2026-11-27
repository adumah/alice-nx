#!/usr/bin/env bash
# Builds the tree the Switch build runs in: the Renut base's SDK, third-party code and tools, with this repository's
# Alice app and tools on top.
#
#   ultimate/assemble.sh <base checkout> <this repository> <destination>
#
# What comes from where:
#   base : sdk/ (ReXGlue SDK with the Horizon layer and the codegen changes), app/thirdparty/ (plume, uam, imgui, smaa,
#          Renut's XenosRecomp), tools/ (shader tools, deko3d tools), docs/ of the base.
#   here : app/ (the Alice game layer and its renderer copy), tools/ (Alice's build scripts; they win over the base's
#          files of the same name), docs/, README, LICENSE.
# The base's own game layer (Katamari: app/src, app/CMakeLists.txt, tomls, pgo/, dist/) is left out.
# Alice's scripts and CMake look for "the sa2-nx tree" beside the SDK; the destination plays that role (SA2_NX=<dest>).
set -euo pipefail
base="$(cd "$1" && pwd)"
here="$(cd "$2" && pwd)"
dest="$3"
mkdir -p "$dest"
dest="$(cd "$dest" && pwd)"

# tar instead of rsync: no extra tool, and an exclude list that names exactly what is left out.
tar -C "$base" -cf - \
  --exclude='./.git' \
  --exclude='./app/src' --exclude='./app/cmake' --exclude='./app/config' --exclude='./app/icon' \
  --exclude='./app/CMakeLists*.txt' --exclude='./app/CMakeLists-linux.cmake' --exclude='./app/CMakePresets.json' --exclude='./app/*.toml' \
  --exclude='./app/indirect_promotions.txt' --exclude='./app/README.md' \
  --exclude='./pgo' --exclude='./pgo-inplace' --exclude='./dist' --exclude='./shaders' . | tar -C "$dest" -xf -

overlay() { mkdir -p "$dest/$1"; tar -C "$here/$1" -cf - . | tar -C "$dest/$1" -xf -; }
overlay app
overlay tools
overlay docs
cp -f "$here/README.md" "$here/LICENSE" "$here/THIRD_PARTY_NOTICES.md" "$dest/"

# The base's shader tools name Windows binaries (.exe); make them portable (every edit is checked).
python3 -I "$here/ultimate/patch_base_tools.py" "$dest"

# The in-tree SDK build (Alice's tools/build_sdk.sh looked for sa2-nx's fetch script, which the base does not have).
install -m 0755 "$here/ultimate/build_sdk.sh" "$dest/tools/build_sdk.sh"

{
  echo "base_repository=$(sed -n 's/^repository=//p' "$here/ultimate/BASE_REF")"
  echo "base_sha=$(sed -n 's/^sha=//p' "$here/ultimate/BASE_REF")"
  echo "alice_sha=${GITHUB_SHA:-unknown}"
} > "$dest/ULTIMATE_REFS"

echo "assemble: $dest"
for p in sdk/CMakeLists.txt app/CMakeLists.txt app/thirdparty/uam app/thirdparty/reblue-XenosRecomp \
         tools/switch/cmake/switch-devkitA64.cmake tools/build_switch.sh tools/post_codegen.py; do
  [[ -e "$dest/$p" ]] || { echo "assemble: missing $p" >&2; exit 1; }
done
