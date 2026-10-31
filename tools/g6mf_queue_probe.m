#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOKit/IOKitLib.h>
#import <dlfcn.h>
#include <assert.h>
@interface NSObject(QueueProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char **argv){@autoreleasepool{
 assert(argc==2);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);setenv("G6MF_TEST_QUEUE_STATS","1",1);
 void (*stats)(uint64_t*)=dlsym(module,"g6mf_queue_stats");assert(stats);
 io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));id<MTLDevice>d=[[NSClassFromString(@"NVMTLDevice")alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
 uint32_t input[64];for(unsigned i=0;i<64;i++)input[i]=0x12340000u+i;
 id<MTLBuffer> src=[d newBufferWithBytes:input length:sizeof input options:MTLResourceStorageModeShared],dst=[d newBufferWithLength:sizeof input options:MTLResourceStorageModeShared];assert(src&&dst);
 id<MTLCommandQueue> q=[d newCommandQueue];NSMutableArray *buffers=[NSMutableArray new];uint64_t before[9],after[9];stats(before);
 for(unsigned i=0;i<64;i++){id<MTLCommandBuffer>cb=[q commandBuffer];id<MTLBlitCommandEncoder>b=[cb blitCommandEncoder];[b copyFromBuffer:src sourceOffset:i*4 toBuffer:dst destinationOffset:i*4 size:4];[b endEncoding];[cb commit];[buffers addObject:cb];}
 for(id<MTLCommandBuffer>cb in buffers){[cb waitUntilCompleted];assert(cb.status==MTLCommandBufferStatusCompleted);}
 uint32_t *read=dst.contents;for(unsigned i=0;i<64;i++)assert(read[i]==input[i]);
 stats(after);assert(after[0]-before[0]==64&&after[3]-before[3]==64&&after[6]-before[6]==64);
 printf("QUEUE PASS:64 ordered copies,64 schedules,64 completions; pending_max=%llu mean_commit_complete_ms=%.4f\n",after[8],(after[4]-before[4])/64e6);return 0;
}}
