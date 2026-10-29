// IOGraphics controller indices must be dense from zero. Accelerator routing
// is independent: Intel is render head 4 even with no NVIDIA display heads.
#pragma once
#include <stdint.h>
static constexpr uint64_t kNMIntelControllerID = 0x4e4d494e54454c01ull;
static constexpr unsigned kNMIntelControllerIndex = 0;
static constexpr unsigned kNMIntelRenderHead = 4;
static inline unsigned nmMuxlessHead(bool intel, unsigned controllerIndex)
{
    return intel ? kNMIntelRenderHead : controllerIndex;
}
