#pragma once
// Present-only readback. 0 = original path, 1 = copied, -1 = keep previous frame.
// Never mark IOSurface RAM current: it was deliberately not written here.
static int nvAccelMuxlessDirect(NVAccel *a, IOService *fb, IOSurface *s, unsigned head)
{
    if (!a || !fb || !s || head != 4 || !fb->metaCast("NMIntelFB")) return 0;
    const uint64_t w = s->getWidth(), height = s->getHeight(), pitch = s->getBytesPerRow();
    if (s->getPixelFormat() != 0x42475241u || !w || !height || w > 16384 || height > 16384 ||
        pitch < w * 4 || pitch > 16384ull * 8 || (pitch & 3)) return 0;
    OSAddAtomic64(1, &gDirectAttempts);
    if (!nvFamLock(a, true)) { OSAddAtomic64(1, &gDirectFallback); return 0; }
    NMPerfScope directTime(&gPerfDirectTotal);
    void *cache = nullptr;
    IOLock *stageLock = nullptr;
    unsigned long long *pages = nullptr;
    uint64_t pageCount = 0;
    int result = 0;
    do {
        cache = _ZN22IOGraphicsAccelerator223deviceCacheForIOSurfaceEP9IOSurfacej((void *)a, (void *)s, 0);
        OSObject *ctx = cache ? *(OSObject *volatile *)((unsigned char *)cache + 0x20) : nullptr;
        NVResource *res = OSDynamicCast(NVResource, ctx);
        NVVidMemory *vm = res ? nvres_vidmem(res) : nullptr;
        volatile unsigned short *valid = res ? *(unsigned short *volatile *)((unsigned char *)res + 0x30) : nullptr;
        const unsigned id = s->getSurfaceID();
        if (!valid || (valid[0] & 1) || !(valid[6] & 1) || !nvAccelResPluginWrote(res) ||
            !nvSVPend(id, 2) || !vm || !vm->fRmHandle || vm->fScanout) break;
        IOMemoryDescriptor *md = s->getMemoryDescriptor();
        uint64_t length = md ? md->getLength() : 0;
        if (length > vm->fBytes) length = vm->fBytes;
        if (length < pitch * height || length > (64ull << 20)) break;
        struct NVRMRmHandles handles; nvSVZero(&handles, sizeof handles);
        IOService *nvrm = nvAccelNVRM();
        if (!nvrm || !nvAccelRmHandles(&handles)) break;
        // Recheck while holding the family lock; do not read a newly pending GPU writer.
        if (!nvSurfWaitReady(id)) { result = -1; break; }
        stageLock = nvSVStageLock();
        if (!stageLock) break;
        IOLockLock(stageLock);
        IOBufferMemoryDescriptor *stage = nvSVStage(length);
        IOByteCount segmentLength = 0;
        addr64_t physical = stage ? stage->getPhysicalSegment(0, &segmentLength, kIOMemoryMapperNone) : 0;
        if (!physical || segmentLength < length) break;
        pageCount = (length + 4095) >> 12;
        pages = (unsigned long long *)IOMalloc(pageCount * sizeof *pages);
        if (!pages) break;
        for (uint64_t k = 0; k < pageCount; k++) pages[k] = physical + k * 4096;
        struct NVRMSurfPageoff q; nvSVZero(&q, sizeof q);
        q.version = NVRM_SS_RM_VERSION; q.status = NVRM_SS_OFF;
        q.kapiDevice = handles.kapiDevice; q.kapiMemory = vm->fRmHandle;
        q.pages = pages; q.pageCount = pageCount; q.length = length;
        const OSSymbol *symbol = OSSymbol::withCStringNoCopy(NVRM_SS_FN_PAGEOFF);
        if (!symbol) break;
        IOReturn callResult;
        { NMPerfScope timing(&gPerfDirectCE);
          callResult = nvrm->callPlatformFunction(symbol, false, &q, nullptr, nullptr, nullptr); }
        symbol->release();
        result = -1; // From here a failed readback holds the last frame, never copies uncertain data.
        if (q.status == 0x65u || callResult != kIOReturnSuccess) {
            // A timed-out DMA may still target this prepared buffer. Match pageoff's quarantine.
            gNVSVStageBuf = nullptr;
            if (q.status == 0x65u) OSAddAtomic64(1, &gDirectTimeout);
        }
        if (callResult != kIOReturnSuccess || q.status != 0) break;
        NVRMVramRequest scanout; nvSVZero(&scanout, sizeof scanout);
        scanout.version = NVRM_VRAM_ABI_VERSION;
        if (a->askFramebufferForScanout(&scanout, fb) != kIOReturnSuccess || !scanout.kva ||
            scanout.width != w || scanout.height != height) break;
        bool copied;
        { NMPerfScope timing(&gPerfCopy);
          copied = nvMuxlessCopy((volatile uint32_t *)scanout.kva, scanout.actualSize, scanout.pitch,
                     (const volatile uint32_t *)stage->getBytesNoCopy(), length, (uint32_t)pitch,
                     (uint32_t)w, (uint32_t)height,
                     __atomic_load_n(&gNvMuxlessCopy64, __ATOMIC_RELAXED) == 1); }
        if (!copied) break;
        // Keep valid[0] clear and nvSVPend set. A later CPU reader must still pageoff into its RAM.
        result = 1;
    } while (false);
    if (pages) IOFree(pages, pageCount * sizeof *pages);
    if (stageLock) IOLockUnlock(stageLock);
    if (cache) ((OSObject *)cache)->release();
    nvFamUnlock(a);
    // Stop after the first uncertain readback; do not allocate/quarantine a new buffer every frame.
    if (result < 0) __atomic_store_n(&gNvDirectPresent, 0, __ATOMIC_RELAXED);
    OSAddAtomic64(1, result > 0 ? &gDirectOK : result < 0 ? &gDirectHeld : &gDirectFallback);
    return result;
}
