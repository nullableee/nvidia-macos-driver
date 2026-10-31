#!/usr/bin/env python3
"""Exercise production AGDC target selection, slot map and 0x980 response.
Mocked registry/kernel only; not an IOPresentment hardware qualification.
"""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1];source=(R/'kexts/NVRMAGDC/nvrm-agdc.cpp').read_text()
def method(signature):
 a=source.index(signature);i=source.index('{',a);depth=1;j=i+1
 while depth:depth+=(source[j]=='{')-(source[j]=='}');j+=1
 return source[a:j]
fixture=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "nvrm-agdc-k5.h"
#define FBLOG(...) do{}while(0)
#define OSDynamicCast(T,p) dynamic_cast<T*>(p)
#define OSSafeReleaseNULL(p) do{if(p){(p)->release();(p)=nullptr;}}while(0)
struct OSObject {int refs=1;virtual ~OSObject()=default;virtual void release(){assert(refs>0);--refs;}void retain(){++refs;}};
struct OSNumber:OSObject {unsigned value=0;unsigned unsigned32BitValue(){return value;}};
struct OSDictionary:OSObject{std::string name;OSDictionary(const char*n):name(n){}void release()override{delete this;}};
struct OSIterator:OSObject{std::vector<OSObject*> objects;unsigned i=0;OSObject *getNextObject(){return i<objects.size()?objects[i++]:nullptr;}void release()override{delete this;}};
struct IOService;static std::map<std::string,std::vector<IOService*>> registry;
struct IOService:OSObject {
 std::string cls;IOService *parent=nullptr;OSNumber index;uint64_t rid;
 IOService(const char*n,uint64_t id,IOService *p=nullptr):cls(n),parent(p),rid(id){}
 IOService *getProvider(){return parent;}void *metaCast(const char*n){return cls==n?this:nullptr;}
 const char *getName(){return cls.c_str();}uint64_t getRegistryEntryID(){return rid;}
 OSObject *getProperty(const char*){return &index;}OSObject *copyProperty(const char*){index.retain();return &index;}
 static OSDictionary *serviceMatching(const char*n){return new OSDictionary(n);}
 static IOService *copyMatchingService(OSDictionary *m){auto &v=registry[m->name];if(v.empty())return nullptr;v[0]->retain();return v[0];}
 static OSIterator *getMatchingServices(OSDictionary *m){auto *it=new OSIterator;for(auto *s:registry[m->name])it->objects.push_back(s);return it;}
};
static bool enabled; static int gAgdcTargetWhy;
static bool PE_parse_boot_argn(const char*,void *p,unsigned n){assert(n==4);*(uint32_t*)p=enabled?1:0;return enabled;}
static const unsigned kAgdcMaxFB=4;static IOService *gAgdcFB[4];static unsigned gAgdcNFB;
static IOService *gAgdcFBRef,*gAgdcMuxlessPCI;static char gAgdcFBMap[256];static int gAgdcScanLogged;
#define SCANLOG(...) do{}while(0)
'''
fixture+=method('static void nvdaAgdcDropTable(void)')+'\n'+method('static void nvdaAgdcDropFB(void)')+'\n'
fixture+=method('static IOService *nvdaPciAncestor(')+'\n'+method('static bool nvdaAgdcMuxlessTargets(')+'\n'+method('static void nvdaAgdcTargets(')+'\n'
# Skip the forward declaration and extract the actual scan body.
scan=source.index('static void nvdaAgdcScan(IOService *pci)\n{');end=source.index('\nstatic SInt32 gAgdcBusy',scan)
fixture+=source[scan:end]+'\n'
structs=source[source.index('#pragma pack(push, 1)'):source.index('static int    gAgdcK5 =')]
fixture+=structs+r'''
using IOReturn=int;struct IOExternalMethodArguments{};
static const int kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnUnsupported=2;
static long long gAgdcCmds,gAgdcUnsupported;static int gAgdcK5,gAgdcLastRefused,gAgdcLogged,gAgdcMaxFBOut;
static void OSAddAtomic64(int n,long long*p){*p+=n;}

