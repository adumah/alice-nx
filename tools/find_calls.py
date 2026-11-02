#!/usr/bin/env python3
"""Lists the direct calls and branches (bl / b) to the given addresses in the decrypted image (out/default_image.bin).

  tools/find_calls.py 0x82B5DF10 [more addresses] [--range 0x82250000-0x8306CBA8]
"""
import argparse
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('targets', nargs='+', type=lambda s: int(s, 0))
ap.add_argument('--image', default=os.path.join(ROOT, 'out', 'default_image.bin'))
ap.add_argument('--range', default='0x82250000-0x8306CBA8', help='code range (default: the whole .text)')
a = ap.parse_args()

lo, hi = (int(x, 0) for x in a.range.split('-'))
data = open(a.image, 'rb').read()
targets = set(a.targets)
found = {t: [] for t in targets}
for va in range(lo, hi, 4):
    off = va - 0x82000000
    if off + 4 > len(data):
        break
    w, = struct.unpack_from('>I', data, off)
    if w >> 26 != 18 or w & 2:  # I-form branch, relative only
        continue
    disp = w & 0x03FFFFFC
    if disp & 0x02000000:
        disp -= 0x04000000
    dest = (va + disp) & 0xFFFFFFFF
    if dest in targets:
        found[dest].append(f'  {va:08X}  {"bl" if w & 1 else "b"}')
for t in a.targets:
    print(f'== {t:08X}: {len(found[t])} calls')
    print('\n'.join(found[t]))
