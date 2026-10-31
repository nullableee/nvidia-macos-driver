"""Exercise the production Objective-C LRU with synthetic import lifetimes and spans."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1];source=(root/'plugin/NVMTLDevice.m').read_text()
block=source[source.index('#include "g6mf_cache_policy.h"'):source.index('// Counts completed API calls')]
pre=r'''
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <assert.h>
static char g6mf_surface_hold_key;
static uint64_t fakeClock=1;
static uint64_t testClock(int clock){return fakeClock;}
static const char*testProgram(void){return "WindowServer";}
#define clock_gettime_nsec_np testClock
#define getprogname testProgram
static int nvmtl_surface_reuse_mode(void){return 2;}
static uint64_t IOSurfaceGetAllocSize(void *s){return 0;}
@interface NVMTLTexture:NSObject { @public BOOL _vramOn;void *_surf;struct{uint64_t size;} _vramBuf; }
@end
@implementation NVMTLTexture
@end
'''
post=r'''
static void put(id device,unsigned key,uint64_t span,__weak NVMTLTexture **out){@autoreleasepool{
 NVMTLTexture *t=[NVMTLTexture new];t->_vramOn=YES;t->_surf=(void*)1;t->_vramBuf.size=span;
 if(out)*out=t;g6mf_surface_hold(device,@[@(key)],t);
}}
int main(){@autoreleasepool{
 assert(g6mf_cache_parse_mb("128")==128 && g6mf_cache_parse_mb("128\n")==128);
 for(const char*s:(const char*[]){"", "64", "256", "128x", "128\nextra", "-1"})assert(g6mf_cache_parse_mb(s)==64);
 NSObject *d=[NSObject new];__weak NVMTLTexture *weak[20]={nil};uint64_t n,b;
 setenv("NVMTL_SURFACE_CACHE_MB","64",1);
 for(unsigned i=0;i<8;i++)put(d,i,1024*1024,&weak[i]);
 @autoreleasepool{NVMTLTexture *first=weak[0];assert(first);g6mf_surface_hold(d,@[@0],first);}
 put(d,8,1024*1024,&weak[8]);assert(weak[0]&&!weak[1]&&weak[8]);
 g6mf_surface_cache_usage(d,&n,&b);assert(n==8&&b==8*1024*1024);
 setenv("NVMTL_SURFACE_CACHE_MB","128",1);
 for(unsigned i=9;i<18;i++)put(d,i,1024*1024,&weak[i]);
 g6mf_surface_cache_usage(d,&n,&b);assert(n==16&&b==16*1024*1024);
 setenv("NVMTL_SURFACE_CACHE_MB","64",1);
 put(d,19,1024*1024,&weak[19]);g6mf_surface_cache_usage(d,&n,&b);assert(n==8&&b==8*1024*1024);
 g6mf_surface_cache_flush(d);assert(!weak[19]);
 setenv("NVMTL_SURFACE_CACHE_MB","128",1);
 for(unsigned i=0;i<12;i++)put(d,i,9*1024*1024,&weak[i]);
 g6mf_surface_cache_usage(d,&n,&b);assert(n==12&&b==108*1024*1024);
 NVMTLTexture *caller=weak[0];assert(caller);
 setenv("NVMTL_SURFACE_CACHE_MB","64",1);
 // An oversized request must still trim existing 128 MiB policy ownership.
 put(d,99,129*1024*1024,nullptr);g6mf_surface_cache_usage(d,&n,&b);assert(n==7&&b==63*1024*1024);
 assert(caller&&!weak[1]);g6mf_surface_cache_flush(d);assert(caller);caller=nil;assert(!weak[0]);
 uint64_t c[8];g6mf_surface_cache_stats(c,8);assert(c[0]>0&&c[2]>0&&c[3]>0&&c[6]==1);
 unsetenv("NVMTL_SURFACE_CACHE_MB");
 FILE *file=fopen("POLICY_FILE","w");assert(file);fputs("128\n",file);fclose(file);
 uint64_t mb,entries;g6mf_surface_cache_policy(&mb,&entries);assert(mb==128&&entries==16);
 file=fopen("POLICY_FILE","w");fputs("64\n",file);fclose(file);
 g6mf_surface_cache_policy(&mb,&entries);assert(mb==128); // Poll limit prevents per-import file I/O.
 fakeClock+=1000000000ull;g6mf_surface_cache_policy(&mb,&entries);assert(mb==64&&entries==8);
 file=fopen("POLICY_FILE","wb");const char invalid[]={49,50,56,0,120};fwrite(invalid,1,sizeof invalid,file);fclose(file);
 fakeClock+=1000000000ull;g6mf_surface_cache_policy(&mb,&entries);assert(mb==64);
 remove("POLICY_FILE");fakeClock+=1000000000ull;g6mf_surface_cache_policy(&mb,&entries);assert(mb==64);
 puts("PASS: production LRU 8/64 ->16/128 ->8/64, touch, count/byte pressure, oversized shrink, caller lifetime, flush and strict policy parsing");
}}
'''
with tempfile.TemporaryDirectory()as tmp:
 p=Path(tmp);text=(pre+block+post).replace('/Library/NullMoth/g6mf-surface-cache-mb',str(p/'policy')).replace('POLICY_FILE',str(p/'policy'))
 (p/'test.mm').write_text(text)
 subprocess.run(['xcrun','clang++','-std=c++17','-fobjc-arc','-O1','-fsanitize=address,undefined','-I'+str(root/'plugin'),str(p/'test.mm'),'-o',str(p/'test'),'-framework','Foundation'],check=True)
 subprocess.run([str(p/'test')],check=True)
