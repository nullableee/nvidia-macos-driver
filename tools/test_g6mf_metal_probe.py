#!/usr/bin/env python3
"""Check diagnostic success/failure decisions with a mocked Objective-C runtime.
This is not a Metal implementation or a GPU test.
"""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
fixture=r'''
#define dlopen fake_open
#define dlsym fake_symbol
#define dlerror fake_error
#define usleep fake_sleep
#define alarm fake_alarm
#define main probe_main
#include "g6mf_metal_probe.c"
#undef main
#undef dlopen
#undef dlsym
#undef dlerror
#undef usleep
#undef alarm
#include <stdarg.h>
#include <string.h>
#include <assert.h>
static int mode,allocated,compute;
static unsigned char source[4096],dest[4096];
static unsigned int input[1056],output[1056];
static Obj tag(unsigned long n){return (Obj)n;}
static void *selector(const char *s){return (void *)s;}
static Obj get_class(const char *s){(void)s;return tag(1);}
static Obj get_devices(void){return tag(10);}
static Obj message(Obj o,void *selector,...){
 const char *s=selector;va_list ap;va_start(ap,selector);Obj ret=0;
 if(!strcmp(s,"alloc") || !strcmp(s,"init"))ret=tag(1);
 else if(!strcmp(s,"count"))ret=tag(mode==1?0:1);
 else if(!strcmp(s,"objectAtIndex:"))ret=tag(2);
 else if(!strcmp(s,"name"))ret=tag(3);
 else if(!strcmp(s,"UTF8String"))ret=(Obj)"NVIDIA RTX test fixture";
 else if(!strcmp(s,"registryID"))ret=tag(0x12345);
 else if(!strcmp(s,"newBufferWithLength:options:")){
  Size bytes=va_arg(ap,Size);assert(bytes==(allocated<2?4096:4224));assert(va_arg(ap,Size)==0);
  ++allocated;ret=tag(allocated==1?4:allocated==2?5:allocated==3?12:13);
 }
 else if(!strcmp(s,"contents"))ret=o==tag(4)?(void*)source:o==tag(5)?(void*)dest:o==tag(12)?(void*)input:(void*)output;
 else if(!strcmp(s,"newCommandQueue"))ret=tag(6);
 else if(!strcmp(s,"commandBuffer"))ret=tag(7);
 else if(!strcmp(s,"blitCommandEncoder")){compute=0;ret=tag(8);}
#ifdef G6MF_SHADER_PROBE
 else if(!strcmp(s,"stringWithUTF8String:"))ret=(Obj)va_arg(ap,const char*);
 else if(!strcmp(s,"newLibraryWithSource:options:error:"))ret=mode==4?0:tag(20);
 else if(!strcmp(s,"newFunctionWithName:"))ret=tag(21);
 else if(!strcmp(s,"newComputePipelineStateWithFunction:error:"))ret=mode==5?0:tag(22);
 else if(!strcmp(s,"maxTotalThreadsPerThreadgroup"))ret=tag(1024);
 else if(!strcmp(s,"computeCommandEncoder")){compute=1;ret=tag(23);}
 else if(!strcmp(s,"dispatchThreadgroups:threadsPerThreadgroup:")){
  Dimensions grid=va_arg(ap,Dimensions),group=va_arg(ap,Dimensions);
  assert(grid.width*group.width==1024 && grid.height==1 && group.depth==1);
 }
#endif
 else if(!strcmp(s,"copyFromBuffer:sourceOffset:toBuffer:destinationOffset:size:")){
  assert(va_arg(ap,Obj)==tag(4));assert(va_arg(ap,Size)==0);
  assert(va_arg(ap,Obj)==tag(5));assert(va_arg(ap,Size)==0);assert(va_arg(ap,Size)==4096);
 }
 else if(!strcmp(s,"commit")){
  if(compute){
   for(unsigned i=0;i<1024;++i)output[i]=(input[i]*1664525u+1013904223u)^(i*0x9e3779b9u);
   if(mode==6)output[100]^=1;if(mode==7)output[1024]=0;
  }else{memcpy(dest,source,4096);if(mode==3)dest[100]^=1;}
 }
 else if(!strcmp(s,"status"))ret=tag(mode==2||(compute&&mode==8)?5:4);
 va_end(ap);return ret;
}
void *fake_open(const char *p,int f){(void)p;(void)f;return tag(1);}
void *fake_symbol(void *h,const char *s){
 (void)h;
 if(!strcmp(s,"objc_msgSend"))return (void *)message;
 if(!strcmp(s,"sel_registerName"))return (void *)selector;
 if(!strcmp(s,"MTLCopyAllDevices"))return (void *)get_devices;
 if(!strcmp(s,"objc_getClass"))return (void *)get_class;
 return 0;
}
char *fake_error(void){return "mock error";}
int fake_sleep(unsigned int t){(void)t;return 0;}
unsigned int fake_alarm(unsigned int t){(void)t;return 0;}
int main(void){
 unsigned modes=4;
#ifdef G6MF_SHADER_PROBE
 modes=9;
#endif
 for(mode=0;mode<(int)modes;++mode){allocated=compute=0;int result=probe_main();assert((result==0)==(mode==0));}
 puts("PASS: diagnostic accepts completed matching readback; refuses absent NVIDIA, command errors and corrupted readback");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='g6mf-metal-test-') as d:
 d=Path(d);(d/'mock.c').write_text(fixture)
 for flags in [[],['-DG6MF_SHADER_PROBE']]:
  subprocess.run(['clang','-O1','-fsanitize=address,undefined','-fno-sanitize=function']+flags+['-I'+str(R/'tools'),str(d/'mock.c'),'-o',str(d/'test')],check=True)
  subprocess.run([str(d/'test')],check=True)
 print('PASS: shader diagnostic refuses library/pipeline errors, corrupted compute values, overwritten guard and failed command')
