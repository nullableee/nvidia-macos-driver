#!/usr/bin/env python3
"""Run the production CPU-only memory and resource lifecycle with a mock kernel.
No hardware presentation is emulated or claimed by this test.
"""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
h=(R/'kexts/NVRM/accel/nv_muxless_memory.h').read_text()
a=h.index('extern "C" __attribute__((naked))')
b=h.index('\nclass NMMuxlessScanoutMemory',a)
h=h[:a]+'static void nmIntelMemoryBaseFree(IOAccelMemory *) { ++base_frees; }\n'+h[b:]
s=(R/'kexts/NVRM/accel/nvrm-accel.cpp').read_text()
start=s.index('bool NVResource::prepare()\n{');end=s.index('bool NVResource::addToAperture()',start)
methods=s[start:end]
fixture=r'''
#include <cstdint>
#include <cassert>
#include <cstring>
using SInt32=int32_t;using IOReturn=int;
constexpr int kIOReturnSuccess=0,NVRM_VRAM_ABI_VERSION=1;
#define NVRM_VRAM_FN_SCANOUT "scanout"
#define OSDeclareDefaultStructors(C)
#define OSDefineMetaClassAndStructors(C,B)
#define OSDynamicCast(T,p) dynamic_cast<T *>(p)
struct OSObject {virtual ~OSObject(){};int refs=1;void retain(){++refs;}void release(){--refs;}};
struct IOAccelTask {};struct IOGraphicsAccelerator2 {};
struct OSSymbol {static const OSSymbol*withCStringNoCopy(const char*){static OSSymbol s;return &s;}void release()const{}};
struct NVRMVramRequest {unsigned version=1;void*kva=nullptr;uint64_t phys=0,actualSize=0;unsigned width=0,height=0,pitch=0;};
struct IOService:OSObject {
 NVRMVramRequest live;bool inactive=false,intel=true;int answer=0;
 void*metaCast(const char*){return intel?this:nullptr;}bool isInactive(){return inactive;}
 int callPlatformFunction(const OSSymbol*,bool,void*p,void*,void*,void*){*(NVRMVramRequest*)p=live;return answer;}
};
static int base_frees=0,base_prepares=0,base_completes=0;
static bool base_init=true;
struct IOAccelMemory {
 virtual ~IOAccelMemory(){};unsigned char opaque[0xb0-sizeof(void*)]={};
 virtual bool init(IOGraphicsAccelerator2*){return base_init;}
 virtual uint64_t getLength()const=0;virtual uint64_t getDirtySize()const=0;virtual uint64_t getResidentSize()const=0;
 virtual OSObject*createMappingInTask(IOAccelTask*,unsigned)=0;
 virtual OSObject*createMappingInTaskAtAddressLength(IOAccelTask*,unsigned,unsigned long long,unsigned long long)=0;
 virtual bool prepare()=0;virtual bool complete()=0;
 virtual uint64_t getPhysicalSegment(unsigned long long,unsigned long long*)=0;
 virtual void setPurgeable(unsigned,unsigned*)=0;virtual uint64_t setTag(unsigned)=0;virtual uint64_t getTag()=0;
 virtual bool matchForReuse(void*,unsigned long long)=0;virtual void wire()=0;virtual void unwire()=0;
 virtual void increment_wire_count()=0;virtual void decrement_wire_count()=0;virtual void free()=0;
};
static_assert(sizeof(IOAccelMemory)==0xb0);
@@MEMORY@@
struct IOAccelResource2 {virtual ~IOAccelResource2(){};unsigned char opaque[0x180-sizeof(void*)]={};
 virtual bool prepare(){++base_prepares;return false;}virtual bool complete(){++base_completes;return false;}};
struct NVResource:IOAccelResource2 {SInt32 fCPUScanoutPrepares=0;bool prepare()override;bool complete()override;
 void backing(OSObject*p){memcpy((char*)this+0x88,&p,sizeof p);}};
static void OSIncrementAtomic(SInt32*p){++*p;}static void OSDecrementAtomic(SInt32*p){--*p;}
@@METHODS@@
int main(){
 IOService panel;IGraphics:;IOGraphicsAccelerator2 accel;
 unsigned pixel=0;panel.live.kva=&pixel;panel.live.actualSize=9216000;
 panel.live.width=1920;panel.live.height=1200;panel.live.pitch=7680;
 NMMuxlessScanoutMemory memory;
 assert(memory.initPanel(&accel,&panel,panel.live));assert(panel.refs==2);
 assert(memory.ready() && memory.getResidentSize()==9216000 && memory.getLength()==9216000);
 assert(*(uint64_t*)((char*)&memory+0x40)==9216000);
 unsigned long long length=99;assert(memory.getPhysicalSegment(0,&length)==0 && length==0);
 assert(!memory.createMappingInTask(nullptr,0));assert(!memory.createMappingInTaskAtAddressLength(nullptr,0,0,4096));
 // The production resource uses its backing slot; no NVIDIA mapping/prepare call.
 NVResource resource;OSObject*ptr=reinterpret_cast<OSObject*>(&memory);resource.backing(ptr);
 assert(resource.prepare() && resource.prepare() && resource.fCPUScanoutPrepares==2);
 assert(!base_prepares);assert(resource.complete() && resource.complete());
 assert(!resource.complete() && !base_completes && resource.fCPUScanoutPrepares==0);
 panel.inactive=true;assert(!resource.prepare());panel.inactive=false;
 panel.live.phys=123;assert(!resource.prepare());panel.live.phys=0;
 panel.live.pitch=7808;assert(!resource.prepare());panel.live.pitch=7680;
 panel.live.kva=nullptr;assert(!resource.prepare());panel.live.kva=&pixel;
 panel.answer=1;assert(!resource.prepare());panel.answer=0;
 assert(resource.prepare());panel.inactive=true;assert(resource.complete());panel.inactive=false;
 resource.backing(nullptr);assert(!resource.prepare() && base_prepares==1);assert(!resource.complete() && base_completes==1);
 memory.free();assert(panel.refs==1 && base_frees==1);
 for(unsigned failure=0;failure<5;++failure){
  NMMuxlessScanoutMemory rejected;auto bad=panel.live;
  if(failure==0)bad.phys=0x4000000000ull;
  if(failure==1)bad.pitch=4;
  if(failure==2)bad.actualSize=4096;
  if(failure==3)panel.intel=false;
  if(failure==4)base_init=false;
  assert(!rejected.initPanel(&accel,&panel,bad));assert(panel.refs==1);
  panel.intel=true;base_init=true;
 }
}
'''.replace('IOService panel;IGraphics:;','IOService panel;')
# The mock backing must share OSObject ancestry for dynamic_cast just as the kernel does.
fixture=fixture.replace('struct IOAccelMemory {','struct IOAccelMemory:OSObject {').replace('unsigned char opaque[0xb0-sizeof(void*)]','unsigned char opaque[0xb0-sizeof(OSObject)]')
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'IOAccelMemory.h').write_text('')
 (p/'test.cpp').write_text(fixture.replace('@@MEMORY@@',h).replace('@@METHODS@@',methods))
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+td,str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: production CPU-only resource lifecycle, foreign mapping refusal, stale scanout refusal, reference balance; mock kernel only')
