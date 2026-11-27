#!/usr/bin/env python3
"""Stubs for what the build generates, so clang can syntax-check the engine without a build:
host_shaders/*.{spirv,dxil,deko3d}.h (empty arrays), deko3d.h (opaque types, enumerators, variadic functions) and
generated/<project>_init.h. Usage: make_stubs.py <tree-root> <out-dir> [<base-root>]"""
import glob, os, re, sys

root, out = sys.argv[1], sys.argv[2]
base = sys.argv[3] if len(sys.argv) > 3 else root  # the Renut base (plume lives there)
os.makedirs(out + '/host_shaders', exist_ok=True)
os.makedirs(out + '/generated/default', exist_ok=True)
os.makedirs(out + '/dk', exist_ok=True)
src_all = ''
for p in glob.glob(root + '/app/src/**/*.[ch]*', recursive=True) + glob.glob(base + '/app/thirdparty/plume/*'):
    if os.path.isfile(p):
        try:
            src_all += open(p, errors='ignore').read() + '\n'
        except OSError:
            pass
for m in sorted(set(re.findall(r'host_shaders/([A-Za-z0-9_]+)\.(spirv|dxil|deko3d)\.h', src_all))):
    open(f'{out}/host_shaders/{m[0]}.{m[1]}.h', 'w').write(f'static const unsigned char g_{m[0]}_{m[1]}[] = {{0}};\n')
toks = set(re.findall(r'\b(Dk[A-Za-z0-9]+(?:_[A-Za-z0-9_]+)?|dk[A-Z][A-Za-z0-9]+|DK_[A-Z0-9_]+)\b', src_all))
o = ['#pragma once', '#include <cstdint>', '#include <cstddef>']
for t in sorted(t for t in toks if t.startswith('Dk') and '_' not in t):
    o.append(f'struct {t} {{ alignas(8) unsigned char b_[512]; {t}() = default; template<class T> {t}(T) {{}} '
             f'operator bool() const {{ return false; }} bool operator==(const {t}&) const {{ return true; }} }};')
o += [f'constexpr int {t} = 0;' for t in sorted(t for t in toks if t.startswith('Dk') and '_' in t)]
o += [f'constexpr uint32_t {t} = 0;' for t in sorted(t for t in toks if t.startswith('DK_'))]
o += [f'template<class... A> inline int {t}(A...) {{ return 0; }}' for t in sorted(t for t in toks if t.startswith('dk'))]
open(out + '/dk/deko3d.h', 'w').write('\n'.join(o) + '\n')
subs = sorted(set(re.findall(r'\bsub_[0-9A-F]{8}\b', src_all)))
decl = ''.join(f'extern "C" void __imp__{n}(PPCContext&, uint8_t*); extern "C" void {n}(PPCContext&, uint8_t*);\n' for n in subs)
for h in ('generated/renut_init.h', 'generated/default/alice_init.h'):
    open(f'{out}/{h}', 'w').write('#pragma once\n#include <rex/ppc.h>\n' + decl)
print('stubs written to', out)
