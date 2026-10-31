from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <IOKit/IOKitLib.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdatomic.h>
#include "kexts/NVRM/nvrm_surfshare_abi.h"
static int mode,opens,services;static _Atomic unsigned calls;
static const char *program(void){return mode==5?"Safari":"WindowServer";}
static CFMutableDictionaryRef matching(const char*n){return (CFMutableDictionaryRef)(uintptr_t)(!strcmp(n,"NVAccel")?1:2);}
static io_service_t mockService(mach_port_t p,CFDictionaryRef m){services++;return (io_service_t)(uintptr_t)m;}
static kern_return_t open_service(io_service_t s,task_port_t t,uint32_t type,io_connect_t *out){
 opens++;assert(type==(s==1?0x4e560000u:0));if(mode==2||(mode==1&&s==1))return KERN_FAILURE;*out=700+s;return KERN_SUCCESS;}
static kern_return_t release(io_object_t o){return KERN_SUCCESS;}
static kern_return_t call(io_connect_t port,uint32_t selector,const uint64_t*scalar,uint32_t sn,const void*in,size_t n,uint64_t*so,uint32_t*son,void*out,size_t*size){
 // The normal rendering client (42) is deliberately unavailable. The new
 // completion path must never use it, even while concurrent callers release.
 assert(port==701||port==702);assert(selector==1&&sn==1&&*scalar==NVRM_ESC_SURF_DIRTY);
 assert(n==sizeof(struct NVRMSurfShareEsc));const struct NVRMSurfShareEsc*r=in;
 assert(r->version==NVRM_SURFSHARE_VERSION&&(r->plane==NVRM_SS_PLANE_GPU_MARK||r->plane==(NVRM_SS_PLANE_GPU_MARK|1)));
 atomic_fetch_add(&calls,1);if(mode==3)return KERN_FAILURE;
 ((struct NVRMSurfShareEsc*)out)->status=0;if(mode==4)*size=0;return KERN_SUCCESS;
}
#define getprogname program
#define IOServiceMatching matching
#define IOServiceGetMatchingService mockService
#define IOServiceOpen open_service
#define IOObjectRelease release
#define IOConnectCallMethod call
#include "plugin/g6mf_completion_channel.h"
static void *worker(void*ignored){for(unsigned i=0;i<1000;i++)assert(g6mf_completion_mark(17,i&1)==0);return NULL;}
int main(int argc,char**argv){mode=atoi(argv[1]);
 if(mode==0||mode==1){pthread_t th[4];for(unsigned i=0;i<4;i++)assert(!pthread_create(th+i,NULL,worker,NULL));for(unsigned i=0;i<4;i++)pthread_join(th[i],NULL);assert(opens==(mode==1?2:1));assert(calls==4000);}
 else {assert(g6mf_completion_mark(0,0)==NVRM_SS_OFF);assert(g6mf_completion_mark(17,0)==NVRM_SS_OFF);}
 uint64_t stats[3];g6mf_completion_channel_stats(stats);
 if(mode==2)assert(!stats[0]&&!stats[1]&&opens==2);
 if(mode==3||mode==4)assert(stats[0]&&stats[1]==2&&stats[2]==2);
 if(mode==5)assert(!opens&&!services&&!stats[0]);
 printf("PASS completion channel mode%d: carrier/fallback/denied/IO-error/short-output/non-WS, dedicated requests=%u\n",mode,calls);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(fixture)
 subprocess.run(['xcrun','clang','-O1','-fsanitize=address,undefined','-I'+str(root),str(p/'test.c'),'-framework','IOKit','-framework','CoreFoundation','-o',str(p/'test')],check=True)
 for mode in range(6):subprocess.run([str(p/'test'),str(mode)],check=True)
