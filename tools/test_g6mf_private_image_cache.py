"""Run the actual experimental image pool against synthetic GPU lifetimes."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = r'''
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#include <time.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
typedef struct { void *img, *view, *mem; uint64_t alloc; unsigned placed, sysmem, up_token; } nvk_image;
static unsigned destroyed, waited;
static void nvmtl_vk_image_destroy(nvk_image *i) { assert(i->img); __atomic_fetch_add(&destroyed,1,__ATOMIC_RELAXED); *i=(nvk_image){0}; }
static void nvmtl_vk_image_upload_barrier(nvk_image *i) { __atomic_fetch_add(&waited,1,__ATOMIC_RELAXED); i->up_token=0; }
static uint64_t fakeClock=1;
static unsigned fakeUid;
static const char *testProgram(void) {return "WindowServer";}
static uint64_t testClock(unsigned x) {return fakeClock;}
static int testStat(int fd,struct stat *st) {int rc=fstat(fd,st);if(!rc)st->st_uid=fakeUid;return rc;}
#define getprogname testProgram
#define clock_gettime_nsec_np testClock
#define fstat testStat
#include "g6mf_private_image_cache.h"
static nvk_image image(uint64_t n) {return (nvk_image){(void*)1,(void*)2,(void*)3,n,0,0,7};}
static void *worker(void *arg) {
 uint64_t key[12]={0}; key[0]=(uintptr_t)arg;
 for(unsigned k=0;k<5000;k++) {nvk_image i={0};key[1]=k%3;
  if(!g6mf_private_image_take(key,&i))i=image(1<<20);
  assert(g6mf_private_image_put(key,&i));assert(!i.img);
 }
 return NULL;
}
int main(void) {
 uint64_t key[12]={1},other[12]={1},c[6];nvk_image i=image(1<<20),out={0};
 setenv("NVMTL_PRIVATE_IMAGE_CACHE","0",1);assert(!g6mf_private_image_put(key,&i)&&i.img);
 setenv("NVMTL_PRIVATE_IMAGE_CACHE","1",1);assert(g6mf_private_image_put(key,&i)&&!i.img);
 other[11]=1;assert(!g6mf_private_image_take(other,&out));assert(g6mf_private_image_take(key,&out));assert(!out.up_token);
 assert(!g6mf_private_image_take(key,&i));nvmtl_vk_image_destroy(&out);
 i=image(1<<20);i.placed=1;assert(!g6mf_private_image_put(key,&i));i.placed=0;i.sysmem=1;assert(!g6mf_private_image_put(key,&i));
 i=image(33ull<<20);assert(!g6mf_private_image_put(key,&i));
 for(unsigned k=0;k<20;k++){i=image(1<<20);key[0]=k;assert(g6mf_private_image_put(key,&i));}
 g6mf_private_image_stats(c);assert(c[4]==16&&c[5]==16ull<<20&&c[3]==4);
 key[0]=0;assert(!g6mf_private_image_take(key,&i)); // oldest key was evicted
 g6mf_private_image_flush();g6mf_private_image_stats(c);assert(!c[4]&&!c[5]);
 for(unsigned k=0;k<3;k++){i=image(32ull<<20);assert(g6mf_private_image_put(key,&i));}
 g6mf_private_image_stats(c);assert(c[4]==2&&c[5]==64ull<<20);
 g6mf_private_image_flush();
 pthread_t threads[4];for(uintptr_t k=0;k<4;k++)assert(!pthread_create(&threads[k],NULL,worker,(void*)(k+100)));
 for(unsigned k=0;k<4;k++)assert(!pthread_join(threads[k],NULL));
 g6mf_private_image_flush();g6mf_private_image_stats(c);assert(!c[4]&&!c[5]);
 assert(waited==20024);puts("PASS: exact keys, disabled mode, uploads, placement/system/oversize rejection, count/byte bounds, eviction, flush, 20000 concurrent lifetimes");
 unsetenv("NVMTL_PRIVATE_IMAGE_CACHE");
 FILE *f=fopen(G6MF_PRIVATE_IMAGE_POLICY,"wb");assert(f);fwrite("1\n",1,2,f);fclose(f);chmod(G6MF_PRIVATE_IMAGE_POLICY,0644);
 assert(g6mf_private_image_enabled());
 f=fopen(G6MF_PRIVATE_IMAGE_POLICY,"wb");assert(f);fwrite("1\0x",1,3,f);fclose(f);
 assert(g6mf_private_image_enabled()); // policy is polled at most once per second
 fakeClock+=1000000000ull;assert(!g6mf_private_image_enabled());
 f=fopen(G6MF_PRIVATE_IMAGE_POLICY,"wb");assert(f);fputs("1\n",f);fclose(f);chmod(G6MF_PRIVATE_IMAGE_POLICY,0666);
 fakeClock+=1000000000ull;assert(!g6mf_private_image_enabled());
 chmod(G6MF_PRIVATE_IMAGE_POLICY,0644);fakeUid=501;
 fakeClock+=1000000000ull;assert(!g6mf_private_image_enabled());
 fakeUid=0;fakeClock+=1000000000ull;assert(g6mf_private_image_enabled());
 remove(G6MF_PRIVATE_IMAGE_POLICY);assert(!symlink("/dev/null",G6MF_PRIVATE_IMAGE_POLICY));
 fakeClock+=1000000000ull;assert(!g6mf_private_image_enabled());remove(G6MF_PRIVATE_IMAGE_POLICY);
 fakeClock+=1000000000ull;assert(!g6mf_private_image_enabled());
 puts("PASS: actual policy reader, polling, strict bytes, owner/mode rejection, symlink/missing fail closed (uid/clock mocked)");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp)
    (p / 'test.c').write_text(source)
    subprocess.run(['xcrun', 'clang', '-O1', '-g', '-fsanitize=address,undefined',
                    '-I' + str(root / 'plugin'), '-DG6MF_PRIVATE_IMAGE_POLICY="'+str(p / 'policy')+'"',
                    str(p / 'test.c'), '-o', str(p / 'test')], check=True)
    subprocess.run([str(p / 'test')], check=True)
