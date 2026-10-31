from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1]
def extract(path,name):
 s=(r/path).read_text();start=s.index(name);end=s.index('\n}\n',start)+3;return s[start:end]
a=extract('plugin/nvmtl_vk.c','static int nvmtl_address_snapshot(')
b=extract('plugin/NVMTLObjects.m','static void nvmtl_surface_remark_attempt(')+extract('plugin/NVMTLObjects.m','static void nvmtl_surface_remark_later(')
prefix=r'''
#import <Foundation/Foundation.h>
#include <assert.h>
#define NVMTL_NBUF 32
#define NVMTL_NTEX 128
#define NVMTL_TABLE_BYTES 1536
#define NVMTL_TABLES_PER_PAGE 8
#define NVMTL_SLOT_BUF 1
#define NVMTL_SLOT_TEX 2
typedef struct {void *map,*buf;uint64_t base;} nvk_buffer;
typedef struct nvmtl_address_page {nvk_buffer buffer;struct nvmtl_address_page *next;} nvmtl_address_page;
typedef struct {int kind;uint64_t address,off,size;void *h;} nvmtl_slot;
typedef struct {nvmtl_slot s[2][160];} nvmtl_bindtable;
typedef struct {unsigned address_count;nvmtl_address_page *address_pages;void *table;} nvk_cmdbuf;
typedef struct {void *buffer;size_t offset,range;} VkDescriptorBufferInfo;
static nvk_buffer g_dummyBuf={0,0,0x100};static unsigned dc,pc;
static uint64_t nvmtl_vk_buffer_address(nvk_buffer *b){if(b==&g_dummyBuf)dc++;else pc++;return b->base;}
static nvmtl_address_page *nvmtl_keep_page_pop(void){return NULL;}
static int nvmtl_vk_buffer_create(size_t n,int v,nvk_buffer*b){b->map=calloc(1,n);b->buf=b->map;b->base=0x10000;return !b->map;}
static void nvmtl_vk_buffer_destroy(nvk_buffer*b){free(b->map);}
#define nvlog(...) ((void)0)
typedef struct {unsigned id,seed,busy,calls,published;int failed;} Surface;
@interface NVMTLTexture:NSObject {@public Surface *_surf;unsigned _plane,_surfSeed,_surfGen;}
@end
@implementation NVMTLTexture
@end
static unsigned IOSurfaceGetSeed(Surface*s){return s->seed;}
static unsigned IOSurfaceGetID(Surface*s){return s->id;}
static Surface *surfaces[4];
static int nvmtl_vk_surface_dirty_try(unsigned id,unsigned plane){Surface*s=surfaces[id];s->calls++;if(s->failed)return -1;if(s->busy){s->busy--;return 1;}return 0;}
static id nvmtl_surface_sync(id r){return r;}
static unsigned nvmtl_vram_tag_bump(Surface*s,unsigned p,unsigned seed){return ++s->published;}
static NSMutableArray *tasks;static uint64_t ticks;
static uint64_t fake_time(uint64_t now,int64_t delta){return ticks+delta;}
static void fake_after(uint64_t due,dispatch_queue_t q,dispatch_block_t task){[tasks addObject:@[@(due),[task copy]]];}
static void fake_async(dispatch_queue_t q,dispatch_block_t task){fake_after(ticks,q,task);}
#define dispatch_time fake_time
#define dispatch_after fake_after
#define dispatch_async fake_async
static void step(void){NSUInteger best=0;for(NSUInteger i=1;i<tasks.count;i++)if([tasks[i][0] unsignedLongLongValue]<[tasks[best][0] unsignedLongLongValue])best=i;NSArray*t=tasks[best];[tasks removeObjectAtIndex:best];ticks=[t[0] unsignedLongLongValue];((dispatch_block_t)t[1])();}
static NVMTLTexture *root(Surface*s){surfaces[s->id]=s;NVMTLTexture*r=[NVMTLTexture new];r->_surf=s;r->_surfSeed=s->seed;return r;}
'''
main=r'''
int main(){@autoreleasepool{
 nvk_cmdbuf c={0};VkDescriptorBufferInfo out;
 for(unsigned run=0;run<3;run++){
  nvmtl_bindtable t={0};if(run==1)for(unsigned i=0;i<32;i++){t.s[1][i].kind=NVMTL_SLOT_BUF;t.s[1][i].address=0x1000+i;t.s[1][i].off=4;}
  if(run==2){t.s[1][3]=(nvmtl_slot){NVMTL_SLOT_BUF,0x9000,8,0,0};t.s[1][32+7]=(nvmtl_slot){NVMTL_SLOT_TEX,0,0,123,(void*)1};}
  c.table=run?&t:NULL;unsigned before=dc;
  for(unsigned j=0;j<20;j++){
   assert(!nvmtl_address_snapshot(&c,1,&out));uint64_t*p=(void*)((char*)c.address_pages->buffer.map+out.offset);
   for(unsigned i=0;i<32;i++){assert(p[i]==(run==1?0x1000+i+4:run==2&&i==3?0x9008:0x100));assert(p[32+i]==c.address_pages->buffer.base+out.offset+i*8);}
   for(unsigned i=0;i<128;i++)assert(p[64+i]==(run==2&&i==7?123:0));
  }
  assert(dc-before==(run==1?0:20));
 }
 while(c.address_pages){nvmtl_address_page*p=c.address_pages;c.address_pages=p->next;free(p->buffer.map);free(p);}assert(pc==60);
 puts("PASS production address snapshots: all192entries, page boundaries, null/mixed/full bindings; dummy queries32->1, fully bound0");
 tasks=[NSMutableArray new];Surface slow={1,1,49,0,0,0},fast={2,1,0,0,0,0};NVMTLTexture*r=root(&slow),*f=root(&fast);
 nvmtl_surface_remark_later(r,1);nvmtl_surface_remark_later(f,1);step();step();assert(fast.published==1&&ticks==0&&slow.published==0);
 while(tasks.count)step();assert(slow.calls==50&&slow.published==1&&ticks==98000000);
 slow=(Surface){1,1,100,0,0,0};r=root(&slow);nvmtl_surface_remark_later(r,1);while(tasks.count)step();assert(slow.calls==50&&!slow.published);
 slow=(Surface){1,1,4,0,0,0};r=root(&slow);nvmtl_surface_remark_later(r,1);step();slow.seed=2;while(tasks.count)step();assert(slow.calls==1&&!slow.published);
 slow=(Surface){1,1,0,0,0,1};r=root(&slow);nvmtl_surface_remark_later(r,1);while(tasks.count)step();assert(slow.calls==1&&!slow.published);
 puts("PASS production deferred marking: unrelated surface publishes before first retry,50attempt bound,2ms spacing,seed cancellation,negative failure");
}}
'''
p=r.parent/'builds/frame-path-audit';p.mkdir(parents=True,exist_ok=True);(p/'test.m').write_text(prefix+a+b+main)
subprocess.run(['xcrun','clang','-O1','-fobjc-arc','-fsanitize=address,undefined',str(p/'test.m'),'-framework','Foundation','-o',str(p/'test')],check=True)
subprocess.run([str(p/'test')],check=True)
