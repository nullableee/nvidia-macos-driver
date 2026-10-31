#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#include <assert.h>
@interface NSObject(ProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
static id parent(id t){Ivar i=class_getInstanceVariable([t class],"_parent");return i?object_getIvar(t,i):nil;}
int main(int argc,char**argv){@autoreleasepool{
 assert(argc==2);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);setenv("NVMTL_LIVE_SURFACE_REUSE",getenv("G6MF_TEST_REUSE")?:"1",1);
 void (*flush)(id)=dlsym(module,"g6mf_surface_cache_flush");assert(flush);
 void (*stats)(uint64_t *,size_t)=dlsym(module,"g6mf_surface_stats");assert(stats);
 const char *(*release)(void)=dlsym(module,"g6mf_graphics_release");assert(release && !strcmp(release(),"0.4.7"));
 io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));
 id<MTLDevice>d=[[NSClassFromString(@"NVMTLDevice") alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
 for(unsigned c=0;c<50;c++){
  __weak id weakRoot=nil;
  @autoreleasepool{
   IOSurfaceRef s=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@64,(id)kIOSurfaceHeight:@32,(id)kIOSurfaceBytesPerElement:@4,(id)kIOSurfaceBytesPerRow:@256,(id)kIOSurfacePixelFormat:@(0x42475241)});assert(s);
   MTLTextureDescriptor*td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:64 height:32 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
   id<MTLTexture>root=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(root);weakRoot=root;
   id<MTLTexture>alias=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(parent(alias)==root);
   root=nil;assert(weakRoot && parent(alias)==weakRoot);
   NSOperationQueue*q=[NSOperationQueue new];q.maxConcurrentOperationCount=4;
   for(unsigned t=0;t<4;t++)[q addOperationWithBlock:^{for(unsigned j=0;j<20;j++){@autoreleasepool{id tex=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(tex && parent(tex)==weakRoot);}}}];
   [q waitUntilAllOperationsAreFinished];
   // Different resource options must not alias the previous backing.
   MTLTextureDescriptor*other=[td copy];other.hazardTrackingMode=MTLHazardTrackingModeUntracked;
   id different=[d newTextureWithDescriptor:other iosurface:s plane:0];assert(different && parent(different)!=weakRoot);
   CFRelease(s);alias=nil;
  }
  if(!strcmp(getenv("NVMTL_LIVE_SURFACE_REUSE"),"2"))flush(d);
  assert(!weakRoot); // after cache ownership is removed, completed jobs do not pin roots
 }
 uint64_t c[9]={0};stats(c,9);
 assert(c[0]==4150 && c[2]==4050 && c[3]==100 && c[7]==100 && c[8]==0);
 printf("COUNTERS PASS: release=%s calls=%llu vram_hit=%llu no_backing=%llu created=%llu\n",release(),c[0],c[2],c[3],c[7]);
 puts("STRESS PASS: 50 surface lifetimes, 4000 concurrent wrappers, last-alias retention, final release and option-key separation");
 return 0;
}}
