#!/usr/bin/env python3
"""Retargets Renut's hooks (app/src/renut_engine, Monster High's addresses after tools/renut/retarget.py) to Alice:
Madness Returns' Direct3D functions, constants and device offsets (docs/d3d-census.md).

    tools/renut/retarget_alice.py            report what would change and what is still unknown (changes nothing)
    tools/renut/retarget_alice.py --apply    rewrite the files; refused while any entry is unknown

Every value comes from docs/d3d-census.md, where its evidence is. An entry set to None isn't identified yet: applying
then would leave a Monster High address in a hook, and that hook would replace an unrelated Alice function (each
generated sub_X is a weak symbol). So --apply refuses until there are no None entries left.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGINE = os.path.join(ROOT, 'app', 'src', 'renut_engine')

FUNCTIONS = {  # Monster High -> Alice (None: not identified yet)
    # Direct3D_CreateDevice 8265E2D8: rewritten by hand, as a hook of Alice's hardware path sub_82B66420 (device.cpp)
    '82673110': '82B57E60',  # CDevice::KickOff
    '82672D88': '82B57B80',  # CDevice::KickOffSegment
    '826733B8': '82B56A98',  # CDevice::BeginRingBig
    '82671ED0': '82B57228',  # ring segment allocator
    '826716D8': '82B56E58',  # RingBufferDeviceAllocate
    '82671DE8': '82B57088',  # CDevice::AllocateInlineData
    '82671A68': '82B57F60',  # CDevice::BlockOnFence
    '8265D768': '82B5BE88',  # CBlocker::Check (probable: the 748,000-calls-a-frame poll BlockOnFence calls)
    '826719E8': '82B583C0',  # D3DDevice_IsFencePending
    # D3DDevice_InsertCallback 82673600: not in Alice; its hook is dropped (device.cpp)
    '82663DB8': '82B58B18',  # D3D::SynchronizeToPresentationInterval
    '82664278': '82B59050',  # D3DDevice_Swap
    '826747A0': '82B55D68',  # D3DDevice_DrawVertices
    '82674BB8': '82B56180',  # D3DDevice_DrawIndexedVertices
    # D3DDevice_DrawVerticesUP 82674178: not in Alice; its hook is dropped (draw.cpp)
    '82674178': '82674178',  # (only banjo_shared_hooks.h's declaration, which nothing defines or calls)
    '82673CB8': '82B55368',  # D3DDevice_BeginVertices (device, type, count, stride): returns the vertex pointer,
                             # stores VerticesRingEnd (+13716). The census first took it for DrawVerticesUP.
    '826629E0': '82B5D7E8',  # D3DDevice_ClearF
    # D3DDevice_Resolve 82670E88: no wrapper in Alice; rewritten by hand as a hook of the worker sub_82B5DF10
    '8266AC10': '82B54ED8',  # XGRegisterVertexShader
    '82667AE0': '82B54CE0',  # XGRegisterPixelShader
    # D3DDevice_CreateVertexDeclaration 82668088: rewritten by hand, as a hook of the in-place init sub_82B551A0
    '8265C778': '82B4B730',  # D3DResource_Destroy (what Release 82B4BF38 calls at count 0)
    # InitializePresentationParameters 82683188 / InitializeApiState 826827B8: called by the hand-written device hook
    # at Alice's addresses (82B65F08, 82B65C30)
}
CONSTANTS = {
    'kVdGlobalDeviceImportSlot = 0x82000794': 'kVdGlobalDeviceImportSlot = 0x8200095C',
    'kGlobalQwordVa = 0x82C68C38': 'kGlobalQwordVa = 0x832F75D8',
}
# Device fields: Monster High -> Alice. Up to +11069 unchanged; from about +12100, Monster High's - 128.
OFFSETS = {
    'kDeviceOffsetSwapFenceTag': (11056, 11056),
    'kDeviceOffsetVertexDeclaration': (12240, 12120),  # InitializeApiState's default; not the -128 rule
    'kDeviceOffsetIndexBuffer': (12812, 12684),
    'kDeviceOffsetRenderTargets': (12816, 12688),
    'kDeviceOffsetDepthStencil': (12832, 12704),
    'kDeviceOffsetStreamSources': (12836, 12708),
    'kDeviceOffsetStreamStrides': (12904, 12776),
    'kDeviceOffsetTextures': (12920, 12792),
    'kDeviceOffsetPixelShader': (13068, 12940),
    'kDeviceOffsetVertexShader': (13072, 12944),
    'kDeviceOffsetPredication': (13084, 12956),
    'kDeviceOffsetInKickOff': (13600, 13472),
    'kDeviceOffsetVerticesRingEnd': (13844, 13716),
    'kDeviceOffsetCommandBuffer': (13920, 13792),
    'kDeviceOffsetPresentFenceTag': (15344, 15216),
    'kDeviceOffsetCriticalSection0': (15348, 15220),
    'kDeviceOffsetCriticalSection1': (15376, 15248),
    'kDeviceOffsetSwapCount': (16968, 16840),
    'kDeviceOffsetSideBuffer': (17136, 17008),
    'kDeviceOffsetPerfFrequency': (21996, 21868),
    'kDeviceOffsetTitleMinusOne': (23380, 23664),  # Alice's hardware path; not the -128 rule
    'kDeviceOffsetBehaviorFlags': (24392, 24264),
}
FILES = ['gpu/d3d/hooks/device.cpp', 'gpu/d3d/hooks/draw.cpp', 'gpu/d3d/hooks/shader.cpp', 'gpu/d3d/hooks/resource.cpp',
         'gpu/d3d/hooks/state.cpp', 'gpu/banjo_shared_hooks.h', 'gpu/d3d/d3d.h', 'gpu/sa2_renut_pacing.cpp']


def unknowns():
    out = [f'function {mh}' for mh, al in FUNCTIONS.items() if al is None]
    out += [f'offset {name}' for name, (_, al) in OFFSETS.items() if al is None]
    return out


def retarget(code):
    code = re.sub(r'sub_([0-9A-F]{8})\b', lambda m: 'sub_' + (FUNCTIONS.get(m.group(1)) or m.group(1)), code)
    for a, b in CONSTANTS.items():
        code = code.replace(a, b)
    for name, (mh, al) in OFFSETS.items():
        if al is not None:
            code = re.sub(rf'\b{name} = {mh}\b', f'{name} = {al}', code)
    return code


def main():
    apply = '--apply' in sys.argv
    missing = unknowns()
    if apply and missing:
        print('refused: not identified yet:\n  ' + '\n  '.join(missing), file=sys.stderr)
        return 1
    changed = 0
    for rel in FILES:
        path = os.path.join(ENGINE, rel)
        if not os.path.exists(path):
            continue
        lines = open(path).read().split('\n')
        out = []
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith('//'):
                out.append(line)
                continue
            cut = line.find('//')
            code, comment = (line, '') if cut < 0 else (line[:cut], line[cut:])
            new = retarget(code) + comment
            if new != line:
                print(f'{rel}:{n}: {new.strip()[:150]}')
                changed += 1
            out.append(new)
        if apply:
            open(path, 'w').write('\n'.join(out))
    print(f'{changed} lines {"changed" if apply else "would change"}; {len(missing)} entries not identified yet',
          file=sys.stderr)
    for m in missing:
        print(f'  unknown: {m}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
