/* G6MF Sequoia: classify descriptor-set misses for optional diagnostics only.
 * No Vulkan objects, addresses or shader state are changed by this header. */
#pragma once

enum g6mf_desc_audit_reason {
    G6MF_DA_REUSE_EXACT,
    G6MF_DA_REUSE_TABLE,
    G6MF_DA_BUILD_NOOPT,
    G6MF_DA_BUILD_NO_LAST,
    G6MF_DA_BUILD_LAYOUT,
    G6MF_DA_BUILD_STALE,
    G6MF_DA_BUILD_STORAGE,
    G6MF_DA_BUILD_MASK,
    G6MF_DA_BUILD_CHANGED,
    G6MF_DA_BUILD_OTHER,
    G6MF_DA_BATCH_HIT,
    G6MF_DA_BATCH_MISS,
    G6MF_DA_N
};

static inline enum g6mf_desc_audit_reason g6mf_desc_audit_miss_reason(
    int have_last, int same_layout, int last_is_live, int storage_grew,
    int mask_grew, int changed_used)
{
    if (!have_last) return G6MF_DA_BUILD_NO_LAST;
    if (!same_layout) return G6MF_DA_BUILD_LAYOUT;
    if (!last_is_live) return G6MF_DA_BUILD_STALE;
    if (storage_grew) return G6MF_DA_BUILD_STORAGE;
    if (mask_grew) return G6MF_DA_BUILD_MASK;
    if (changed_used) return G6MF_DA_BUILD_CHANGED;
    return G6MF_DA_BUILD_OTHER; /* e.g. table page rollover */
}
