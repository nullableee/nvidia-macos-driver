#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <dlfcn.h>
#include <assert.h>
@interface NSObject(ChurnProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char **argv) { @autoreleasepool {
    assert(argc==3);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);
    setenv("NVMTL_LIVE_SURFACE_REUSE",argv[2],1);
    void (*stats)(uint64_t*,size_t)=dlsym(module,"g6mf_surface_stats");assert(stats);
    io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));
    id<MTLDevice> d=[[NSClassFromString(@"NVMTLDevice") alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
    IOSurfaceRef s=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@1920,(id)kIOSurfaceHeight:@1200,(id)kIOSurfaceBytesPerElement:@4,(id)kIOSurfaceBytesPerRow:@7680,(id)kIOSurfacePixelFormat:@(0x42475241)});assert(s);
    MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:1920 height:1200 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
    uint64_t start=clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
    for(unsigned i=0;i<120;i++){@autoreleasepool{id t=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(t);}}
    uint64_t ns=clock_gettime_nsec_np(CLOCK_UPTIME_RAW)-start, c[10]={0};stats(c,10);
    assert(c[0]==120);
    if(!strcmp(argv[2],"1"))assert(c[7]==120 && c[2]==0 && c[9]==119);
    if(!strcmp(argv[2],"2"))assert(c[7]==1 && c[2]==119 && c[9]==0);
    printf("CHURN PASS: mode=%s calls=%llu created=%llu hit=%llu repeat_miss=%llu total_ms=%.3f\n",argv[2],c[0],c[7],c[2],c[9],ns/1e6);
    CFRelease(s);return 0;
} }
