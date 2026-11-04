// alice-nx (2026-11-03): the game's own graphics settings, overridden after UE3 loads them (alice_shadows).
//
// UE3 keeps its graphics switches in [SystemSettings] of Xe-AliceEngine.ini (Coalesced_<lang>.bin on the disc):
// DynamicShadows = True, LightEnvironmentShadows = True, among ~80 others. sub_8242F4B0 loads one section of them
// into an FSystemSettingsData (r3 = the data, r4 = the section name, r5 = the ini file). It builds a table of
// (name, field) pairs on its stack first: 8242F530 stores L"DynamicShadows" (820C5F54) at sp+384, and 8242F55C
// stores r18 = r31+808 at sp+388; L"LightEnvironmentShadows" (820C5F74) at sp+392 goes with r31+812 at sp+396
// (r31 = r3). Its five callers: 82430CBC, 82430E18, 82430ED0, 8243175C (section 820C3C2C, L"SystemSettings") and
// 82432964 (r3 = this+4, L"SystemSettingsEditor" and L"SystemSettings").
//
// With alice_shadows off, both fields are zeroed after every load, so whatever section or file the game loads
// (the split-screen sections too), the renderer sees shadows disabled. The disc files are not touched.
// WHY: the user asked for shadows off (2026-11-03), for frame rate; the shadow depth passes are GPU work in every
// scene with a dynamic light. NOT EXACT: the picture changes (no dynamic shadows), by design.
#include <cstdint>

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/ppc.h>
#include <rex/system/kernel_state.h>

REXCVAR_DEFINE_BOOL(alice_shadows, false, "ALICE",
                    "The game's dynamic shadows (UE3 SystemSettings DynamicShadows and LightEnvironmentShadows): "
                    "false = off (default, faster), true = the game's own setting. Read at each settings load");

namespace {

constexpr uint32_t kDynamicShadows = 808;           // FSystemSettingsData +0x328, UBOOL
constexpr uint32_t kLightEnvironmentShadows = 812;  // +0x32C, UBOOL

uint32_t LoadBE(uint32_t va) {
  const uint8_t *p = REX_KERNEL_MEMORY()->TranslateVirtual<const uint8_t *>(va);
  return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3];
}

void StoreBE(uint32_t va, uint32_t v) {
  uint8_t *p = REX_KERNEL_MEMORY()->TranslateVirtual<uint8_t *>(va);
  p[0] = uint8_t(v >> 24);
  p[1] = uint8_t(v >> 16);
  p[2] = uint8_t(v >> 8);
  p[3] = uint8_t(v);
}

}  // namespace

REX_EXTERN(__imp__sub_8242F4B0);

extern "C" REX_FUNC(sub_8242F4B0) {
  const uint32_t data = ctx.r3.u32;
  __imp__sub_8242F4B0(ctx, base);
  if (!data || REXCVAR_GET(alice_shadows))
    return;
  const uint32_t dyn = LoadBE(data + kDynamicShadows);
  const uint32_t env = LoadBE(data + kLightEnvironmentShadows);
  StoreBE(data + kDynamicShadows, 0);
  StoreBE(data + kLightEnvironmentShadows, 0);
  static int logged = 0;
  if (logged < 8) {
    ++logged;
    REXLOG_INFO("[alice] shadows off: settings {:08X} DynamicShadows {} -> 0, LightEnvironmentShadows {} -> 0", data,
                dyn, env);
  }
}
