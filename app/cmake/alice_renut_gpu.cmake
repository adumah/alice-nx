# Renut's Direct3D-level renderer for Alice (reNut by masterspike52, through banjo-nx, sa2-nx and mhnwis-nx; sa2-nx's
# cmake/sa2_renut_gpu.cmake, PC part). The renderer's code is app/src/renut_engine, sa2-nx's with its hooks retargeted
# to this game's Direct3D (docs/d3d-census.md). Its third-party code (plume, Renut's
# XenosRecomp with DXC, zstd, smol-v and xxHash, Dear ImGui) and tools are sa2-nx's, from the tree beside this one.
#
# An OBJECT library, not a static one: its hooks replace the generated code's weak sub_X definitions, and a static
# archive's members are only pulled in for undefined symbols, so the hooks would silently not be linked.


# madlice-nx (ultimate): the tree is the Renut ultimate base (ultimate/assemble.sh) with Alice's game layer on it, so its
# thirdparty (plume, XenosRecomp, uam, imgui) is app/thirdparty and its tools are the ones beside app/.
set(RENUT_THIRDPARTY_DIR "${CMAKE_SOURCE_DIR}/thirdparty")
set(RENUT_TOOLS_DIR "${CMAKE_SOURCE_DIR}/../tools")

# The shader containers the shader cache is built from: the ones Renut captured at runtime (renut_shader_capture_dir:
# a shader its cache lacks is written next to the executable, and the next build adds it). Game data: in the build
# tree's parent out/, never committed. It exists from the start, so gpu.cmake's N&B dump step never runs.
set(RENUT_SHADER_DUMP_DIR "${CMAKE_SOURCE_DIR}/../out/renut_shader_dump")
file(MAKE_DIRECTORY "${RENUT_SHADER_DUMP_DIR}")
set(RENUT_ASSETS_DIR "${CMAKE_SOURCE_DIR}/../assets/game_root" CACHE PATH "The game's files")
set(RENUT_SHADER_CAPTURE_DIR "${CMAKE_BINARY_DIR}/shader_capture" CACHE PATH
    "Where Renut, run from the build directory, captures the shaders its cache lacks")

# Renut's XenosRecomp is built as an ExternalProject (gpu.cmake): it gets this build's host toolchain flags too.
set(BANJO_RENUT_XENOS_RECOMP_ARGS "")
foreach(_banjo_var CMAKE_C_COMPILER_TARGET CMAKE_CXX_COMPILER_TARGET CMAKE_LINKER_TYPE CMAKE_C_FLAGS CMAKE_CXX_FLAGS
                   CMAKE_AR)
    if(DEFINED ${_banjo_var} AND NOT "${${_banjo_var}}" STREQUAL "")
        list(APPEND BANJO_RENUT_XENOS_RECOMP_ARGS "-D${_banjo_var}=${${_banjo_var}}")
    endif()
endforeach()

