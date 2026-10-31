"""Compile the production direct-present function against fault-injecting kernel stubs.
This is a host correctness test, not a native IOAccel lifecycle or display test.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <string>
using SInt64=long long;using IOByteCount=unsigned long long;using addr64_t=uint64_t;using IOReturn=int;
const int kIOReturnSuccess=0,kIOMemoryMapperNone=0,NVRM_SS_RM_VERSION=1,NVRM_SS_OFF=99,NVRM_VRAM_ABI_VERSION=1;
#define NVRM_SS_FN_PAGEOFF "readback"
#define OSDynamicCast(T,p) static_cast<T*>(p)
struct NMPerfMetric{};struct NMPerfScope { NMPerfScope(NMPerfMetric*){} };
static SInt64 gDirectAttempts,gDirectOK,gDirectFallback,gDirectHeld,gDirectTimeout;
static NMPerfMetric gPerfDirectTotal,gPerfDirectCE,gPerfCopy;static int gNvMuxlessCopy64,gNvDirectPresent;
static std::vector<std::string> events;static int fault;
static constexpr unsigned kPixels=1920*1200+16;
static uint32_t pixels[kPixels],staging[kPixels],destination[kPixels],cpuRAM[kPixels];
static unsigned width=7,height=3,stride=40;
static void OSAddAtomic64(int v,SInt64*p){*p+=v;}
struct OSObject {void release(){events.push_back("cache-");}};
struct OSSymbol {static const OSSymbol*withCStringNoCopy(const char*){static OSSymbol s;return &s;}void release()const{}};
struct IOMemoryDescriptor {uint64_t getLength(){return fault==15?8:sizeof pixels;}};
struct IOSurface {uint64_t getWidth(){return fault==1?0:width;}uint64_t getHeight(){return height;}uint64_t getBytesPerRow(){return stride;}unsigned getPixelFormat(){return fault==2?0:0x42475241u;}unsigned getSurfaceID(){return 42;}IOMemoryDescriptor*getMemoryDescriptor(){static IOMemoryDescriptor md;return &md;}};
struct IOBufferMemoryDescriptor {addr64_t getPhysicalSegment(int,IOByteCount*n,int){*n=fault==16?1:sizeof staging;return 0x1000;}void*getBytesNoCopy(){return staging;}};
struct NVRMRmHandles{void*kapiDevice;};
struct NVRMSurfPageoff {unsigned version,status;void*kapiDevice,*kapiMemory;unsigned long long*pages;uint64_t pageCount,length,usec;};
struct NVRMVramRequest{unsigned version;void*kva;uint64_t actualSize;unsigned width,height,pitch;};
struct IOService {void*metaCast(const char*){return fault==3?nullptr:this;}IOReturn callPlatformFunction(const OSSymbol*,bool,NVRMSurfPageoff*q,void*,void*,void*){events.push_back("CE");assert(q->pages[0]==0x1000 && q->pageCount==(sizeof pixels+4095)/4096);memcpy(staging,pixels,sizeof pixels);q->status=fault==9?0x65:fault==10?7:0;return fault==17?1:0;}};
struct NVVidMemory{void*fRmHandle=(void*)1;uint64_t fBytes=sizeof pixels;bool fScanout=false;};
struct NVResource:OSObject{alignas(8)char reserve[256]{};};
struct Cache:OSObject{char pad[32]{};OSObject*ctx;};
static NVResource resource;static NVVidMemory memory;static Cache cache;static unsigned short valid[8];
struct NVAccel {int askFramebufferForScanout(NVRMVramRequest*q,IOService*){events.push_back("scanout");q->kva=destination;q->actualSize=fault==12?1:sizeof destination;q->width=fault==11?width+1:width;q->height=height;q->pitch=stride;return 0;}};
static bool nvFamLock(NVAccel*,bool){if(fault==4)return false;events.push_back("family+");return true;}
static void nvFamUnlock(NVAccel*){events.push_back("family-");}
static void* _ZN22IOGraphicsAccelerator223deviceCacheForIOSurfaceEP9IOSurfacej(void*,void*,int){if(fault==5)return nullptr;events.push_back("cache+");return &cache;}
static NVVidMemory*nvres_vidmem(NVResource*){return &memory;}
static bool nvAccelResPluginWrote(NVResource*){return fault!=6;}
static bool nvSVPend(unsigned,int op){assert(op==2);return fault!=7;}
static void nvSVZero(void*p,unsigned long n){memset(p,0,n);}
static IOService*nvAccelNVRM(){static IOService s;return &s;}
static bool nvAccelRmHandles(NVRMRmHandles*h){h->kapiDevice=(void*)2;return true;}
static bool nvSurfWaitReady(unsigned){events.push_back("ready");return fault!=8;}
struct IOLock{};static IOLock lock;
static IOLock*nvSVStageLock(){return &lock;}
static void IOLockLock(IOLock*){events.push_back("stage+");}
static void IOLockUnlock(IOLock*){events.push_back("stage-");}
static IOBufferMemoryDescriptor stage;static IOBufferMemoryDescriptor*gNVSVStageBuf=&stage;
static IOBufferMemoryDescriptor*nvSVStage(uint64_t){return fault==13?nullptr:gNVSVStageBuf;}
static void*IOMalloc(uint64_t n){return fault==14?nullptr:malloc(n);}
static void IOFree(void*p,uint64_t){free(p);}
#include "nv_muxless_copy.h"
#include "nv_direct_present.h"
int main(){
 for(int scenario=0;scenario<=20;scenario++){
  fault=scenario;gNvDirectPresent=1;events.clear();memset(valid,0,sizeof valid);valid[6]=1;
  if(scenario==18)valid[0]=1;if(scenario==19)valid[6]=0;
  memory.fRmHandle=scenario==20?nullptr:(void*)1;
  *(unsigned short**)((char*)&resource+0x30)=valid;cache.ctx=&resource;
  assert(*(OSObject**)((char*)&cache+0x20)==&resource);
  gNVSVStageBuf=&stage;
  for(unsigned i=0;i<kPixels;i++){pixels[i]=i*1103515245u+12345;destination[i]=0xdeadbeef;cpuRAM[i]=0xabcdef01;}
  auto saved=std::vector<unsigned short>(valid,valid+8);
  NVAccel a;IOService fb;IOSurface s;int result=nvAccelMuxlessDirect(&a,&fb,&s,4);
  if(scenario==0){assert(result==1);for(unsigned i=0;i<kPixels;i++)assert(destination[i]==((i/10<3&&i%10<7)?pixels[i]:0xdeadbeef));}
  else {assert(result==(scenario==8||scenario==9||scenario==10||scenario==11||scenario==12||scenario==17?-1:0));for(auto v:destination)assert(v==0xdeadbeef);}
  assert(gNvDirectPresent==(result<0?0:1));
  for(unsigned i=0;i<8;i++)assert(valid[i]==saved[i]);for(auto v:cpuRAM)assert(v==0xabcdef01);
  if(scenario==9||scenario==17)assert(!gNVSVStageBuf);
  int family=0,st=0,cacheRefs=0;
  for(auto&e:events){if(e=="family+"){assert(!family&&!st);family++;}if(e=="cache+"){assert(family);cacheRefs++;}if(e=="stage+"){assert(family);st++;}if(e=="CE"||e=="scanout")assert(family&&st);if(e=="stage-")st--;if(e=="cache-")cacheRefs--;if(e=="family-"){assert(!st&&!cacheRefs);family--;}}
  assert(!family&&!st&&!cacheRefs);
 }
 // Full panel, then another GPU write with CPU RAM still stale: both presents must show fresh pixels.
 fault=0;width=1920;height=1200;stride=width*4;valid[0]=0;valid[6]=1;memory.fRmHandle=(void*)1;gNVSVStageBuf=&stage;
 NVAccel a;IOService fb;IOSurface surface;
 for(unsigned frame=0;frame<2;frame++){
  for(unsigned i=0;i<kPixels;i++){pixels[i]=i*1103515245u+frame+17;destination[i]=0xdeadbeef;cpuRAM[i]=0xabcdef01;}
  assert(nvAccelMuxlessDirect(&a,&fb,&surface,4)==1);
  for(unsigned i=0;i<kPixels;i++){assert(destination[i]==(i<width*height?pixels[i]:0xdeadbeef));assert(cpuRAM[i]==0xabcdef01);}
  assert(valid[0]==0&&valid[6]==1);
 }
 assert(gDirectOK==3 && gDirectTimeout==1);
 puts("PASS: production direct present pixels/padding, 20 fault/state cases, CPU validity preserved, lock order, cleanup and timeout quarantine");
}
'''
with tempfile.TemporaryDirectory()as td:
 p=Path(td);(p/'test.cpp').write_text(fixture)
 subprocess.run(['xcrun','clang++','-std=c++17','-O2','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(root/'kexts/NVRM/accel'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
