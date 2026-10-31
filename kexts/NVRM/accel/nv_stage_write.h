#pragma once
// Prepared, ordinary IOSurface RAM only; never use for MMIO/Intel scanout.
static IOByteCount nvStageWrite(IOMemoryDescriptor *md, const void *src,
                                IOByteCount len, bool mapped)
{
    if (!md || !src || !len || len > md->getLength()) return 0;
    if (mapped) {
        IOMemoryMap *m = md->map();
        if (m) {
            const auto address = m->getVirtualAddress();
            if (address && m->getLength() >= len) {
                bcopy(src, (void *)address, len);
                m->release();
                OSAddAtomic64(1, &gStageMapOk);
                return len;
            }
            m->release();
        }
        OSAddAtomic64(1, &gStageMapFallback);
    }
    return md->writeBytes(0, src, len);
}
