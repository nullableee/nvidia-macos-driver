/* CPU-only ownership of the existing Intel scanout. Never NVIDIA VRAM. */
#pragma once
#include "IOAccelMemory.h"
// IOAccelMemory::free is absent from the reconstructed header. Call the actual
// base implementation through its exported Tahoe vtable (slot verified in KC).
extern "C" __attribute__((naked)) void nmIntelMemoryBaseFree(IOAccelMemory *) {
    __asm__("movq __ZTV13IOAccelMemory@GOTPCREL(%rip), %r11\n\tjmpq *160(%r11)");
}
class NMMuxlessScanoutMemory : public IOAccelMemory {
    OSDeclareDefaultStructors(NMMuxlessScanoutMemory)
public:
    IOService *fPanel = nullptr;
    NVRMVramRequest fScanout = {};
    bool initPanel(IOGraphicsAccelerator2 *accel, IOService *panel,
                   const NVRMVramRequest &scanout) {
        if (!panel || !panel->metaCast("NMIntelFB") || !scanout.kva || scanout.phys ||
            !scanout.width || !scanout.height || scanout.pitch < 4ull * scanout.width ||
            scanout.actualSize < (uint64_t)scanout.pitch * scanout.height) return false;
        if (!IOAccelMemory::init(accel)) return false;
        panel->retain(); fPanel = panel; fScanout = scanout;
        // IOAccelMemory's length ivar, checked in the customer's 25G241 KC.
        *(volatile uint64_t *)((unsigned char *)this + 0x40) = scanout.actualSize;
        return true;
    }
    bool ready() const {
        if (!fPanel || fPanel->isInactive()) return false;
        NVRMVramRequest live = {}; live.version = NVRM_VRAM_ABI_VERSION;
        const OSSymbol *fn = OSSymbol::withCStringNoCopy(NVRM_VRAM_FN_SCANOUT);
        if (!fn) return false;
        IOReturn status = fPanel->callPlatformFunction(fn, false, &live, nullptr, nullptr, nullptr);
        fn->release();
        return status == kIOReturnSuccess && !live.phys && live.kva == fScanout.kva &&
            live.actualSize == fScanout.actualSize && live.pitch == fScanout.pitch &&
            live.width == fScanout.width && live.height == fScanout.height;
    }
    uint64_t getLength() const override { return fScanout.actualSize; }
    uint64_t getDirtySize() const override { return 0; }
    uint64_t getResidentSize() const override { return ready() ? fScanout.actualSize : 0; }
    OSObject *createMappingInTask(IOAccelTask *, unsigned int) override { return nullptr; }
    OSObject *createMappingInTaskAtAddressLength(IOAccelTask *, unsigned int,
                                                unsigned long long, unsigned long long) override { return nullptr; }
    bool prepare() override { return ready(); }
    bool complete() override { return true; }
    uint64_t getPhysicalSegment(unsigned long long, unsigned long long *length) override {
        if (length) *length = 0;
        return 0; // No address in the NVIDIA GPU's aperture or page tables.
    }
    void setPurgeable(unsigned int, unsigned int *old) override { if (old) *old = 0; }
    uint64_t setTag(unsigned int) override { return 0; }
    uint64_t getTag() override { return 0; }
    bool matchForReuse(void *, unsigned long long) override { return false; }
    void wire() override {} // NMIntelFB owns and maps the aperture for its lifetime.
    void unwire() override {}
    void increment_wire_count() override {}
    void decrement_wire_count() override {}
    void free() override {
        if (fPanel) { fPanel->release(); fPanel = nullptr; }
        nmIntelMemoryBaseFree(this);
    }
};
OSDefineMetaClassAndStructors(NMMuxlessScanoutMemory, IOAccelMemory)
