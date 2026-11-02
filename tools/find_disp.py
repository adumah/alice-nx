#!/usr/bin/env python3
"""Lists the instructions of the decrypted image (out/default_image.bin) whose 16-bit displacement or immediate is one
of the given values: the loads, stores and addi of a structure field (a device offset), for checking Renut's offsets.

  tools/find_disp.py 12120 0x2F58 [--base-reg N] [--range 0x82B40000-0x82B80000] [--max 40]
"""
import argparse
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# D-form opcodes with a signed 16-bit displacement: addi, lwz, lwzu, lbz, lbzu, stw, stwu, stb, stbu, lhz, lhzu, lha,
# lhau, sth, sthu, lfs, lfsu, lfd, lfdu, stfs, stfsu, stfd, stfdu; DS-form ld/std (58/62, low 2 bits the variant).
NAMES = {14: 'addi', 32: 'lwz', 33: 'lwzu', 34: 'lbz', 35: 'lbzu', 36: 'stw', 37: 'stwu', 38: 'stb', 39: 'stbu',
         40: 'lhz', 41: 'lhzu', 42: 'lha', 43: 'lhau', 44: 'sth', 45: 'sthu', 48: 'lfs', 49: 'lfsu', 50: 'lfd',
         51: 'lfdu', 52: 'stfs', 53: 'stfsu', 54: 'stfd', 55: 'stfdu', 58: 'ld', 62: 'std'}

ap = argparse.ArgumentParser()
ap.add_argument('values', nargs='+', type=lambda s: int(s, 0))
ap.add_argument('--image', default=os.path.join(ROOT, 'out', 'default_image.bin'))
ap.add_argument('--range', default='0x82250000-0x8306CBA8', help='code range (default: the whole .text)')
ap.add_argument('--base-reg', type=int, help='only this base register (rA)')
ap.add_argument('--max', type=int, default=40, help='most hits printed per value')
a = ap.parse_args()

lo, hi = (int(x, 0) for x in a.range.split('-'))
data = open(a.image, 'rb').read()
for value in a.values:
    hits = []
    for va in range(lo, hi, 4):
        off = va - 0x82000000
        if off + 4 > len(data):
            break
        w, = struct.unpack_from('>I', data, off)
        op = w >> 26
        if op not in NAMES:
            continue
        imm = w & 0xFFFF
        if op in (58, 62):
            imm &= ~3
        if imm >= 0x8000:
            imm -= 0x10000
        if imm != value:
            continue
        rt, ra = (w >> 21) & 31, (w >> 16) & 31
        if a.base_reg is not None and ra != a.base_reg:
            continue
        if op == 14 and ra == 0:  # li
            continue
        hits.append(f'  {va:08X}  {NAMES[op]} r{rt},{value}(r{ra})')
    print(f'== {value} ({value:#x}): {len(hits)} hits')
    print('\n'.join(hits[:a.max]))
