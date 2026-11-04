#!/usr/bin/env python3
"""The post-codegen steps of the codegen flavour (alice-nx, after mk9-nx's and sa2-nx's tools/post_codegen.py).

Run after EVERY codegen: by tools/codegen.sh and by the PC build itself (app/CMakeLists.txt appends this script to
the generator's command, which the build re-runs on its own when an input changes; that would otherwise drop the steps).

  - the flavour is read from app/codegen_flavor.toml (tools/codegen.sh --flavor): "optimised" when it sets any key;
  - optimised: tools/pch_no_volatile.py + tools/loop_barriers.py (required together) and tools/direct_calls.py --redo;
  - both: app/generated/codegen_flavor.txt (the build's name in the first "[enh]" log line), written only on change.

  python3 tools/post_codegen.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, 'app')
GEN = os.path.join(APP, 'generated')


def run(*args):
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f'post_codegen: {os.path.basename(args[0])} failed ({result.returncode})')


def main():
    flavor_toml = open(os.path.join(APP, 'codegen_flavor.toml'), encoding='utf-8').read()
    optimised = re.search(r'^\s*[a-z_]+\s*=\s*true', flavor_toml, re.M) is not None
    flavor = 'optimised' if optimised else 'classic'
    tools = os.path.join(ROOT, 'tools')
    gen = os.path.join(GEN, 'default')
    if optimised:
        run(os.path.join(tools, 'pch_no_volatile.py'), os.path.join(gen, 'alice_pch.h'))
        # REQUIRED with the line above: without barriers GCC turns guest polling loops into infinite loops.
        run(os.path.join(tools, 'loop_barriers.py'), gen)
        os.environ.setdefault('REXSDK_DIR', os.path.join(ROOT, '..', 'sa2-nx', 'sdk'))
        run(os.path.join(tools, 'direct_calls.py'), '--redo', '--gen', gen)
    text = f'{flavor} codegen'
    path = os.path.join(GEN, 'codegen_flavor.txt')
    try:
        old_text = open(path, encoding='utf-8').read()
    except OSError:
        old_text = None
    if old_text != text:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(f'post_codegen: {flavor} codegen steps done')


if __name__ == '__main__':
    main()
