#!/usr/bin/env python3
"""Prints a PowerPC listing of the decrypted image (out/default_image.bin) around addresses, with sa2-nx's ppc_mini.

  tools/ppcdis.py 0x82B80788 [more addresses] [--before N] [--after N]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.environ.get('SA2_NX', os.path.join(ROOT, '..', 'sa2-nx')), 'tools'))
from ppc_mini import Image, decode, text  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('addrs', nargs='+')
ap.add_argument('--before', type=int, default=8)
ap.add_argument('--after', type=int, default=16)
ap.add_argument('--image', default=os.path.join(ROOT, 'out', 'default_image.bin'))
a = ap.parse_args()
img = Image(a.image, 0x82000000)
for s in a.addrs:
    t = int(s, 16)
    print(f'== {t:08X}')
    for addr in range(t - 4 * a.before, t + 4 * a.after, 4):
        if not img.contains(addr):
            continue
        w = img.word(addr)
        try:
            d = text(decode(w, addr))
        except Exception:
            d = '?'
        print(f'{"->" if addr == t else "  "} {addr:08X}  {w:08X}  {d}')
