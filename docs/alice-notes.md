# Alice: Madness Returns (Xbox 360): analysis notes

Facts about the game's code and data that the port depends on, each with where it came from. Addresses are guest
addresses in `Default.xex` (image base 0x82000000).

## Stage 1: the disc (2026-11-02)

| What | Value | Evidence |
|---|---|---|
| Title ID | 45410916 | `rexglue codegen` header (out/codegen.log) |
| Media ID | 31C4B45C | same |
| XEX version | 0.0.0.2 | same |
| Build time | 2011-04-27 02:56:13 UTC | same |
| Original name | `AliceGame-XeReleaseLTCG.pe` | XEX optional header 0x000183FF |
| Image | 0x82000000 + 0x1460000 | codegen (`out/default_image.bin`) |
| Entry point | 0x82DCFAC0 | XEX optional header 0x00010100 |
| Imports | xboxkrnl.exe, xam.xex only | XEX import libraries (0x000103FF) |
| XDK | 2.0.20353 (D3D9LTCG 2.0.20353.16385, XAUDIO2, XONLINE, XHV2, XMP, D3DX9) | XEX static libraries (0x000200FF) |
| Compiler | MSVC 16.0.11886 / 16.0.10224, LINK 10.0.11886 | same |
| Engine | Unreal Engine 3 (cooked for Xenon: `CookedXenon`, package tag 0x9E2A83C1) | the data |

**No guest DLLs.** The executable imports only xboxkrnl and xam, and no other file on the disc starts with `XEX2`
(scan of every file over 4 KB). There's no XEX2 header in the image either.

**Data** (4.5 GB, 1952 files):
- `AliceGame/CookedXenon`: 1654 `.xxx` packages, four texture file caches (`Textures.tfc`, `CharTextures.tfc`,
  `WorldTextures.tfc`, `Lighting.tfc`), `GlobalShaderCache-Xbox360.bin` (tag `GSMB`, uncompressed), `Coalesced_*.bin`
  (ini files, six languages) and `GlobalPersistentCookerData.upk`.
- The packages are compressed as whole files: each starts with the UE3 chunk header (0x9E2A83C1, block size 0x20000,
  then compressed/uncompressed sizes and a size pair per block). A `.uncompressed_size` file sits beside 13 of them.
  The blocks don't start like zlib (0x78) or LZO, so they're most likely LZX (XMemCompress). That isn't confirmed yet,
  and it only matters for offline shader extraction (masseffect-nx's `ue3_shader_scan` handles LZO only). At run time,
  the game's own translated code decompresses them.
- `AliceGame/Movies`: Bink movies (`.bik`) with subtitle `.txt` files. Bink is linked into the executable, so it's
  translated with the rest of the code.

## Stage 2: code generation

- Codegen: ~310 s single-threaded, 479 files, 247 MB of C++ (Monster High: 144 MB).
- First validation: 3 "target not in any function", fixed in `app/overrides.toml` (evidence there).
- `setjmp` 0x82DBA170 / `longjmp` 0x82DBA440: found by shape (the only `stfd f14,0(r3)` and the only
  `lfd f14,0(rX)` in the image), the same CRT pair and jmp_buf layout as Monster High's. setjmp: hook check (lis r4
  / lwz r0,3404(r4) / mtctr / bnectr), mflr r0, mfcr r4, stfd f14-f31 at 0-136(r3), std r13-r31 from 152(r3).
  longjmp: mflr r0, stwu r1,-80(r1), mr r7,r3, val==0 check, then the mirror loads lfd f14.. from 0(r7).

## Renderer route: what the UE3 ports teach (read 2026-11-02, not yet checked on Alice)

- gears2-nx `gow2/PORTING.md`: "Unreal does not create shaders through Direct3D: only 7 shader objects are ever
  created; the rest are loaded straight from the packages." Its draws are matched to a shader library by their
  microcode, and the library is extracted offline from the cooked packages, which are LZX on that disc.
