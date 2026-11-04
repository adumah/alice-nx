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
// With alice_shadows off, both fields are zeroed after every load (the other alice_* switches below work the same way), so whatever section or file the game loads
// (the split-screen sections too), the renderer sees shadows disabled. The disc files are not touched.
// WHY: the user asked for shadows off (2026-11-03), for frame rate; the shadow depth passes are GPU work in every
// scene with a dynamic light. NOT EXACT: the picture changes (no dynamic shadows), by design.
#include <cstdint>
#include <cstring>

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/ppc.h>
#include <rex/system/kernel_state.h>

REXCVAR_DEFINE_BOOL(alice_shadows, false, "ALICE",
                    "The game's dynamic shadows (UE3 SystemSettings DynamicShadows and LightEnvironmentShadows): "
                    "false = off (default, faster), true = the game's own setting. Read at each settings load");
// alice-nx (2026-11-03, the user: "improve FPS while the camera is looking at water, or turn off reflections"). The
// other switches of the same table, each true = the game's own value (default), false = forced off. Offsets from the
// table sub_8242F4B0 builds (name at sp+N, field r31+offset at sp+N+4), read by tools in docs/alice-notes.md.
REXCVAR_DEFINE_BOOL(alice_distortion, true, "ALICE",
                    "UE3 Distortion, FilteredDistortion, DropParticleDistortion: the refraction / heat-haze pass "
                    "(water surfaces, glass, particles). false = off. Read at each settings load");
REXCVAR_DEFINE_BOOL(alice_depth_of_field, true, "ALICE", "UE3 DepthOfField. false = off. Read at each settings load");
REXCVAR_DEFINE_BOOL(alice_bloom, true, "ALICE",
                    "UE3 UseHighQualityBloom. false = the cheaper bloom (bloom itself stays). Read at each settings "
                    "load");
REXCVAR_DEFINE_BOOL(alice_lens_flares, true, "ALICE", "UE3 LensFlares. false = off. Read at each settings load");
REXCVAR_DEFINE_BOOL(alice_fog_volumes, true, "ALICE", "UE3 FogVolumes. false = off. Read at each settings load");
// alice-nx (2026-11-03): numeric settings of the same table. ScreenPercentage +0x310 (float; the ini's 100.0, with
// UpscaleScreenPercentage = True the game renders the scene at that share of 1280x720 and scales it up: masseffect-nx
// got its GPU-bound scenes from 10-14 to 15-17 fps at 960x544 by a smaller guest video mode). ParticleLODBias +0x68
// (int, the ini's 0: higher picks the particle systems' cheaper LODs, the user's "cascade" lag).
REXCVAR_DEFINE_DOUBLE(alice_screen_percentage, 0.0, "ALICE",
                      "UE3 ScreenPercentage: the scene's render size in % of 1280x720, scaled up by the game "
                      "(75 = 960x540). 0 = the game's own (100). Read at each settings load")
    .range(0.0, 100.0);
REXCVAR_DEFINE_INT32(alice_particle_lod_bias, -1, "ALICE",
                     "UE3 ParticleLODBias: 1, 2, ... = cheaper particle LODs; -1 = the game's own (0). Read at each "
                     "settings load")
    .range(-1, 8);

namespace {

struct Override {
  bool (*keep)();
  const char *name;
  uint32_t offset;  // FSystemSettingsData field, UBOOL
};

const Override kOverrides[] = {
    {[] { return REXCVAR_GET(alice_shadows); }, "DynamicShadows", 0x328},
    {[] { return REXCVAR_GET(alice_shadows); }, "LightEnvironmentShadows", 0x32C},
    {[] { return REXCVAR_GET(alice_distortion); }, "Distortion", 0x48},
    {[] { return REXCVAR_GET(alice_distortion); }, "FilteredDistortion", 0x4C},
    {[] { return REXCVAR_GET(alice_distortion); }, "DropParticleDistortion", 0x50},
    {[] { return REXCVAR_GET(alice_depth_of_field); }, "DepthOfField", 0x38},
    {[] { return REXCVAR_GET(alice_bloom); }, "UseHighQualityBloom", 0x44},
    {[] { return REXCVAR_GET(alice_lens_flares); }, "LensFlares", 0x54},
    {[] { return REXCVAR_GET(alice_fog_volumes); }, "FogVolumes", 0x58},
};

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
  if (!data)
    return;
  static int logged = 0;
  if (const double pct = REXCVAR_GET(alice_screen_percentage); pct > 0.0) {
    const float f = float(pct);
    uint32_t bits;
    std::memcpy(&bits, &f, 4);
    const uint32_t was = LoadBE(data + 0x310);
    StoreBE(data + 0x310, bits);
    if (logged < 64) {
      ++logged;
      float old;
      std::memcpy(&old, &was, 4);
      REXLOG_INFO("[alice] settings {:08X}: ScreenPercentage {} -> {}", data, old, f);
    }
  }
  if (const int32_t bias = REXCVAR_GET(alice_particle_lod_bias); bias >= 0) {
    const uint32_t was = LoadBE(data + 0x68);
    StoreBE(data + 0x68, uint32_t(bias));
    if (logged < 64) {
      ++logged;
      REXLOG_INFO("[alice] settings {:08X}: ParticleLODBias {} -> {}", data, int32_t(was), bias);
    }
  }
  for (const Override &o : kOverrides) {
    if (o.keep())
      continue;
    const uint32_t was = LoadBE(data + o.offset);
    StoreBE(data + o.offset, 0);
    if (logged < 64) {
      ++logged;
      REXLOG_INFO("[alice] settings {:08X}: {} {} -> 0", data, o.name, was);
    }
  }
}
