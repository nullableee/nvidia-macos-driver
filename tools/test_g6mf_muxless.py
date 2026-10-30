#!/usr/bin/env python3
"""Compile/run production layout/copy code and actual head-registration methods."""
from pathlib import Path
import subprocess,tempfile,json
R=Path(__file__).resolve().parents[1]
src=(R/'kexts/NVRM/accel/nvrm-accel.cpp').read_text()
def body(text,signature):
 a=text.index(signature);i=text.index('{',a);depth=1;j=i+1
 while depth:
  depth += (text[j]=='{')-(text[j]=='}');j+=1
 return text[a:j]
fixture=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "nmintel_scanout.h"
#include "nv_muxless_copy.h"
#define ALOG(...) do {} while(0)
static unsigned gNvIgpu, gNvHeadsPublished, gNvHeadsRegistered, gNvHeadsPiped;
static const unsigned kNvMaxFB=5;
struct IOService { const char *getName(){return "test";} };
using IOFramebuffer=IOService;
struct FakePipe { uint8_t pad[0x98]={}; IOService *fb=nullptr; };
struct FakeDM {
 uint8_t pad[0x88]={}; FakePipe *pipes[16]={}; uint32_t count=0;
 bool nullPipe=false; FakePipe storage[5];
 unsigned getFramebufferCount(){return count;}
 void found_framebuffer(IOFramebuffer *fb){unsigned i=count++;storage[i].fb=fb;pipes[i]=nullPipe?nullptr:&storage[i];}
 void start(void*){}
};
static_assert(__builtin_offsetof(FakeDM,count)==0x108,"production count offset");
struct Accel {
 FakeDM *fDM=nullptr; IOService *fFB=nullptr; IOService *fFBs[5]={};
 unsigned fFBRegistered=0; bool backend=true; void *fPCI=nullptr; unsigned grew=0;
 IOService *renderBackend(){return backend?&service:nullptr;}
 IOService service;
 void onCountGrewLocked(){grew++;}
'''
fixture+=body(src,'    unsigned registerPendingLocked(')+'\n'+body(src,'    bool registerFramebufferLocked(')+'\n};\n'
fixture+=r'''
namespace FenceTest {
using IOLock=int;
static int lock;static IOLock *gSurfPendLock=&lock;
static unsigned gSurfGpuOn=1;
struct Entry {unsigned id;};static Entry gSurfPend[32];
static uint64_t now;static int gSurfWaitMaxUs;
static long long gCntSurfWaits,gCntSurfTimeouts;
static const unsigned kSurfGpuWaitMs=100,kMillisecondScale=1,THREAD_UNINT=0;
static uint64_t mach_absolute_time(){return now;}
static void clock_interval_to_deadline(unsigned,unsigned,uint64_t *d){*d=now+3;}
static void absolutetime_to_nanoseconds(uint64_t t,uint64_t *n){*n=t*1000;}
static void IOLockLock(IOLock*){} static void IOLockUnlock(IOLock*){}
static void IOLockSleepDeadline(IOLock*,void*,uint64_t d,unsigned){now=d;}
static void OSAddAtomic64(int n,long long *v){*v+=n;}
'''
fixture+=body(src,'static bool nvSurfWaitReady(unsigned int id)\n{')+'\n}\n'
fixture+=r'''
int main(){
 // Captured on G6 MF / Tahoe with NMIntelProbe 0.1.2, report
 // macOS-20261029-184502-745. Exercise the actual MMIO offsets as well
 // as the validator; zero surface offset is a valid firmware layout.
 std::vector<uint32_t> regs(0x74000/4,0);
 const uint32_t captured[4][7]={
  {0xc0000000u,0x94000008u,0x78u,0x04af077fu,0,0,0},
  {0,8,0,0,0,0,0}, {0,8,0,0,0,0,0}, {0,0,0,0,0,0,0}
 };
 const unsigned offsets[]={0x70008,0x70180,0x70188,0x70190,0x7019c,0x701a4,0x7018c};
 NMIntelLayout actual;
 unsigned active=0;
 for(unsigned pipe=0;pipe<4;++pipe){
  for(unsigned field=0;field<7;++field)
   regs[(offsets[field]+pipe*0x1000)/4]=captured[pipe][field];
  auto plane=nmIntelReadPlane(reinterpret_cast<const volatile uint8_t *>(regs.data()),pipe);
  auto result=nmIntelLayout(plane,268435456,actual);
  assert(result==(pipe==0?kNMIntelOK:kNMIntelDisabled));
  if(result==kNMIntelOK){
   ++active;
   assert(actual.width==1920 && actual.height==1200 && actual.pitch==7680);
   assert(actual.surface==0 && actual.bytes==9216000);
  }
 }
 assert(active==1);
 puts("PASS: captured Tahoe 0.1.2 MMIO snapshot: unique pipe A, 1920x1200, pitch 7680, surface zero");
 NMIntelPlane p={0x80000000u,0x84000000u,120,(1199u<<16)|1919,0x100000,0,0};
 NMIntelLayout out;
 assert(nmIntelLayout(p,256ull<<20,out)==kNMIntelOK);
 assert(out.width==1920 && out.height==1200 && out.pitch==7680 && out.bytes==9216000);
 auto bad=p;bad.ctl|=1u<<10;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelTiling);
 bad=p;bad.ctl|=1u<<15;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelTransform);
 bad=p;bad.offset=1;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelTransform);
 bad=p;bad.position=1;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelTransform);
 bad=p;bad.ctl|=1u<<20;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelTransform);
 bad=p;bad.stride=119;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelGeometry);
 bad=p;bad.ctl=0;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelDisabled);
 assert(nmIntelLayout(p,0x100000+9216000-1,out)==kNMIntelRange);
 assert(nmIntelLayout(p,0x100000+9216000,out)==kNMIntelOK);
 bad=p;bad.stride=2048;assert(nmIntelLayout(bad,256ull<<20,out)==kNMIntelOK && out.pitch==131072);
 // Old min(srcPitch,dstPitch) copy overwrote padding and failed to check dst capacity.
 uint32_t s[12]={1,2,3,99,98,97,4,5,6,96,95,94},d[10];
 for(auto &v:d)v=0xdeadbeef;
 assert(nvMuxlessCopy(d,40,20,s,48,24,3,2));
 assert(d[0]==1 && d[2]==3 && d[5]==4 && d[7]==6);
 assert(d[3]==0xdeadbeef && d[4]==0xdeadbeef && d[8]==0xdeadbeef);
 assert(!nvMuxlessCopy(d,39,20,s,48,24,3,2));
 assert(!nvMuxlessCopy(d,40,20,s,47,24,3,2));
 assert(!nvMuxlessCopy(d,40,10,s,48,24,3,2));
 assert(!nvMuxlessCopy(d,40,20,s,48,23,3,2));
 // Execute production registration with ONLY Intel head 4, no NVIDIA display head 0.
 gNvIgpu=1;gNvHeadsPublished=1u<<4;gNvHeadsPiped=0;
 FakeDM dm;Accel a;a.fDM=&dm;IOService intel;a.fFBs[4]=&intel;
 assert(a.registerFramebufferLocked(1));
 assert(dm.count==1 && dm.pipes[0]->fb==&intel && a.grew==1);
 assert(a.fFBRegistered==(1u<<4) && gNvHeadsPiped==(1u<<4));
 assert(!a.registerFramebufferLocked(1) && dm.count==1); // idempotent
 FakeDM dm2;Accel b;b.fDM=&dm2;b.fFBs[4]=&intel;b.backend=false;
 assert(!b.registerFramebufferLocked(1) && dm2.count==0);
 gNvIgpu=0;b.backend=true;assert(!b.registerFramebufferLocked(1) && dm2.count==0);
 gNvIgpu=1;FenceTest::gSurfPend[0].id=42;
 assert(!FenceTest::nvSurfWaitReady(42) && FenceTest::gSurfPend[0].id==42);
 gNvIgpu=0;assert(!FenceTest::nvSurfWaitReady(42) && FenceTest::gSurfPend[0].id==0);
 puts("PASS: production layout, exact aperture boundary, compression/offset rejection, padded copy, short buffers, Intel-only registration, idempotency and missing backend");
}
'''
with tempfile.TemporaryDirectory(prefix='g6mf-tests-') as d:
 p=Path(d);(p/'test.cpp').write_text(fixture)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I'+str(R/'kexts/NMIntelFB'),'-I'+str(R/'kexts/NVRM/accel'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
 # Prove the Intel-only fixture detects the upstream head-0 dependency.
 original=body(src,'    bool registerFramebufferLocked(')
 gate='if (!fFB && !(gNvIgpu && fFBs[4]))'
 assert original.count(gate)==1
 control=original.replace(gate,'if (!fFB)')
 oldfixture=fixture.replace(original,control)
 (p/'old.cpp').write_text(oldfixture)
 subprocess.run(['clang++','-std=c++17','-I'+str(R/'kexts/NMIntelFB'),'-I'+str(R/'kexts/NVRM/accel'),str(p/'old.cpp'),'-o',str(p/'old')],check=True)
 result=subprocess.run([str(p/'old')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert result.returncode!=0,'regression must fail on upstream method'
 print('PASS: head-0-only negative control fails the Intel-only registration regression')