# The Switch build (sa2-nx's Switch part): plume's deko3d back end (banjo-nx) with uam for the shader variants on the
# console, no Vulkan driver (REXGLUE_SWITCH_NO_NVK), the host shaders' deko3d blobs made with the PC tools
# (tools/deko3d_build_tools.sh), and the game's shaders from a PC build: the GLSL package and the SPIR-V cache in
# out/renut_switch (tools/renut/switch_shaders.sh). Those two files are game data: the NRO they go into is for the
# player's own console and is never distributed.
if(REXGLUE_PLATFORM_SWITCH)
    set(PLUME_PLATFORM_SWITCH ON CACHE BOOL "" FORCE)
    set(PLUME_SWITCH_DEVKITPRO "${DEVKITPRO}" CACHE PATH "" FORCE)
    set(PLUME_SWITCH_NVK_ROOT "${REXGLUE_SWITCH_NVK_SDK}" CACHE PATH "" FORCE)
    set(PLUME_SWITCH_NVK_LIBRARY "${REXGLUE_SWITCH_NVK_SDK}/lib/libvulkan.a" CACHE FILEPATH "" FORCE)
    # The base's SDK says REXGLUE_SWITCH_NVK (OFF: no Vulkan driver linked; Renut then runs on deko3d only).
    set(PLUME_SWITCH_NVK_LINK ${REXGLUE_SWITCH_NVK} CACHE BOOL "" FORCE)
    set(PLUME_SWITCH_UAM_DIR "${RENUT_THIRDPARTY_DIR}/uam" CACHE PATH "" FORCE)
    set(PLUME_DEKO3D ON CACHE BOOL "deko3d back end (Switch)" FORCE)
    set(BANJO_DEKO3D_HOST_SHADERS ON)
    set(BANJO_DEKO3D_SPIRV_CROSS "${CMAKE_SOURCE_DIR}/../out/deko3d_tools/spirv-cross-build/spirv-cross" CACHE FILEPATH
        "SPIRV-Cross for the deko3d host shaders (tools/deko3d_build_tools.sh)")
    set(BANJO_DEKO3D_UAM "${CMAKE_SOURCE_DIR}/../out/deko3d_tools/uam-build/uam" CACHE FILEPATH
        "uam built for the PC, for the deko3d host shaders (tools/deko3d_build_tools.sh)")
    foreach(_alice_tool BANJO_DEKO3D_SPIRV_CROSS BANJO_DEKO3D_UAM)
        if(NOT EXISTS "${${_alice_tool}}")
            message(FATAL_ERROR "No ${${_alice_tool}}: run tools/deko3d_build_tools.sh first")
        endif()
    endforeach()
    set(_alice_renut_shaders "${CMAKE_SOURCE_DIR}/../out/renut_switch")
    set(BANJO_DEKO3D_GLSL_CPP "${_alice_renut_shaders}/deko3d_glsl_switch.cpp" CACHE FILEPATH
        "The deko3d GLSL package's source (tools/renut/switch_shaders.sh)" FORCE)
    set(BANJO_RENUT_SHADER_CACHE_CPP "${_alice_renut_shaders}/shader_cache_switch.cpp" CACHE FILEPATH
        "Renut's shader cache for the Switch build (tools/renut/switch_shaders.sh, from a PC build)" FORCE)
    function(banjo_renut_shader_cache_override TARGET)
        if(NOT EXISTS "${BANJO_RENUT_SHADER_CACHE_CPP}")
            message(FATAL_ERROR "No ${BANJO_RENUT_SHADER_CACHE_CPP}: build the PC tree first, then run "
                                "tools/renut/switch_shaders.sh (Renut's XenosRecomp runs on the host)")
        endif()
        target_sources(${TARGET} PRIVATE "${BANJO_RENUT_SHADER_CACHE_CPP}")
        set_source_files_properties("${BANJO_RENUT_SHADER_CACHE_CPP}" PROPERTIES SKIP_PRECOMPILE_HEADERS ON)
    endfunction()
endif()

# Renut's SDK exports o1heap as rex::o1heap; the sa2-nx SDK fork names it o1heap.
if(TARGET o1heap AND NOT TARGET rex::o1heap)
    add_library(rex::o1heap ALIAS o1heap)
endif()

if(NOT Python3_EXECUTABLE)
    find_package(Python3 COMPONENTS Interpreter REQUIRED)
endif()
if(NOT PYTHON_EXECUTABLE)
    set(PYTHON_EXECUTABLE "${Python3_EXECUTABLE}")
endif()

# shader_common.h is the base's (thirdparty/reblue-XenosRecomp/XenosRecomp): it applies the fetch constant's exponent
# adjust itself (sasrt_renut_texture_exp_adjust), so the translator and the renderer are one generation.

include("${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/gpu.cmake")

