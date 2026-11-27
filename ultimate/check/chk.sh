#!/bin/bash
# chk.sh <tree> <base> <stubs> <file>: clang -fsyntax-only of one source. <tree> has app/src; <base> has sdk/ and
# app/thirdparty (the fetched Renut base); <stubs> from make_stubs.py.
T=$1; B=$2; S=$3; F=$4; X=$B/app/thirdparty/reblue-XenosRecomp/thirdparty
INC="-I$S -I$S/dk -I$T/app/src/renut_engine/sa2_compat -I$B/app/thirdparty/reblue-XenosRecomp/XenosRecomp -I$T/app/src -I$T/app/src/renut_engine -I$T/app/src/renut_engine/gpu -I$T/app/src/renut_engine/gpu/shaders -I$T/app/src/renut_engine/gpu/shaders/xenos -I$B/sdk/include -I$B/app/thirdparty/plume -I$B/app/thirdparty/imgui -I$B/sdk/thirdparty/fmt/include -I$B/sdk/thirdparty/spdlog/include -I$B/sdk/thirdparty/simde -I$B/sdk/thirdparty/tomlplusplus/include -I$B/sdk/thirdparty/stb -I$X/xxHash -I$X/zstd/lib -I$X/smol-v/source -I$B/app/src -I$B/app/thirdparty/plume/contrib/volk -I$B/sdk/thirdparty/sdl3/include -I$B/sdk/thirdparty/o1heap/o1heap -I$B/sdk/src/core -I$B/sdk/thirdparty/vulkan-headers/include -I/home/claude/chanseyisthebest/renut_nx_ultimate_base/app/thirdparty/plume/contrib/VulkanMemoryAllocator/include"
for d in $B/app/thirdparty/plume/*/; do INC="$INC -I$d"; done
clang++ -std=c++23 -include $S/generated/default/alice_init.h -fsyntax-only -w -DPLUME_DEKO3D=1 -ferror-limit=60 $INC "$F" 2>&1
