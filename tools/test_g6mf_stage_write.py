#!/usr/bin/env python3
"""Exercise production mapped pageoff copy, failed maps and short writes."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
code = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <strings.h>
using IOByteCount = unsigned long long;
using SInt64 = long long;
static SInt64 gStageMapOk, gStageMapFallback;
static void OSAddAtomic64(int n, SInt64 *p) { *p += n; }
struct IOMemoryMap {
    char data[32]{}; unsigned long long bytes=32; bool zero=false; int releases=0;
    uintptr_t getVirtualAddress() { return zero ? 0 : (uintptr_t)data; }
    unsigned long long getLength() { return bytes; }
    void release() { releases++; }
};
struct IOMemoryDescriptor {
    IOMemoryMap m; bool fail=false, shortWrite=false; int writes=0, maps=0;
    unsigned long long getLength() { return 32; }
    IOMemoryMap *map() { maps++; return fail ? nullptr : &m; }
    IOByteCount writeBytes(IOByteCount off, const void *s, IOByteCount n) {
        assert(off==0); writes++; if(shortWrite) n--; memcpy(m.data,s,n); return n;
    }
};
#include "nv_stage_write.h"
int main() {
    const char src[]="fresh frame";
    for (int mode=0;mode<5;mode++) {
        IOMemoryDescriptor md;
        md.fail=mode==1; md.m.bytes=mode==2?1:32; md.m.zero=mode==3;
        assert(nvStageWrite(&md,src,sizeof src,mode!=4)==sizeof src);
        assert(!memcmp(md.m.data,src,sizeof src));
        assert(md.m.data[sizeof src]==0);
        assert(md.writes==(mode==0?0:1));
        assert(md.maps==(mode==4?0:1));
        assert(md.m.releases==((mode==1||mode==4)?0:1));
    }
    assert(gStageMapOk==1 && gStageMapFallback==3);
    IOMemoryDescriptor md;
    assert(!nvStageWrite(&md,src,33,true));
    assert(!nvStageWrite(&md,nullptr,1,true));
    assert(!nvStageWrite(nullptr,src,1,true));
    assert(!nvStageWrite(&md,src,0,true));
    assert(md.maps==0 && md.writes==0);
    md.fail=true; md.shortWrite=true;
    assert(nvStageWrite(&md,src,sizeof src,true)==sizeof src-1);
}
'''
with tempfile.TemporaryDirectory() as td:
    p = Path(td)
    (p / 'test.cpp').write_text(code)
    subprocess.run(['clang++', '-std=c++17', '-fsanitize=address,undefined',
                    '-I' + str(root / 'kexts/NVRM/accel'), str(p / 'test.cpp'),
                    '-o', str(p / 'test')], check=True)
    subprocess.run([str(p / 'test')], check=True)
print('PASS: mapped copy, lifetime, map failure, invalid/short maps, bounds and short-write propagation')
