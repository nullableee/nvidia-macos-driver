// Firmware scanout validation shared by the real framebuffer, probe and CPU tests.
// Register definitions: Linux i915 skl_universal_plane_regs.h (MIT).
#pragma once
#include <stdint.h>

struct NMIntelPlane {
    uint32_t conf, ctl, stride, size, surf, offset, position;
};
struct NMIntelLayout {
    uint32_t width, height, pitch, surface;
    uint64_t bytes;
};
enum NMIntelReject {
    kNMIntelOK = 0, kNMIntelDisabled, kNMIntelFormat, kNMIntelTiling,
    kNMIntelTransform, kNMIntelGeometry, kNMIntelRange
};
static inline NMIntelReject nmIntelLayout(const NMIntelPlane &p, uint64_t aperture,
                                         NMIntelLayout &out)
{
    out = {};
    if (!(p.conf & (1u << 31)) || !(p.ctl & (1u << 31))) return kNMIntelDisabled;
    if (((p.ctl >> 23) & 31u) != 8u) return kNMIntelFormat;
    if (p.ctl & (7u << 10)) return kNMIntelTiling;
    // No swizzle/rotation/mirroring/compression or displaced sub-plane.
    // The copied bytes must be the linear BGRA raster the pipe actually reads.
    if ((p.ctl & ((1u << 20) | (1u << 15) | (1u << 8) | (1u << 4) | 3u)) ||
        p.offset || p.position) return kNMIntelTransform;
    NMIntelLayout v = {};
    v.width = (p.size & 0xffffu) + 1;
    v.height = (p.size >> 16) + 1;
    v.pitch = (p.stride & 0xfffu) * 64u;
    v.surface = p.surf & ~0xfffu;
    v.bytes = (uint64_t)v.pitch * v.height;
    if (v.width < 320 || v.height < 200 || v.width > 16384 || v.height > 16384 ||
        v.pitch < (uint64_t)v.width * 4) return kNMIntelGeometry;
    if (!aperture || v.surface >= aperture || v.bytes > aperture - v.surface)
        return kNMIntelRange;
    out = v;
    return kNMIntelOK;
}

static inline NMIntelPlane nmIntelReadPlane(const volatile uint8_t *regs, unsigned pipe)
{
    const unsigned delta = pipe * 0x1000u;
    return {*(const volatile uint32_t *)(regs + 0x70008u + delta),
            *(const volatile uint32_t *)(regs + 0x70180u + delta),
            *(const volatile uint32_t *)(regs + 0x70188u + delta),
            *(const volatile uint32_t *)(regs + 0x70190u + delta),
            *(const volatile uint32_t *)(regs + 0x7019cu + delta),
            *(const volatile uint32_t *)(regs + 0x701a4u + delta),
            *(const volatile uint32_t *)(regs + 0x7018cu + delta)};
}
