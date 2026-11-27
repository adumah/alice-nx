#!/usr/bin/env python3
"""Makes the base's shader tools run on Linux. They were written for Windows: they name the tools they run with .exe
(spirv-cross.exe, uam.exe) and the packager points at devkitPro's msys2 zstd.exe. Every edit must match exactly once, so
a change in the base shows up as an error here, not as a build that quietly goes wrong.

    ultimate/patch_base_tools.py <assembled tree>
"""
import pathlib
import sys

EXE = "('.exe' if os.name == 'nt' else '')"

EDITS = {
    # The base reads its hooks from app/src, app/config and a few app/*.toml; Alice's are in app/src and
    # app/overrides.toml (mid-function hooks such as setjmp). Every app/*.toml counts: a name too many is safe.
    'tools/direct_calls.py': [
        ("os.path.join(APP, 'CMakeLists.txt')]",
         "os.path.join(APP, 'CMakeLists.txt'),\n           *__import__('glob').glob(os.path.join(APP, '*.toml'))]"),
    ],
    'tools/deko3d_shaders.py': [
        ("'spirv-cross-build', 'spirv-cross.exe')", f"'spirv-cross-build', 'spirv-cross' + {EXE})"),
        ("'uam-build', 'uam.exe')", f"'uam-build', 'uam' + {EXE})"),
    ],
    'tools/deko3d_glsl_opt.py': [
        ("'uam-build',\n                   'uam.exe')", f"'uam-build',\n                   'uam' + {EXE})"),
    ],
    'tools/deko3d_variant_cache.py': [
        ("'uam-build', 'uam.exe')", f"'uam-build', 'uam' + {EXE})"),
    ],
    'tools/deko3d_shader_package.py': [
        ("ZSTD = r'C:\\devkitPro\\msys2\\usr\\bin\\zstd.exe'",
         "ZSTD = r'C:\\devkitPro\\msys2\\usr\\bin\\zstd.exe' if os.name == 'nt' else 'zstd'"),
    ],
}


def main():
    root = pathlib.Path(sys.argv[1])
    for rel, edits in EDITS.items():
        p = root / rel
        s = p.read_text(encoding='utf-8')
        for old, new in edits:
            if new in s:
                continue  # already patched
            if s.count(old) != 1:
                sys.exit(f'patch_base_tools: {rel}: expected text not found exactly once: {old[:60]!r} '
                         f'(the base changed; update ultimate/patch_base_tools.py)')
            s = s.replace(old, new)
        p.write_text(s, encoding='utf-8')
        print(f'patch_base_tools: {rel}')


main()