add_library(alice_renut_gpu OBJECT
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_select.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_tuning.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/ultimate.cpp"  # renut-ultimate: the ported fixes' switches
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/sasrt_gpu_round.cpp"  # sasrt-nx's GPU rounds
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_checks.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_record.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/display_sync.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/perf/frame_stats.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/sa2_compat/frame_latency.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/sa2_compat/sa2_compat.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/sa2_renut_pacing.cpp"
    # sa2-nx's support code the renderer uses (taken as it is) and this port's stand-ins for the SA2-specific parts.
    "${CMAKE_SOURCE_DIR}/src/cpu/sa2_enhancements.cpp"
    "${CMAKE_SOURCE_DIR}/src/cpu/alice_enhancements_port.cpp"
    "${CMAKE_SOURCE_DIR}/src/cpu/sa2_gpu_boost.cpp"
    "${CMAKE_SOURCE_DIR}/src/cpu/alice_handheld_clocks.cpp"
    "${CMAKE_SOURCE_DIR}/src/me/sa2_render_mode.cpp"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/alice_renut_port.cpp")
target_include_directories(alice_renut_gpu PRIVATE
    "${CMAKE_SOURCE_DIR}"
    "${CMAKE_SOURCE_DIR}/src"
    "${CMAKE_SOURCE_DIR}/src/renut_engine/sa2_compat"
    "${REXGLUE_ENTRYPOINT_INCLUDE_DIR}"
    "${REXSDK_DIR}/src/core")
target_link_libraries(alice_renut_gpu PRIVATE rex::runtime)
if(COMMAND rexglue_apply_target_settings)
    rexglue_apply_target_settings(alice_renut_gpu)
endif()
if(REXGLUE_PLATFORM_SWITCH)
    # The deko3d back end's glue and the game shaders' GLSL package (sa2-nx docs/deko3d-renderer-guide.md).
    target_sources(alice_renut_gpu PRIVATE "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_deko3d.cpp")
    if(EXISTS "${BANJO_DEKO3D_GLSL_CPP}")
        target_sources(alice_renut_gpu PRIVATE "${BANJO_DEKO3D_GLSL_CPP}")
        set_source_files_properties("${BANJO_DEKO3D_GLSL_CPP}" PROPERTIES SKIP_PRECOMPILE_HEADERS ON)
    else()
        message(FATAL_ERROR "No ${BANJO_DEKO3D_GLSL_CPP}: run tools/renut/switch_shaders.sh first")
    endif()
endif()
renut_gpu_setup(alice_renut_gpu)
target_compile_definitions(alice_renut_gpu PRIVATE SA2_RENUT_RENDERER=1)
# The base registers a hook only with KATAMARI_RENUT_HOOKS (banjo_renut_select.h); here the registered ones are Alice's
# (d3d/hooks: device, draw, resource, shader), at Alice's functions.
target_compile_definitions(alice_renut_gpu PRIVATE KATAMARI_RENUT_HOOKS=1)
if(REXGLUE_PLATFORM_SWITCH AND NOT REXGLUE_SWITCH_NVK)
    # No Vulkan driver in this build: Renut on deko3d whatever sa2_renderer / renut_gpu_backend say.
    target_compile_definitions(alice_renut_gpu PRIVATE BANJO_SWITCH_NO_VULKAN=1 SA2_SWITCH_NO_NVK=1)
endif()
# The base's render-thread build option: the draw path's function-local statics without the thread-safe guard (its
# fast path is a load-acquire that holds back every later load on the A57). Sound: these files run on the render thread.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set_property(SOURCE
        "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/render/draw.cpp"
        "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/guest/command_buffers.cpp"
        "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/ultimate.cpp"
        "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/banjo_renut_tuning.cpp"
        "${CMAKE_SOURCE_DIR}/src/renut_engine/gpu/backend/render_thread.cpp"
        TARGET_DIRECTORY alice_renut_gpu APPEND PROPERTY COMPILE_OPTIONS "-fno-threadsafe-statics")
endif()

target_link_libraries(alice PRIVATE alice_renut_gpu)
target_compile_definitions(alice PRIVATE SA2_RENUT_RENDERER=1)
