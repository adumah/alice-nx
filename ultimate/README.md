# Alice on the Renut base

This repository is Alice's game layer. The ReXGlue SDK, Plume, Renut's XenosRecomp, UAM, FFmpeg and the shader tools
come from [renut_nx_ultimate_base](https://github.com/ChanseyIsTheBest/renut_nx_ultimate_base), at the commit named in
`BASE_REF`. `assemble.sh` combines the two into the tree the workflow builds in (`.github/workflows/ultimate-build.yml`).

## Stages

| Stage | What changes | State |
| --- | --- | --- |
| 1 | The base's **SDK** (Horizon layer, memory governor, pooled thread stacks, event waits, XMA cache), **third-party code** (Plume, Renut's XenosRecomp, UAM) and **shader tools**, under Alice's app and renderer copy as they are. Alice's known-good codegen flavour ("stage A") stays. | this branch; not yet built |
| 2 | The base's renderer fixes and speed-ups, file by file into `app/src/renut_engine`, each tried on its own. | not started |
| 3 | The base's post-codegen passes, one at a time, behind switches (see below). | not started |

## Why the post-codegen passes are not simply switched on

`docs/alice-notes.md` (2026-11-03/04) bisected a glitch in Alice's skin and dress textures on the console. Every build with
the loop barriers, the no-volatile pch, direct calls, `non_volatile_as_local` or `elide_lr_stores` showed it; the stage A
flavour (`skip_msr` and the cr/ctr/xer/reserved locals, no post steps) did not. The suspected cause is the guest's
setjmp/longjmp (`82DBA170` / `82DBA440`): after a longjmp the setjmp caller's r14-r31 locals keep the failing call's values.
The base's `tools/post_codegen.py` runs exactly those passes, so this tree uses Alice's own `tools/post_codegen.py` (it only
records the flavour's name) until stage 3 adds the base's passes back one by one.

## Using it

1. Actions tab: enable workflows for the fork if GitHub asks.
2. Run **Ultimate Build (Alice on the Renut base)**. The Google Drive file ID of your game ZIP is an input.
3. The NRO and shader cache come out as the `alice-nx-switch-ultimate` artifact; logs are in `alice-nx-build-diagnostics`.

Artifacts of a public repository can be downloaded by anyone signed in to GitHub, and these contain code translated from
the game: delete them after downloading, and make the repository private when you can.

## Taking newer base work

Sync your fork of the base, put its commit in `BASE_REF`, and run the workflow.

## Engine layout (from the base-first re-port, 2026-11-27)

`app/src/renut_engine` is now the base's engine (commit in `BASE_REF`), not Alice's older sa2-nx copy, with only the
game layer of Alice on it:

- `gpu/d3d/hooks/{device,draw,resource}.cpp`: Alice's own hooks, at Alice's functions (Direct3D 2.0.20353).
  `gpu/d3d/hooks/shader.cpp` is the base's file with Alice's hook registrations and declaration table.
  `d3d/hooks/state.cpp`, `guest/widescreen.cpp`, `guest/photo_capture.cpp` are not built (gpu.cmake).
- `gpu/d3d/d3d.h`, `d3d_native.h`: the base's, with Alice's offsets by name; `kStateTagChunks` is the conservative
  range (every chunk after the register packets) until Alice's private state is census-checked.
- `backend/queued.cpp`, `guest/command_buffers.{h,cpp}`: the base's, with Alice's delta-chunk bounds (11008-12096) and
  BeginIndexedVertices' index copy.
- `gpu/banjo_renut_select.cpp`: Alice's (`sa2_renderer`), `gpu/sa2_renut_pacing.cpp`, `guest/sa2_screen.cpp`: Alice's.
- Alice's depth bias, fetch-only textures, texture exponent adjust and resolve exponent bias are the base's own
  features now (dynamic depth bias, `sasrt_renut_texture_fetch_only`, `sasrt_renut_texture_exp_adjust`,
  `blur_renut_resolve_exp_bias`): the renderer's and the translator's shader_common.h are one generation again.
- `ultimate/check/`: a local `clang -fsyntax-only` of every source against stubs for what the build generates
  (`make_stubs.py`, `chk.sh`, `chkall.sh`): API drift shows in a minute instead of after a two-hour CI run.

## Codegen groups (`codegen_passes`)
`vector`, `scalar`, `memory` are the safe set (`all`). `max` adds `barrier`, `locals`, `fences`, `calls` (direct_calls) and
`image` (ro_constants, ro_constants_cfg, leaf_dead_stores, dead_ctx_defs, reg_liveness; they read `out/default_image.bin`).
If textures glitch, go `max` -> `all`, then add groups back one at a time (barrier first, locals needs it).
Not ported (they need profiled data): indirect_calls, the localized hot copies, the r1 / lr passes.
