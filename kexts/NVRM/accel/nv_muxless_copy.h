// Checked packed-BGRA CPU copy into a different GPU's scanout aperture.
#pragma once
#include <stdint.h>
static inline bool nvMuxlessCopy(volatile uint32_t *dst, uint64_t dstBytes,
                                uint32_t dstPitch, const volatile uint32_t *src,
                                uint64_t srcBytes, uint32_t srcPitch,
                                uint32_t width, uint32_t height, bool wide = false)
{
    if (!dst || !src || !width || !height || width > 16384 || height > 16384 ||
        (srcPitch & 3u) || (dstPitch & 3u) ||
        srcPitch < (uint64_t)width * 4 || dstPitch < (uint64_t)width * 4 ||
        srcBytes < (uint64_t)srcPitch * height ||
        dstBytes < (uint64_t)dstPitch * height) return false;
    for (uint32_t y = 0; y < height; ++y) {
        volatile uint32_t *d = dst + (uint64_t)y * (dstPitch / 4);
        const volatile uint32_t *s = src + (uint64_t)y * (srcPitch / 4);
        uint32_t x = 0;
#if defined(__x86_64__)
        // General-purpose registers only: kexts must not borrow SIMD/FPU state.
        // Check each row, since odd pitches can alternate its alignment.
        // may_alias allows the IOSurface's 32-bit pixels to be read in pairs.
        typedef uint64_t NMWord64 __attribute__((__may_alias__));
        if (wide && !(((uintptr_t)d | (uintptr_t)s) & 7u)) {
            volatile NMWord64 *d64 = (volatile NMWord64 *)d;
            const volatile NMWord64 *s64 = (const volatile NMWord64 *)s;
            for (; x + 8 <= width; x += 8) {
                const uint64_t a = s64[x / 2], b = s64[x / 2 + 1];
                const uint64_t c = s64[x / 2 + 2], e = s64[x / 2 + 3];
                d64[x / 2] = a; d64[x / 2 + 1] = b;
                d64[x / 2 + 2] = c; d64[x / 2 + 3] = e;
            }
            for (; x + 2 <= width; x += 2) d64[x / 2] = s64[x / 2];
        }
#else
        (void)wide;
#endif
        // Includes the odd-pixel tail and all rows needing 32-bit accesses.
        for (; x < width; ++x) d[x] = s[x];
    }
    // Complete write-combined stores before reporting the transaction finished.
#if defined(__x86_64__)
    __asm__ volatile("sfence" ::: "memory");
#endif
    return true;
}
