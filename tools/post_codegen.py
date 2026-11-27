#!/usr/bin/env python3
"""After every codegen: app/generated/codegen_flavor.txt, the codegen flavour's name in the first "[enh]" log line.

Run by tools/codegen.sh and by the PC build itself (app/CMakeLists.txt appends this script to the generator's command,
which the build re-runs on its own when an input changes).

The flavour is app/codegen_flavor.toml (included by app/alice_manifest.toml): "classic" when it sets no key, otherwise
"optimised: " and its keys. The file is written only when its text changes, so the build does not reconfigure for
nothing.

alice-nx (2026-11-05): the post-codegen rewrites of sa2-nx's optimised flavour (no-volatile pch, loop barriers, direct
calls) and its stage B options (non_volatile_as_local, elide_lr_stores) glitched Alice's textures on the console in
every combination tried (docs/alice-notes.md, 2026-11-03/04); they were removed from this repository. sa2-nx keeps the
tools.

  python3 tools/post_codegen.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, 'app')
GEN = os.path.join(APP, 'generated')
CODEGEN = os.path.join(GEN, 'default')

# ultimate (stage 3): the base's local rewrites, switchable by ALICE_CODEGEN_PASSES: a comma list of groups, or
#   none | all (vector, scalar, memory) | max (every group).
# Groups and their order are the base's (tools/post_codegen.py there). 'barrier' (pch_no_volatile + loop_barriers, required
# together), 'locals' (needs 'barrier'), 'fences', 'calls' (direct_calls) and 'image' are the suspects of the 2026-11-03/04
# texture glitches in docs/alice-notes.md: if textures glitch, drop groups until it stops.
#   calls  direct_calls --redo: calls between unhooked functions become direct (inlinable). It reads the hooks from
#          app/src, the SDK and app/*.toml (ultimate/patch_base_tools.py adds overrides.toml).
#   image  the passes that read the decrypted image (out/default_image.bin, written by codegen.sh): ro_constants,
#          ro_constants_cfg, leaf_dead_stores, dead_ctx_defs, reg_liveness. Skipped when the image is missing.
# Not ported, because they need data only a profiled game has: indirect_calls (indirect_promotions.txt), the localized
# hot copies (localized*.txt) and the r1 / lr passes (their *_choice.json lists). app/src/cpu/hot/hand.txt is empty
# here (Alice has no hand-written natives of that kind), which those tools expect to exist.
# Entry: (group, tool, args): {gen} the generated folder, {pch} the pch, {dir} the folder, {image} the image dump.
STEPS = [
    ('barrier', 'pch_no_volatile', ['{pch}']), ('barrier', 'loop_barriers', ['{dir}']),
    ('memory', 'pch_cold_traps', ['{pch}']), ('calls', 'direct_calls', ['--redo', '--gen', '{gen}']),
    ('memory', 'guest_cas', ['--gen', '{gen}']),
    ('fences', 'guest_fences', ['--gen', '{gen}']),
    ('vector', 'vec_byteswap', ['--gen', '{gen}']), ('vector', 'pch_neon_shuffles', ['{pch}']),
    ('image', 'ro_constants', ['--gen', '{gen}', '--image', '{image}']),
    ('locals', 'loop_locals', ['--gen', '{gen}']), ('locals', 'leaf_locals', ['--gen', '{gen}']),
    ('vector', 'vperm_one_source', ['--gen', '{gen}']), ('scalar', 'fp_sign_ops', ['--gen', '{gen}']),
    ('image', 'leaf_dead_stores', ['--gen', '{gen}', '--image', '{image}']),
    ('scalar', 'single_floats', ['--gen', '{gen}']),
    ('scalar', 'inline_memcalls', ['--gen', '{gen}']), ('vector', 'vec_unaligned_stores', ['--gen', '{gen}']),
    ('vector', 'vec_lane_index', ['--gen', '{gen}']),
    ('vector', 'vec_cvt_fixed', ['--gen', '{gen}']), ('vector', 'vec_prefetch_line', ['--gen', '{gen}']),
    ('vector', 'vec_lvlx_splat', ['--gen', '{gen}']),
    ('vector', 'vec_shift_whole', ['--gen', '{gen}']),
    ('image', 'ro_constants_cfg', ['--gen', '{gen}', '--image', '{image}']),
    ('image', 'dead_ctx_defs', ['--gen', '{gen}', '--image', '{image}', '--abi-indirect']),
    ('memory', 'flush_hoist', ['--gen', '{gen}']), ('vector', 'vupkd3d_neon', ['--gen', '{gen}']),
    ('vector', 'vmx_float_macros', ['--gen', '{gen}']), ('memory', 'stack_forward', ['--gen', '{gen}']),
    ('scalar', 'float_loads', ['--gen', '{gen}']),
    ('image', 'reg_liveness', ['--gen', '{gen}', '--image', '{image}']),
    ('memory', 'vec_dcbz_zva', ['--gen', '{gen}']),
]
GROUPS = ['vector', 'scalar', 'memory', 'barrier', 'locals', 'fences', 'calls', 'image']
DEFAULT_ALL = ['vector', 'scalar', 'memory']
IMAGE = os.path.join(ROOT, 'out', 'default_image.bin')


def passes_wanted():
    raw = os.environ.get('ALICE_CODEGEN_PASSES', 'none').strip().lower()
    names = set()
    for part in re.split(r'[,+ ]+', raw):
        if part == 'max':
            names |= set(GROUPS)
        elif part == 'all':
            names |= set(DEFAULT_ALL)
        elif part in GROUPS:
            names.add(part)
    if 'locals' in names and 'barrier' not in names:
        print('post_codegen: ::warning::locals needs barrier (loop barriers); locals dropped')
        names.discard('locals')
    return names


def pch_path():
    for name in sorted(os.listdir(CODEGEN)):
        m = re.fullmatch(r'(\w+)_recomp\.\d+\.cpp', name)
        if m:
            return os.path.join(CODEGEN, m.group(1) + '_pch.h')
    return os.path.join(CODEGEN, 'alice_pch.h')


def run_passes(groups):
    """Each pass on its own: a failure is a warning (and the pass is not counted), not the end of a two-hour build."""
    done = []
    pch = pch_path()
    for group, name, how in STEPS:
        if group not in groups:
            continue
        tool = os.path.join(ROOT, 'tools', name + '.py')
        if not os.path.isfile(tool):
            print(f'post_codegen: ::warning::{name}.py is missing; skipped')
            continue
        if group == 'image' and not os.path.isfile(IMAGE):
            print(f'post_codegen: ::warning::{IMAGE} is missing; {name} skipped')
            continue
        fill = {'{gen}': CODEGEN, '{pch}': pch, '{dir}': CODEGEN, '{image}': IMAGE}
        args = [fill.get(a, a) for a in how]
        result = subprocess.run([sys.executable, tool, *args], cwd=ROOT)
        if result.returncode != 0:
            print(f'post_codegen: ::warning::{name}.py failed ({result.returncode}); its rewrites may be partial')
        else:
            done.append(name)
    return done


def main():
    flavor_toml = open(os.path.join(APP, 'codegen_flavor.toml'), encoding='utf-8').read()
    keys = re.findall(r'^\s*([a-z_]+)\s*=\s*true', flavor_toml, re.M)
    text = 'optimised: ' + ', '.join(keys) if keys else 'classic'
    groups = passes_wanted()
    if groups and os.path.isdir(CODEGEN):
        done = run_passes(groups)
        text += ' + passes: ' + ', '.join(done) if done else ''
    path = os.path.join(GEN, 'codegen_flavor.txt')
    try:
        old_text = open(path, encoding='utf-8').read()
    except OSError:
        old_text = None
    if old_text != text:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(f'post_codegen: flavour "{text}"')


if __name__ == '__main__':
    main()
