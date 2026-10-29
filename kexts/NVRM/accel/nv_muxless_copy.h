// Checked packed-BGRA CPU copy into a different GPU's scanout aperture.
#pragma once
#include <stdint.h>
static inline bool nvMuxlessCopy(volatile uint32_t *dst, uint64_t dstBytes,
                                uint32_t dstPitch, const volatile uint32_t *src,
                                uint64_t srcBytes, uint32_t srcPitch,
                                uint32_t width, uint32_t height)
{
    if (!dst || !src || !width || !height || width > 16384 || height > 16384 ||
        (srcPitch & 3u) || (dstPitch & 3u) ||
        srcPitch < (uint64_t)width * 4 || dstPitch < (uint64_t)width * 4 ||
        srcBytes < (uint64_t)srcPitch * height ||
        dstBytes < (uint64_t)dstPitch * height) return false;
    for (uint32_t y = 0; y < height; ++y)
        for (uint32_t x = 0; x < width; ++x)
            dst[(uint64_t)y * (dstPitch / 4) + x] = src[(uint64_t)y * (srcPitch / 4) + x];
    // Complete write-combined stores before reporting the transaction finished.
#if defined(__x86_64__)
    __asm__ volatile("sfence" ::: "memory");
#endif
    return true;
}
