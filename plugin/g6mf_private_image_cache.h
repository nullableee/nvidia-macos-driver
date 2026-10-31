// Experimental private render-image reuse. Disabled unless explicitly enabled
// in the process environment; never applies to IOSurface or heap allocations.
#pragma once
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <time.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#define G6MF_PRIVATE_IMAGE_SLOTS 16
#define G6MF_PRIVATE_IMAGE_BYTES (64ull << 20)
#ifndef G6MF_PRIVATE_IMAGE_POLICY
#define G6MF_PRIVATE_IMAGE_POLICY "/Library/NullMoth/g6mf-private-image-cache"
#endif
typedef struct { uint64_t key[12]; nvk_image image; } g6mf_private_image_slot;
static pthread_mutex_t g6mf_private_image_lock = PTHREAD_MUTEX_INITIALIZER;
static g6mf_private_image_slot g6mf_private_images[G6MF_PRIVATE_IMAGE_SLOTS];
static size_t g6mf_private_image_count;
static uint64_t g6mf_private_image_bytes, g6mf_private_image_hits, g6mf_private_image_misses;
static uint64_t g6mf_private_image_puts, g6mf_private_image_evictions;
int g6mf_private_image_enabled(void) {
    const char *e = getenv("NVMTL_PRIVATE_IMAGE_CACHE");
    if (e) return !strcmp(e, "1"); // native probes set this after dlopen
    if (strcmp(getprogname(), "WindowServer")) return 0;
    static _Atomic uint64_t next;
    static _Atomic int enabled;
    uint64_t old = atomic_load(&next), now = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
    if (now >= old && atomic_compare_exchange_strong(&next, &old, now + 1000000000ull)) {
        int on = 0;
        int fd = open(G6MF_PRIVATE_IMAGE_POLICY, O_RDONLY | O_NOFOLLOW | O_NONBLOCK);
        if (fd >= 0) {
            struct stat st; char b[4] = {0};
            if (!fstat(fd, &st) && S_ISREG(st.st_mode) && !st.st_uid && !(st.st_mode & 022)) {
                ssize_t n = read(fd, b, sizeof b);
                on = (n == 1 && b[0] == '1') || (n == 2 && b[0] == '1' && b[1] == '\n');
            }
            close(fd);
        }
        atomic_store(&enabled, on);
    }
    return atomic_load(&enabled);
}
void g6mf_private_image_stats(uint64_t out[6]) {
    pthread_mutex_lock(&g6mf_private_image_lock);
    out[0] = g6mf_private_image_hits; out[1] = g6mf_private_image_misses;
    out[2] = g6mf_private_image_puts; out[3] = g6mf_private_image_evictions;
    out[4] = g6mf_private_image_count; out[5] = g6mf_private_image_bytes;
    pthread_mutex_unlock(&g6mf_private_image_lock);
}
void g6mf_private_image_flush(void) {
    g6mf_private_image_slot dead[G6MF_PRIVATE_IMAGE_SLOTS];
    pthread_mutex_lock(&g6mf_private_image_lock);
    size_t n = g6mf_private_image_count;
    memcpy(dead, g6mf_private_images, n * sizeof *dead);
    memset(g6mf_private_images, 0, sizeof g6mf_private_images);
    g6mf_private_image_count = 0; g6mf_private_image_bytes = 0;
    pthread_mutex_unlock(&g6mf_private_image_lock);
    for (size_t k = 0; k < n; k++) nvmtl_vk_image_destroy(&dead[k].image);
}
int g6mf_private_image_take(const uint64_t key[12], nvk_image *out) {
    if (!g6mf_private_image_enabled()) { g6mf_private_image_flush(); return 0; }
    int hit = 0;
    pthread_mutex_lock(&g6mf_private_image_lock);
    for (size_t k = g6mf_private_image_count; k-- > 0;) {
        if (memcmp(key, g6mf_private_images[k].key, sizeof g6mf_private_images[k].key)) continue;
        *out = g6mf_private_images[k].image;
        g6mf_private_image_bytes -= out->alloc;
        memmove(&g6mf_private_images[k], &g6mf_private_images[k + 1],
            (g6mf_private_image_count - k - 1) * sizeof g6mf_private_images[0]);
        memset(&g6mf_private_images[--g6mf_private_image_count], 0, sizeof g6mf_private_images[0]);
        hit = 1; break;
    }
    if (hit) g6mf_private_image_hits++; else g6mf_private_image_misses++;
    pthread_mutex_unlock(&g6mf_private_image_lock);
    return hit;
}
int g6mf_private_image_put(const uint64_t key[12], nvk_image *image) {
    if (!g6mf_private_image_enabled() || !image->img || !image->view || !image->mem
        || image->placed || image->sysmem || !image->alloc || image->alloc > (32ull << 20)) return 0;
    // Same lifetime boundary as normal texture destruction. Pending uploads
    // must finish before a subsequent texture can overwrite this allocation.
    nvmtl_vk_image_upload_barrier(image);
    nvk_image dead[G6MF_PRIVATE_IMAGE_SLOTS]; size_t n = 0;
    pthread_mutex_lock(&g6mf_private_image_lock);
    while (g6mf_private_image_count && (g6mf_private_image_count == G6MF_PRIVATE_IMAGE_SLOTS
        || g6mf_private_image_bytes + image->alloc > G6MF_PRIVATE_IMAGE_BYTES)) {
        dead[n++] = g6mf_private_images[0].image;
        g6mf_private_image_bytes -= dead[n - 1].alloc;
        memmove(g6mf_private_images, g6mf_private_images + 1,
            (--g6mf_private_image_count) * sizeof g6mf_private_images[0]);
    }
    g6mf_private_image_slot *slot = &g6mf_private_images[g6mf_private_image_count++];
    memcpy(slot->key, key, sizeof slot->key); slot->image = *image;
    g6mf_private_image_bytes += image->alloc; g6mf_private_image_puts++;
    g6mf_private_image_evictions += n;
    memset(image, 0, sizeof *image);
    pthread_mutex_unlock(&g6mf_private_image_lock);
    for (size_t k = 0; k < n; k++) nvmtl_vk_image_destroy(&dead[k]);
    return 1;
}
