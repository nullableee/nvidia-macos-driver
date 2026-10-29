#!/usr/bin/env python3
"""Run the production real-FB start method with allocation failure injection."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
text=(R/'kexts/NMIntelFB/intelfb.cpp').read_text();begin=text.index('bool NMIntelFB::start(');end=text.index('\nvoid NMIntelFB::stop(',begin)
fixture=r'''
#include <cassert>
#include "nv_muxless_topology.h"
#include "nvrm-agdc-k5.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#define IFBLOG(...) do{}while(0)
#define OSDynamicCast(T,p) dynamic_cast<T*>(p)
#define OSSafeReleaseNULL(p) do{if(p){(p)->release();(p)=nullptr;}}while(0)
using IOPhysicalLength=uint64_t;
static int fault,starts,live,timers,backlights,armed;
enum {kIOPCIConfigBaseAddress0=0,kIOPCIConfigBaseAddress2=2,kIOMapWriteCombineCache=0,kIOServiceSynchronous=0,kPowerStates=0};
static void *kOSBooleanTrue=(void*)1;
struct IOService{virtual ~IOService()=default;uint32_t captured[13]={};virtual bool setProperty(const char*,void *data,unsigned length){assert(length==sizeof captured);memcpy(captured,data,length);return fault!=9;}};
struct IOMemoryMap{
 IOMemoryMap(){++live;} void release(){--live;delete this;}
 uint64_t getLength(){return fault==2?8:0x1000000;}
 uintptr_t getVirtualAddress(){return 0x123000;}
};
struct IODeviceMemory{
 uint64_t getPhysicalAddress(){return 0x4000000000ull;}
 uint64_t getLength(){return 256ull<<20;}
 static IODeviceMemory *withRange(uint64_t,uint64_t){return fault==5?nullptr:new IODeviceMemory;}
 IOMemoryMap *map(int){return fault==6?nullptr:new IOMemoryMap;}
 void release(){delete this;}
};
struct IOPCIDevice:IOService{
 void setMemoryEnable(bool){}
 IOMemoryMap *mapDeviceMemoryWithRegister(int){return fault==1?nullptr:new IOMemoryMap;}
 IODeviceMemory *getDeviceMemoryWithRegister(int){static IODeviceMemory ap;return fault==3?nullptr:&ap;}
};
static void *thread_call_allocate(void(*)(void*,void*),void*){if(fault==7)return nullptr;++timers;return (void*)1;}
static void thread_call_free(void*){--timers;}
struct Backlight{Backlight(){++backlights;}void terminate(int){}void detach(void*){}void release(){--backlights;delete this;}};
struct IOFramebuffer:IOService{bool start(IOService*);};
struct NMIntelFB:IOFramebuffer{
 IOPCIDevice *fPCI=nullptr;IOMemoryMap *fMMIO=nullptr,*fSurfMap=nullptr;
 volatile uint8_t *fRegs=nullptr;uint64_t fApertureBase=0,fApertureLen=0;
 unsigned fWidth=1920,fHeight=1200,fRowBytes=7680,fSurf=0,fPipe=0,fVer=13;
 unsigned fHSS=1944,fHSE=1960,fHT=2080,fVSS=1203,fVSE=1209,fVT=1300,fRefresh16=165u<<16;uint64_t fPclk=446160000;
 void *fVblTimer=nullptr;Backlight *fBacklight=nullptr;
 bool depID=false,depIndex=false;uint64_t group=0,index=99;
 bool adoptFirmwareMode(){return fault!=4;}
 void publishBacklight(){fBacklight=new Backlight;}
 void setProperty(const char *n,uint64_t value,int){if(!strcmp(n,"IOFBDependentID")){depID=true;group=value;}if(!strcmp(n,"IOFBDependentIndex")){depIndex=true;index=value;}}
 void setProperty(const char*,const char*){} void setProperty(const char*,void*){}
 static void vblFire(void*,void*){}
 void armVbl(){++armed;}void registerPowerDriver(void*,int,int){}
 bool start(IOService*);
 void cleanup(){if(fVblTimer){thread_call_free(fVblTimer);fVblTimer=nullptr;}OSSafeReleaseNULL(fBacklight);OSSafeReleaseNULL(fSurfMap);OSSafeReleaseNULL(fMMIO);}
};
bool IOFramebuffer::start(IOService*){
 ++starts;auto *fb=static_cast<NMIntelFB*>(this);
 // The superclass can publish/open immediately. No allocation may be pending.
 assert(starts==1 && fb->fSurfMap && fb->fVblTimer && fb->depID && fb->depIndex && fb->fBacklight);
 assert(fb->index==0 && fb->group==kNMIntelControllerID);
 assert(nmMuxlessHead(true,fb->index)==4 && nmMuxlessHead(false,2)==2);
 // IOGraphics extGetAttribute('wsup') unconditionally uses fFbs[0].
 NMIntelFB *controller[5]={};controller[fb->index]=fb;
 assert(controller[0]==fb);
 return fault!=8;
}
'''+text[text.index('static bool nmIntelPublishTiming('):begin]+text[begin:end]+r'''
int main(){
 for(fault=0;fault<=9;++fault){
  starts=0;armed=0;NMIntelFB fb;IOPCIDevice pci;bool result=fb.start(&pci);
  assert(result==(fault==0));assert(starts==((fault==0||fault==8)?1:0));
  assert(armed==(fault==0?1:0));
  if(fault)assert(live==0 && timers==0 && backlights==0);
  if(!fault){assert(nvk5_timing_bad(fb.captured,sizeof fb.captured)==0);assert(fb.captured[NVK5_T_HVIS]==1920 && fb.captured[NVK5_T_VVIS]==1200);}
  fb.cleanup();assert(live==0 && timers==0 && backlights==0);
 }
 puts("PASS: real framebuffer starts superclass once after scanout/timer/dependencies, and cleans every injected failure");
 puts("PASS: Intel controller has slot zero for the IOGraphics wsup path; render slot remains four");
}
'''
with tempfile.TemporaryDirectory(prefix='g6mf-start-') as d:
 d=Path(d);(d/'test.cpp').write_text(fixture)
 subprocess.run(['clang++','-I'+str(R/'kexts/NVRM/accel'),'-I'+str(R/'kexts/NVRMAGDC'),'-std=c++17','-fsanitize=address,undefined',str(d/'test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)

# Exercise the exact routing method used by NVAccel's publication callback.
source=(R/'kexts/NVRM/accel/nvrm-accel.cpp').read_text()
a=source.index('    static unsigned framebufferSlot(');b=source.index('    static bool fbPublished(',a)
route=r"""
#include <cassert>
#include <cstring>
#include "nv_muxless_topology.h"
struct OSObject {virtual ~OSObject()=default;};
struct OSNumber:OSObject {unsigned value;unsigned unsigned32BitValue(){return value;}};
#define OSDynamicCast(T,p) dynamic_cast<T*>(p)
struct IOService {bool intel=false,missing=false;OSNumber index;
 OSObject *getProperty(const char*){return missing?nullptr:&index;}
 void *metaCast(const char *s){return intel&&!strcmp(s,"NMIntelFB")?this:nullptr;}
};
struct Accel {
"""+source[a:b]+r"""
};
int main(){
 IOService fb;fb.intel=true;fb.index.value=0;assert(Accel::framebufferSlot(&fb)==4);
 fb.index.value=4;assert(Accel::framebufferSlot(&fb)==4);
 fb.intel=false;fb.index.value=0;assert(Accel::framebufferSlot(&fb)==0);
 fb.index.value=3;assert(Accel::framebufferSlot(&fb)==3);
 fb.missing=true;assert(Accel::framebufferSlot(&fb)==0);
}
"""
with tempfile.TemporaryDirectory(prefix='g6mf-route-') as d:
 d=Path(d);(d/'route.cpp').write_text(route)
 subprocess.run(['clang++','-I'+str(R/'kexts/NVRM/accel'),'-I'+str(R/'kexts/NVRMAGDC'),'-std=c++17','-fsanitize=address,undefined',str(d/'route.cpp'),'-o',str(d/'route')],check=True)
 subprocess.run([str(d/'route')],check=True)
 print('PASS: production NVAccel callback routing keeps Intel render head 4 independently of dense IOGraphics index 0')
