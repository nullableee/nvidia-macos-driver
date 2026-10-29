// G6 MF read-only Intel display snapshot. No IOFramebuffer classes or scanout writes.
#include <IOKit/IOLib.h>
#include <IOKit/pci/IOPCIDevice.h>
#include <pexpert/pexpert.h>
#include <mach/kmod.h>
#include "nmintel_scanout.h"
#define IFBLOG(fmt, ...) IOLog("NMIntelProbe: " fmt "\n", ##__VA_ARGS__)
extern "C" kern_return_t _start(kmod_info_t *, void *);
extern "C" kern_return_t _stop(kmod_info_t *, void *);
extern "C" { KMOD_EXPLICIT_DECL(com.nullmoth.NMIntelProbe, "0.1.2", _start, _stop) }
extern "C" kern_return_t _start(kmod_info_t *, void *) { IFBLOG("0.1.2: module entry"); return KERN_SUCCESS; }
extern "C" kern_return_t _stop(kmod_info_t *, void *) { return KERN_SUCCESS; }


class NMIntelProbe : public IOService {
    OSDeclareDefaultStructors(NMIntelProbe)
public:
    bool start(IOService *provider) override {
        IFBLOG("0.1.2: start on %s", provider ? provider->getName() : "null");
        uint32_t enabled = 0;
        if (!PE_parse_boot_argn("nmintelprobe", &enabled, sizeof enabled) || enabled != 1) {
            IFBLOG("nmintelprobe=1 absent"); return false;
        }
        IOPCIDevice *pci = OSDynamicCast(IOPCIDevice, provider);
        if (!pci) { IFBLOG("provider is not PCI"); return false; }
        const uint16_t vendor = pci->configRead16(kIOPCIConfigVendorID);
        const uint16_t device = pci->configRead16(kIOPCIConfigDeviceID);
        if (vendor != 0x8086 || device != 0xa7a0) {
            IFBLOG("unsupported PCI %04x:%04x", vendor, device); return false;
        }
        pci->setProperty("NMIntelProbeStatus", "reading display registers");
        IOMemoryMap *mmio = pci->mapDeviceMemoryWithRegister(kIOPCIConfigBaseAddress0);
        IODeviceMemory *ap = pci->getDeviceMemoryWithRegister(kIOPCIConfigBaseAddress2);
        if (!mmio || mmio->getLength() < 0x74000 || !ap) {
            IFBLOG("BAR mapping refused: mmio=%p length=%llu aperture=%p", mmio,
                   mmio ? (unsigned long long)mmio->getLength() : 0ull, ap);
            pci->setProperty("NMIntelProbeStatus", "BAR mapping refused");
            OSSafeReleaseNULL(mmio); return false;
        }
        volatile uint8_t *regs = (volatile uint8_t *)mmio->getVirtualAddress();
        setProperty("NMMuxlessPatch", "g6mf-v1.1");
        setProperty("NMIntelProbeVersion", "0.1.2");
        setProperty("NMIntelApertureBase", ap->getPhysicalAddress(), 64);
        setProperty("NMIntelApertureLength", ap->getLength(), 64);
        for (int p = 0; p < 4; ++p) {
            NMIntelPlane raw = nmIntelReadPlane(regs, (unsigned)p);
            char key[48];
            snprintf(key, sizeof key, "NMIntelPipe%cRaw", 'A' + p);
            setProperty(key, &raw, sizeof raw);
            NMIntelLayout layout = {};
            NMIntelReject result = nmIntelLayout(raw, ap->getLength(), layout);
            IFBLOG("pipe %c: conf=%08x ctl=%08x stride=%08x size=%08x surf=%08x offset=%08x pos=%08x reject=%u",
                   'A' + p, raw.conf, raw.ctl, raw.stride, raw.size, raw.surf, raw.offset, raw.position, (unsigned)result);
            snprintf(key, sizeof key, "NMIntelPipe%cReject", 'A' + p);
            setProperty(key, (uint64_t)result, 32);
        }
        mmio->release();
        if (!IOService::start(provider)) {
            pci->setProperty("NMIntelProbeStatus", "IOService start failed");
            IFBLOG("IOService::start failed"); return false;
        }
        pci->setProperty("NMIntelProbeStatus", "snapshot published");
        registerService();
        IFBLOG("NMIntelProbe g6mf-v1.1: register snapshot published; firmware framebuffer untouched");
        return true;
    }
};
OSDefineMetaClassAndStructors(NMIntelProbe, IOService)