- This is why Monster High's Renut route (shaders captured at CreateVertexShader/CreatePixelShader) probably fits
  Alice badly. Mass Effect, also UE3, used the PM4-ring renderer (sa2-nx `app/src/me`) with offline package scanning
  (`ue3_shader_scan`, LZO only). For Alice that scanner needs an LZX decoder (libmspack is in the SDK's thirdparty).
  To confirm on Alice: count the CreateVertexShader/CreatePixelShader calls in a boot.
- Other UE3 lessons from Gears 2 to expect here:
  - UnrealScript and the game thread dominate the CPU, so a CPU overclock is likely needed on Switch.
  - Occlusion queries are polled by the render thread.
  - The depth prepass vs the base pass need bit-identical depth.
  - 7e3 render targets with an exponent bias.
- `tools/pointer_fixpoint.py` (2026-11-02): pass 1 found 27,848 gaps and 176 candidates. 160 were accepted, and 16
  were rejected (13 no code, 2 tail branches into a function body, 1 with no terminator). Pass 2 found nothing new.
- `switch_check.py` (code 0x82250000-0x8306CBA8): 0 truncated, 0 wrong, 0 missed. 17 "odd shapes" are UnrealScript's
  bytecode dispatch, not switches. At 0x822E50A8 and the run of 16 stubs at 0x822F3438-0x822F3728 (one every 0x30
  bytes), each does `lwz r11,24(r4)` (the script stack's Code pointer), `lbz` the opcode, stores Code+1, then
  `lwzx`s a 256-entry function table in data (0x833370F0, then 0x833374F0 onward, 0x400 apart) and tail-calls it
  with `bctr`. They're generated as indirect calls, which is right. The tables are filled at run time, so a native
  whose address only appears there would surface at boot as "unregistered function".

## Stage 3: first boots on PC, emulated GPU (2026-11-02)

The first build (`tools/build_pc.sh -j 4`, Renut off) booted on its first run, with no fatal error, no unregistered
call and no access violation in any test so far (up to 8 minutes).
- Boot to the Spicy Horse logo, the "Press START" title, the main menu, difficulty select, the gamma and invert-look
  screens of a new game, and the opening cinematic with subtitles. Audio (XMA) decodes in real time, and the
  presenter acquires 99.9 % of frames without waiting.
- `tools/boot_test.sh` runs with `--alice_screenshots` and `--input_script`. The menus' timing changes between runs,
  so a fixed script can land in a different menu. One run reached the "Memories" screen (Bumby, 0/16 memories) after
  START during or after the cinematic.
- Every warning in the log is a normal existence probe: optional subtitle `.txt` and `.xxx` files beside the movies,
  `*TextureS.xxx` beside the `.tfc` caches, localized TOCs (POL/RUS/SLO), `Binaries\EpicInternal.txt`, and the
  `UPDATE:` device (no title update installed).
- 20-minute run (2026-11-02, census build, scripted input): no fatal error, no unregistered call, no access violation.
  The first ~8 minutes were movement, jumps and attacks in the orphanage (hallway and dormitory). After that, an A
  press examined a drawing on the wall, which opens a text popup that only B closes, and the input loop sends no B. So
  the rest of the run sat on that popup with the game running. Wider coverage (Wonderland, combat, saving and loading)
  needs a person playing, or a smarter script.

## Switch build without a renderer (2026-11-02)

- `ALICE_RENUT=OFF tools/build_switch.sh -j 4`: the whole game compiles and links for the console (out/nx/alice.nro,
  76 MB; 46 minutes on 8 cores at -j 4). It has no renderer, so on a console it can't show anything yet. It only
  proves the translated code builds for aarch64 with devkitA64.
- In stock Ryujinx (Ryubing 1.3.3, flatpak), the NRO starts: it reaches the SDK's Switch layer (docked mode, 1920x1080)
  and maps the guest memory arena. Then committing guest memory fails (`AllocFixed: could not commit ... Failure
  0x0000E401`), and the first guest access is an invalid memory access. sa2-nx's deko3d guide tested in **banjo-nx's
  Ryujinx build**, with its three no-loader SDK changes, so stock Ryujinx doesn't seem to support the SDK's memory
  commit. Not a sign of a bug in the port. A real console, or that Ryujinx build, is needed.
- The test copy is in Ryujinx's own SD folder, `~/.var/app/io.github.ryubing.Ryujinx/config/Ryujinx/sdcard/switch/alice-nx`
  (alice.nro, alice.toml without the asset pack, and game_root as a link to disc/). It's local only and holds the
  game's translated code, so don't share it.

### On a real Switch (2026-11-02, renderer off)

Sent with `tools/send_switch.sh` to `sdmc:/switch/alice-nx/alice.nro`, game files in `sdmc:/switch/alice-nx/game_root/`.
From its log (`sdmc:/switch/alice-nx/logs/alice_001.log`):
- The guest memory arena maps (`Guest memory arena mapped: virtual base 0x...576754C000`): the 0xE401 commit failure
  seen in stock Ryujinx doesn't happen on hardware.
- No asset pack: "the game data is 4535 MB, over FAT32's 4 GB file limit". It falls back to the game folder: 1960
  entries mounted in 5978 ms (the VFS index written to `cache/` speeds up later starts).
- The game's code starts: function table initialised, audio up (48000 Hz, 2 channels).
- Then `VdInitializeRingBuffer: no GPU emulation loaded; call ignored`, and nothing more logged: with Renut off there
  is no GPU, so the first wait on a GPU fence never ends. A black screen, by design for this build. Next: Renut.
- To do: the pack's 4 GB limit (FAT32). Split the pack, or leave the movies out of it.
