#pragma once
#include <stdint.h>
#include <string.h>
// Only two bounded policies; malformed values retain the established 64 MiB default.
static uint32_t g6mf_cache_parse_mb(const char *s) {
    return s && (!strcmp(s, "128") || !strcmp(s, "128\n")) ? 128u : 64u;
}
static uint32_t g6mf_cache_max_entries(uint32_t mb) { return mb == 128 ? 16u : 8u; }