#define bzero mock_bzero
#define strlcpy mock_strlcpy
static void mock_bzero(void*p,unsigned long n){memset(p,0,n);}
static void mock_strlcpy(char*d,const char*s,unsigned long n){snprintf(d,n,"%s",s);}
static void nvdaAgdcRescanForReply(IOService*p){nvdaAgdcScan(p);}
static IOReturn nvdaK5Answer(IOService*,unsigned,unsigned long*,unsigned long,unsigned long*,unsigned long*){return kIOReturnUnsupported;}
struct NVDADeviceControl{IOService *fPci,*fFB;IOReturn vendor_doDeviceAttribute(unsigned,unsigned long*,unsigned long,unsigned long*,unsigned long*,IOExternalMethodArguments*);};
'''
fixture+=method('IOReturn NVDADeviceControl::vendor_doDeviceAttribute(')+'\n'
fixture+=r'''
int main(){
 IOService intel("IOPCIDevice",1),nvidia("IOPCIDevice",2),panel("NMIntelFB",3,&intel),broker("NVRMRenderBridge",4,&nvidia),broker2("NVRMRenderBridge",5,&nvidia),display("NVRMNVDAFramebuffer",6,&nvidia);
 registry["NMIntelFB"]={&panel};registry["NVRMRenderBridge"]={&broker};
 IOService *pci=nullptr,*fb=nullptr;
 enabled=false;nvdaAgdcTargets(&pci,&fb);assert(!pci&&!fb&&panel.refs==1);
 enabled=true;panel.index.value=4;nvdaAgdcTargets(&pci,&fb);assert(!pci&&!fb&&panel.refs==1);
 panel.index.value=0;registry["NVRMRenderBridge"]={};nvdaAgdcTargets(&pci,&fb);assert(!pci&&!fb&&panel.refs==1);
 registry["NVRMRenderBridge"]={&broker,&broker2};nvdaAgdcTargets(&pci,&fb);assert(!pci&&!fb&&panel.refs==1);
 registry["NVRMRenderBridge"]={&broker};nvdaAgdcTargets(&pci,&fb);
 assert(pci==&nvidia&&fb==&panel&&pci!=panel.getProvider());
 nvdaAgdcScan(pci);assert(gAgdcNFB==1&&gAgdcFB[0]==&panel&&strstr(gAgdcFBMap,"muxless Intel"));
 NVDADeviceControl control{pci,fb};alignas(8) NVAGDCGPUCapability cap;memset(&cap,0xff,sizeof cap);unsigned long bytes=sizeof cap;
 assert(control.vendor_doDeviceAttribute(0x980,nullptr,0,(unsigned long*)&cap,&bytes,nullptr)==0);
 assert(cap.maxFramebuffers==1&&cap.framebuffer[0]==&panel&&cap.pciDevice==&nvidia&&cap.portMask==2);
 bytes=1;assert(control.vendor_doDeviceAttribute(0x980,nullptr,0,(unsigned long*)&cap,&bytes,nullptr)==kIOReturnBadArgument);
 nvdaAgdcDropFB();assert(panel.refs==1&&nvidia.refs==1&&!gAgdcNFB);
 registry["NVRMNVDAFramebuffer"]={&display};nvdaAgdcTargets(&pci,&fb);
 assert(pci==&nvidia&&fb==&panel);nvdaAgdcDropFB();
 registry["NVRMRenderBridge"]={};nvdaAgdcTargets(&pci,&fb);
 assert(!pci&&!fb); // refuse a dummy NVIDIA head when the muxless broker is unavailable
 registry["NVRMRenderBridge"]={&broker};
 enabled=false;nvdaAgdcTargets(&pci,&fb);
 assert(pci==&nvidia&&fb==&display&&!gAgdcMuxlessPCI);nvdaAgdcScan(pci);
 assert(gAgdcNFB==1&&gAgdcFB[0]==&display);nvdaAgdcDropFB();assert(display.refs==1);
 puts("PASS: production AGDC opt-in, legacy-index refusal, missing/ambiguous broker refusal, Intel slot zero on NVIDIA renderer, exact 0x980 map, reference balance, desktop fallback");
}
'''
with tempfile.TemporaryDirectory(prefix='g6mf-agdc-') as d:
 d=Path(d);(d/'test.cpp').write_text(fixture)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(R/'kexts/NVRMAGDC'),str(d/'test.cpp'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
