# Direct3D census (for the native renderer)

The Switch build needs a native renderer, so the game's XDK Direct3D functions have to be hooked, and the device's
state read at known offsets. This file records which function is which in Alice: Madness Returns' `Default.xex`, and
why. As sa2-nx's guide asks, it names the source of every one. Monster High's values (mhnwis-nx, XDK 2.0.21256) are
given for comparison.

Tools:
- `tools/d3d/fnindex.py build|show|callers|grep`: listings and the call graph from the generated code.
- `tools/d3d/fingerprint.py`: functions using a set of displacements.
- `tools/d3d/census_build.py` / `census_report.py`: a diagnostic build counting every call in a range.

Static analysis done 2026-11-02. The runtime census is still to come.

## The library

Alice links XDK 2.0.20353 with **D3D9LTCG**. The Direct3D library is link-time optimised together with the game, so
some XDK functions are inlined or take different arguments than in SA2 or Monster High. For example, game code calls
the resolve worker directly. The library's code sits at 0x82B40000-0x82B80000, and the game's own D3D layer (Unreal's
Xenon renderer) sits right below it at 0x82A4xxxx-0x82A5xxxx.

## The device layout differs from Monster High's

The device is 0x5F80 bytes, against Monster High's 0x6080. Fields after about +11100 sit 128 bytes lower; the ring
and fence fields are unchanged.

| What | Monster High | Alice | Evidence |
|---|---|---|---|
| Device allocation, clear | 0x6080 at 0x80 | 24576 allocated, aligned to 128 (`addi 131` / mask), 24448 (0x5F80) cleared | CreateDevice `sub_82B5C288` |
| Global device pointer | | 0x8335016C | CreateDevice: `stw r31,364(r30)` with r30 = 0x83350000 |
| Ring, ring limit, ring guarantee | +48, +52, +56 | same | BeginRingBig compares +48 + 4n with +52; KickOff returns +48; `sub_82B58340` tests +48 against +56 |
| Fence completion pointer, fence tag | +11024, +11036 | same | KickOff, BlockOnFence `tag - fence < tag - *completion` |
| Flag bytes | +11068..+11071 | same (+11068, +11069 read; +11072 in the draws) | KickOff, the segment allocator, the draws |
| In KickOff | +13600 | **+13472** | KickOff, BlockOnFence, KickOffSegment's helper |
| Command buffer being recorded | +13920 | **+13792** | AllocateInlineData, the segment allocator |
| End of inline vertices | +13844 | **+13716** | the two UP draws |
| Swap count | +16968 | **+16840** | Swap: `lwz r11,16840(r31)` / `addi 1` / `stw` |
| Index buffer | +12812 | **+12684** | DrawIndexedVertices (`lwz r24,12684(r31)`), not DrawVertices |
| Render targets [4], depth | +12816, +12832 | **+12688..+12700, +12704** | `sub_82B5D7E8` (22 callers) reads exactly these five |
| Vertex shader: container, physical part | +0x368, +0x20 | same | XGRegisterVertexShader `sub_82B54ED8` |

Assumed, but not yet checked: stream sources, textures, the vertex declaration and the bound VS/PS are Monster High's
offsets − 128 (+12708, +12792, +12112, +12944, +12940). Each one gets confirmed when the renderer reads it.

## Functions identified

