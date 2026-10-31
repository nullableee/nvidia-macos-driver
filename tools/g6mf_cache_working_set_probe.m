#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <dlfcn.h>
#include <assert.h>
@interface NSObject(CacheProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char **argv){@autoreleasepool{
 assert(argc==3);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);
 setenv("NVMTL_LIVE_SURFACE_REUSE","2",1);setenv("NVMTL_SURFACE_CACHE_MB",argv[2],1);
 void (*stats)(uint64_t*,size_t)=dlsym(module,"g6mf_surface_stats");void(*usage)(id,uint64_t*,uint64_t*)=dlsym(module,"g6mf_surface_cache_usage");void(*flush)(id)=dlsym(module,"g6mf_surface_cache_flush");assert(stats&&usage&&flush);
 io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));id<MTLDevice>d=[[NSClassFromString(@"NVMTLDevice")alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
 IOSurfaceRef surfaces[12];for(unsigned i=0;i<12;i++){
  surfaces[i]=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@1920,(id)kIOSurfaceHeight:@1200,(id)kIOSurfaceBytesPerRow:@7680,(id)kIOSurfaceBytesPerElement:@4,(id)kIOSurfacePixelFormat:@(0x42475241)});assert(surfaces[i]);
  assert(!IOSurfaceLock(surfaces[i],0,NULL));uint32_t*p=IOSurfaceGetBaseAddress(surfaces[i]);for(unsigned j=0;j<1920*1200;j++)p[j]=0xff000000u|((j*1664525u+i*1013904223u)&0xffffffu);IOSurfaceUnlock(surfaces[i],0,NULL);
 }
 MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:1920 height:1200 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
 for(unsigned i=0;i<240;i++){@autoreleasepool{id t=[d newTextureWithDescriptor:td iosurface:surfaces[i%12] plane:0];assert(t);}}
 uint64_t c[10],n,b;stats(c,10);usage(d,&n,&b);
 if(!strcmp(argv[2],"64"))assert(c[7]==240&&c[2]==0&&n<=8&&b<=64ull*1024*1024);
 else assert(!strcmp(argv[2],"128")&&c[7]==12&&c[2]==228&&n==12&&b<=128ull*1024*1024);
 printf("WORKING SET PASS mb=%s calls=%llu created=%llu hits=%llu held=%llu bytes=%llu\n",argv[2],c[0],c[7],c[2],n,b);fflush(stdout);
 id<MTLTexture>dst=[d newTextureWithDescriptor:td];id<MTLCommandQueue>q=[d newCommandQueue];uint32_t*read=malloc(1920*1200*4);assert(dst&&q&&read);
 for(unsigned i=0;i<12;i++){@autoreleasepool{
  id<MTLTexture>src=[d newTextureWithDescriptor:td iosurface:surfaces[i] plane:0];assert(src);
  id<MTLCommandBuffer>cb=[q commandBuffer];id<MTLBlitCommandEncoder>enc=[cb blitCommandEncoder];[enc copyFromTexture:src sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(1920,1200,1) toTexture:dst destinationSlice:0 destinationLevel:0 destinationOrigin:MTLOriginMake(0,0,0)];[enc endEncoding];
  src=nil;setenv("NVMTL_SURFACE_CACHE_MB","64",1);flush(d); // CB ownership must survive policy shrink and cache release.
  [cb commit];[cb waitUntilCompleted];assert(cb.status!=MTLCommandBufferStatusError);
  [dst getBytes:read bytesPerRow:7680 fromRegion:MTLRegionMake2D(0,0,1920,1200) mipmapLevel:0];
  for(unsigned j=0;j<1920*1200;j++)assert(read[j]==(0xff000000u|((j*1664525u+i*1013904223u)&0xffffffu)));
 }}
 free(read);flush(d);for(unsigned i=0;i<12;i++)CFRelease(surfaces[i]);puts("WORKING SET GPU PASS: all pixels of12full surfaces, cache/policy release before submit");
}}
