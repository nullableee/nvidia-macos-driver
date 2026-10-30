#!/usr/bin/env python3
"""Execute production serial router and import rebinder against a mock Darwin VM."""
from pathlib import Path
import subprocess,tempfile,re
R=Path(__file__).resolve().parents[1]
source=(R/'tools/g6mf_lut_serial.c').read_text()
for name in ['dlopen','dlsym','getprogname','strcmp','open','read','close','syslog']:
 if name=='strcmp':continue
 source=re.sub(r'\b'+name+r'\b','fixture_'+name,source)
fixture=r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
@@SOURCE@@
static unsigned char *image;
static const char *process="WindowServer",*config="1\n";
static int vm_prot=1,protect_calls,fail_initial,fail_restore,executable,delegated;
static U32 fakeTask=12;
static unsigned visits[16384];static unsigned last,ordered;
static void visitor(void *block,unsigned long i){(void)block;assert(i<16384);++visits[i];if(i!=last++)ordered=0;}
static void parallel(unsigned long n,void *queue,void *block){(void)queue;++delegated;struct Block*b=block;for(unsigned long i=n;i>0;--i)b->invoke(block,i-1);}
static void **slot(void){return (void**)(image+0x180000);}
static U32 countImages(void){return 1;}
static const unsigned char *header(U32 i){(void)i;return image;}
static const char *imageName(U32 i){(void)i;return "/System/Library/Frameworks/CoreDisplay.framework/Versions/A/CoreDisplay";}
static int region(U32 task,U64*a,U64*s,int flavor,int*info,U32*n,U32*obj){assert(task==12&&flavor==9&&*n>=9);*a=(U64)image;*s=0x200000;info[0]=executable?5:vm_prot;info[1]=3;*n=9;*obj=7;return 0;}
static int pageSize(void){return 4096;}
static int deallocate(U32 task,U32 obj){assert(task==12&&obj==7);return 0;}
static int protect(U32 task,U64 a,U64 n,int max,int prot){assert(task==12&&a==((U64)slot()&~4095ull)&&n==4096&&!max);++protect_calls;if((protect_calls==1&&fail_initial)||(protect_calls==2&&fail_restore))return 1;vm_prot=prot&7;return 0;}
void *fixture_dlopen(const char*s,int flags){(void)s;(void)flags;return &fakeTask;}
void *fixture_dlsym(void*h,const char*s){(void)h;
#define RESOLVE(k,f) if(!strcmp(s,k))return (void*)(f)
 RESOLVE("mach_vm_region",region);RESOLVE("mach_vm_protect",protect);RESOLVE("mach_port_deallocate",deallocate);RESOLVE("mach_task_self_",&fakeTask);RESOLVE("getpagesize",pageSize);
 RESOLVE("_dyld_image_count",countImages);RESOLVE("_dyld_get_image_header",header);RESOLVE("_dyld_get_image_name",imageName);RESOLVE("dispatch_apply",parallel);
 return 0;
}
const char *fixture_getprogname(void){return process;}
int fixture_open(const char*s,int f,...){(void)s;(void)f;return 3;}
long fixture_read(int fd,void*b,unsigned long n){assert(fd==3);unsigned long z=strlen(config);if(z>n)z=n;memcpy(b,config,z);return z;}
int fixture_close(int fd){assert(fd==3);return 0;}
void fixture_syslog(int level,const char*f,...){(void)level;(void)f;}
static void put32(unsigned off,U32 x){memcpy(image+off,&x,4);}
static void put64(unsigned off,U64 x){memcpy(image+off,&x,8);}
static void reset(void){
 memset(image,0,0x200000);installed=seen=0;importSlot=0;originalApply=0;lutReturn=lutInvoke=0;
 vm_prot=1;protect_calls=fail_initial=fail_restore=executable=delegated=0;process="WindowServer";config="1\n";
 put32(0,0xfeedfacf);put32(4,0x1000007);put32(16,2);put32(20,96);
 put32(32,0x1b);put32(36,24);memcpy(image+40,uuid,16);
 put32(56,0x19);put32(60,72);memcpy(image+64,"__TEXT",7);put64(80,0x7ff805347000ull);
 unsigned call=0x7ff80540bbadull-0x7ff805347000ull,stub=0x7ff80543a230ull-0x7ff805347000ull;
 image[call]=0xe8;put32(call+1,stub-call-5);image[stub]=0xff;image[stub+1]=0x25;put32(stub+2,0x180000-stub-6);
 *slot()=(void*)parallel;
}
static void expectOriginal(void){assert(!installed&&*slot()==(void*)parallel&&vm_prot==1);}
int main(void){
 image=aligned_alloc(4096,0x200000);assert(image);
 reset();installSerial();assert(installed&&*slot()==(void*)selectedApply&&vm_prot==1&&protect_calls==2);
 assert(g6mfLUTSerialSelfTest());
 // Selective route: the production call site AND the production block must match.
 struct Block b={0,0,0,visitor};lutInvoke=(U64)visitor;
 memset(visits,0,sizeof visits);last=0;ordered=1;
 routeApply(1024,0,&b,lutReturn);assert(!delegated&&ordered&&last==1024);
 for(unsigned i=0;i<16384;i++)assert(visits[i]==(i<1024));
 routeApply(3,0,&b,lutReturn+1);assert(delegated==1);
 lutInvoke++;routeApply(3,0,&b,lutReturn);assert(delegated==2);
 assert(!eligible(0,&b,lutReturn)&&!eligible(16385,&b,lutReturn)&&!eligible(1,0,lutReturn));
 reset();process="Finder";installSerial();expectOriginal();assert(!protect_calls);
 for(unsigned i=0;i<5;i++){reset();config=(const char*[]){"0\n","1x","1\nX","","10"}[i];installSerial();expectOriginal();}
 reset();image[40]^=1;installSerial();expectOriginal();
 reset();image[0xc4bad]=0;installSerial();expectOriginal();
 reset();fail_initial=1;installSerial();expectOriginal();assert(protect_calls==1);
 reset();fail_restore=1;installSerial();expectOriginal();assert(protect_calls==3);
 reset();executable=1;installSerial();expectOriginal();assert(!protect_calls);
 reset();image[36]=8;installSerial();expectOriginal();
 free(image);puts("PASS: production serial router, 1024 exact ordered iterations, delegation, process/config/UUID/site refusal, private data protection, restoration failure rollback; mock Darwin only");
}
'''.replace('@@SOURCE@@',source)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(fixture)
 subprocess.run(['clang','-std=c11','-O2','-g','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
