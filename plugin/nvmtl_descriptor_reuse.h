#pragma once
#include <stdint.h>
// Only sampled/read-only metadata: storage-image ranges need separate tracking.
// All descriptors actually used by the shader, including direct buffers and
// samplers, must be unchanged. Non-descriptor texture handles live in the new
// address-table snapshot and do not require a new descriptor set.
static inline int nvmtl_metadata_descriptors_unchanged(uint32_t storage_hi,
                                                      const uint64_t *changed,
                                                      const uint64_t *used)
{
    if (storage_hi || !changed || !used) return 0;
    for (unsigned k = 0; k < 4; ++k) if (changed[k] & used[k]) return 0;
    return 1;
}