| Function | Monster High | Alice | Evidence |
|---|---|---|---|
| Direct3D_CreateDevice | 8265E2D8 | **82B5C288** | Allocates the device (above). E_OUTOFMEMORY (0x8007000E) on failure. Stores 0x0C000001 at +24264. Hardware path `sub_82B66420` (VdInitializeEngines, VdSetGraphicsInterruptCallback). One caller, `sub_82A54980`. |
| CDevice::KickOff | 82673110 | **82B57E60** | 70 callers. Checks +13472 and flag 0x80 of +11068. Waits through BlockOnFence on tag − 2 (+11036). Sets 0x2 of +11069. Returns the ring (+48). |
| CDevice::KickOffSegment | 82672D88 | **82B57B80** | Called by KickOff. Calls the segment allocator and the segment packet writer `sub_82B57D08` (+13472, +13632). |
| CDevice::BeginRingBig | 826733B8 | **82B56A98** | (device, count): ring + 4·count > limit (+52) → KickOff, then the segment allocator. Returns the ring. |
| Ring segment allocator | 82671ED0 | **82B57228** | (device, dwords). Its callers are exactly BeginRingBig, KickOffSegment and Swap, as in Monster High. Uses +13792. |
| RingBufferDeviceAllocate | 826716D8 | **82B56E58** | AllocateInlineData calls it as (device, 1, &size, alignment). |
| CDevice::AllocateInlineData | 82671DE8 | **82B57088** | (device, dwords, alignment): bytes = 4·dwords, from the command buffer (+13792) or RingBufferDeviceAllocate. |
| CDevice::BlockOnFence | 82671A68 | **82B57F60** | (device, fence, type, no_kick): the pending test on +11024/+11036, then KickOff when the fence is the current one and +13472 is clear. |
| D3D::SynchronizeToPresentationInterval | 82663DB8 | **82B58B18** | The only small function setting the swap-pending flag (0x10 of +11069). Called by Swap. |
| D3DDevice_Swap | 82664278 | **82B59050** | The only caller of VdSwap. Increments +16840. Copies 24 bytes of scaler parameters from arg 2 + 28. |
| D3DDevice_DrawVertices | 826747A0 | **82B55D68** | Exactly 0x418 before DrawIndexedVertices, as in SA2 and Monster High. Same state flush (`sub_82B5A258`, `82B5B2A8`, `82B59B28` …) without the index buffer. Called by Unreal's `sub_82A52870`. |
| D3DDevice_DrawIndexedVertices | 82674BB8 | **82B56180** | Reads the index buffer (+12684), then the draw packets. Called by Unreal's `sub_82A52908`. |
| DrawVerticesUP / DrawIndexedVerticesUP | 82674178 | **82B55368 / 82B55828** (to be confirmed by the census) | The only two functions setting the ring to +13716 after a copy. 82B55368 has 8+ game callers, 82B55828 has 2. |
| Resolve (copy worker) | 8266FD30 | **82B5DF10** | The only function programming RB_COPY_CONTROL (0x2318). Under LTCG it's called straight from game code (`sub_82A53D20`, `82A54E80`, `82A55EC0`), with no 19-instruction wrapper. |
| D3DResource_IsSet | 8265BD98 | **82B4C048** | Switch on the resource type: index buffer +12684, render targets +12688..+12700 and depth +12704, 16 stream sources from +12708, 26 textures from +12792, vertex shader +12944, pixel shader +12940. Callers `829A4488`, `82A57380`. |
| XGRegisterVertexShader | 8266AC10 | **82B54ED8** | Clears 872 bytes, type 6, reference 1, physical part at +0x20, container at +0x368. Called by Unreal's `sub_82A57888`. |

Still open, for the runtime census: ClearF (candidates `82B51E88`, `82B521D8`), XGRegisterPixelShader, the
CreateVertexShader/CreatePixelShader path, IsFencePending, InsertCallback, CBlocker::Check, BeginVertices. Also how
many shaders the game registers through XG versus loading them straight from its packages (gears2-nx saw only 7
shader objects created in Gears of War 2).

## Runtime census (2026-11-02, census build over 0x82A40000-0x82B80000, 7-minute run into the first gameplay area)

