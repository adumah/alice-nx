# alice-nx

An unofficial, fan-made port of the Xbox 360 game **Alice: Madness Returns** to the **Nintendo Switch** and
**Linux**, made by static recompilation (ReXGlue), following [mhnwis-nx](https://github.com/adumah/mhnwis-nx) and
[sa2-nx](https://github.com/ChanseyIsTheBest/sa2-nx).

> **This repository contains no game.** No game files, no game code (translated or not), no shaders, no assets and no
> ready-made NRO. **You must bring your own disc.** See [Disclaimer](#disclaimer).

## Status (work in progress)

| | |
|---|---|
| Linux (x86-64), emulated GPU | **Boots and plays the opening**: logos, title, menus, a new game, the opening cinematic, then walking around the first area. Tested up to 8 minutes per run with no crash. Not played further yet. |
| Native renderer | Not started. The Direct3D census is under way ([docs/d3d-census.md](docs/d3d-census.md)). |
| Nintendo Switch | Not built yet. It needs the native renderer (there's no emulated GPU on the console). |

Analysis notes, with the evidence for every correction: [docs/alice-notes.md](docs/alice-notes.md).
Code-generator corrections: [app/overrides.toml](app/overrides.toml).

## What you need

- **Your own copy of the game**: the Xbox 360 disc, dumped by you, as an extracted folder holding `Default.xex`.
  `Default.xex` must be title ID `45410916`, media ID `31C4B45C`, version 2 (the code generator prints these).
- Linux on x86-64 with: clang, CMake 3.25 or newer, Ninja, Python 3, Git, a Vulkan driver, and the X11/XCB and
  Wayland development files.
- About 10 GB of free memory to compile (the translated game is ~247 MB of C++; `-j 4`), and about 15 GB of disk.
- [sa2-nx](https://github.com/ChanseyIsTheBest/sa2-nx) next to this repository, at commit
  `adf3a4eee524dcca5cd7c1b42454ddb8a09124a1`: its SDK fork and tools are used to build.

## Building the Linux version

```sh
# 1. This repository and sa2-nx, side by side
git clone https://github.com/ChanseyIsTheBest/sa2-nx.git
git -C sa2-nx checkout adf3a4eee524dcca5cd7c1b42454ddb8a09124a1

# 2. The code generator (once)
alice-nx/tools/build_sdk.sh

# 3. Your game: link your extracted disc folder (the one holding Default.xex)
mkdir -p alice-nx/assets
ln -s /path/to/your/extracted/disc alice-nx/assets/game_root

# 4. Translate the game's code (about 5 minutes; written to app/generated/, never committed)
alice-nx/tools/codegen.sh

# 5. Build the PC version and play it
alice-nx/tools/build_pc.sh -j 4
alice-nx/tools/run.sh
```

`tools/boot_test.sh [seconds] [options]` makes a muted, minimized test run, and takes scripted input
(`--input_script=60:START,75:A,345:LY+:4`) and screenshots (`--alice_screenshots=120,135`, written to
`out/pc/shots/`).

## Disclaimer

This is an unofficial, non-commercial fan project for preservation and personal use. It is not affiliated with,
endorsed by, sponsored by or connected to Electronic Arts, Spicy Horse, American McGee, Microsoft or Nintendo.

*Alice: Madness Returns* and all related titles, characters, names, logos and marks belong to their respective owners.
Xbox 360 is a trademark of Microsoft; Nintendo Switch is a trademark of Nintendo. The fallback homebrew menu icon
(`app/switch/icon.jpg`, `tools/make_icon.py`) is original artwork drawn from plain shapes, with no art from the game.

This repository contains **no part of the game**: no disc files, no assets, no executable, no shaders, and none of the
C++ the code generator produces from the game (`app/generated/` is never committed). It holds only this project's own
code, build scripts and analysis notes (addresses and descriptions of the game's code, needed to translate it
correctly). **Bring your own disc.** Builds made from it contain the game's translated code: they are for your own
use only. **Do not share them, and do not ask for or share game files, NROs or download links.**

## Credits

- **The game**: *Alice: Madness Returns*, developed by **Spicy Horse** and published by **Electronic Arts**. All
  credit for the game itself goes to them.
- **[ReXGlue SDK](https://github.com/rexglue/rexglue-sdk)**, which turns Xbox 360 code into C++ and provides the
  runtime it runs on. ReXGlue builds on the [Xenia](https://github.com/xenia-project) emulator.
- **[sa2-nx](https://github.com/ChanseyIsTheBest/sa2-nx)** by ChanseyIsTheBest: the porting prompt and guide, the SDK
  fork, tools and Switch platform layer.
- **[mhnwis-nx](https://github.com/adumah/mhnwis-nx)**: the project this one started from.
- The UE3 ports whose notes guide the renderer work: [masseffect-nx](https://github.com/nebadasSwifty/masseffect-nx),
  [gears2-nx](https://github.com/VasilkovND/gears2-nx), [mk9-nx](https://github.com/Thorhax/mk9-nx).

Full notices and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

GPL-3.0 (see [LICENSE](LICENSE)), because this project includes code adapted from sa2-nx and mhnwis-nx. The game
itself is not covered: it is not here, and it belongs to its owners.