Measured in the 350-410 s window of gameplay: 1800 Swaps in 60 s, a steady **30 fps** (the game's own cap).

| Function | Calls | Notes |
|---|---|---|
| Swap `82B59050`, SynchronizeToPresentationInterval `82B58B18` | 1 / frame | Confirms both |
| CreateDevice `82B5C288` | 1 in the run | |
| DrawIndexedVertices `82B56180` | 444 / frame | |
| DrawVertices `82B55D68` | 12 / frame | |
| `82B55828` / `82B55368` (the UP draws) | 34 / frame, 1 / frame | `82B55828` is the main inline draw (probably DrawIndexedVerticesUP or the UP path Unreal uses for its UI and lines) |
| Resolve worker `82B5DF10` | 21 / frame | |
| `82B5BE88` | 748,000 / frame | A GPU-wait poll: CBlocker::Check (BlockOnFence calls it). A spin-wait that costs CPU on the Switch. |
| `82B4D048` | 79,000 / frame | Another polling loop. To identify. |
| XGRegisterVertexShader `82B54ED8` | **270 in the whole run** | Through Unreal's `82A57888` |

**Shaders.** The emulated GPU built pipelines with **84 distinct vertex shaders** and 174 distinct pixel shaders in the
same run, while 270 vertex shaders were registered through XGRegisterVertexShader. So, unlike Gears of War 2, Alice
appears to create its vertex shaders through XG. Capturing them at registration (Monster High's Renut method) should
work for vertex shaders. Not proven yet: the next check is to compare the registered microcode's hashes with the drawn
ones. The pixel shader registration isn't found yet. Under LTCG it may be inlined into Unreal's shader cache code
(`82A57CD0`, 64 calls a frame, which calls `82A57888` on a miss).

## More identified (static, 2026-11-02)

| What | Monster High | Alice | Evidence |
|---|---|---|---|
| D3DDevice_IsFencePending | 826719E8 | **82B583C0** | One argument. The device comes from an import slot chosen by KeGetCurrentProcessType == 2. Reads +11036 and +11024. |
| VdGlobalDevice import slot | 0x82000794 | **0x8200095C** | IsFencePending: the title process (type 2) reads `lwz 2396(0x82000000)`; the system one reads 0x82000958 (VdGlobalXamDevice) |
| Global qword copied into every device | 0x82C68C38 | **0x832F75D8** | CreateDevice: `lis r11,-31953` / `ld r11,30168(r11)` / `std r11,11008(r31)` |
| CBlocker::Check | 8265D768 | **82B5BE88** (probable) | BlockOnFence's callees are KickOff, `82B5BDC0` and `82B5BE88`. 82B5BE88 is the one polled 748,000 times a frame. |

## Renut's device offsets for Alice

Renut (app/src/renut_engine, `kDeviceOffset*`) reads 36 device fields. The rule found so far: the fields up to +11069
are Monster High's, and the fields from +12100 up are Monster High's − 128. Confirmed fields below. The rest follow
the rule until checked.

| Field | Monster High | Alice | Status |
|---|---|---|---|
| GlobalQword, CreationThreadId, IsTitleProcess | 11008, 11016, 11020 | same | confirmed (CreateDevice) |
| FenceCompletion, FenceTag, Flags, SwapFlags | 11024, 11036, 11068, 11069 | same | confirmed |
| SwapFenceTag | 11056 | 11056? | not checked |
| VertexDeclaration, StreamStrides | 12240, 12904 | 12112, 12776 | inferred (−128) |
| StreamSources [16], Textures [26] | 12836, 12920 | 12708, 12792 | confirmed (D3DResource_IsSet `82B4C048` loops 16 / 26 slots from these) |
| IndexBuffer, RenderTargets, DepthStencil | 12812, 12816, 12832 | 12684, 12688, 12704 | confirmed |
| PixelShader, VertexShader | 13068, 13072 | 12940, 12944 | confirmed (D3DResource_IsSet) |
| Predication | 13084 | 12956 | inferred |
| InKickOff, VerticesRingEnd, CommandBuffer | 13600, 13844, 13920 | 13472, 13716, 13792 | confirmed |
| PresentFenceTag, CriticalSection0/1 | 15344, 15348, 15376 | 15216, 15220, 15248 | inferred |
| SwapCount, SideBuffer | 16968, 17136 | 16840, 17008 | confirmed (Swap; CreateDevice's 4800-byte alloc) |
| PerfFrequency, TitleMinusOne, BehaviorFlags | 21996, 23380, 24392 | 21868, 23252, 24264 | BehaviorFlags confirmed (CreateDevice stores the constant 0x0C000001: LTCG folded the argument); the others inferred |

Renut functions not found yet for Alice: ClearF (the `82B51E88`/`82B521D8` candidates run 60-70 times a frame, too
often for a clear), BeginVertices, CreateVertexDeclaration, D3DResource_Destroy, InitializePresentationParameters,
InitializeApiState, XGRegisterPixelShader, InsertCallback. Under LTCG, some may be inlined into their callers, which
would need a different hook point.
