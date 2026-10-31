#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#include <assert.h>
@interface NSObject(HoldProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
static id parent(id t) { return object_getIvar(t,class_getInstanceVariable([t class],"_parent")); }
static id make(id<MTLDevice> d, unsigned w, unsigned h) {
    IOSurfaceRef s=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@(w),(id)kIOSurfaceHeight:@(h),(id)kIOSurfaceBytesPerElement:@4,(id)kIOSurfaceBytesPerRow:@(w*4),(id)kIOSurfacePixelFormat:@(0x42475241)});assert(s);
    MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:w height:h mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
    id t=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(t);CFRelease(s);return t;
}
int main(int argc,char **argv) { @autoreleasepool {
    assert(argc==2);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);
    setenv("NVMTL_LIVE_SURFACE_REUSE","2",1);
    void (*usage)(id,uint64_t*,uint64_t*)=dlsym(module,"g6mf_surface_cache_usage");
    void (*flush)(id)=dlsym(module,"g6mf_surface_cache_flush");assert(usage && flush);
    io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));
    id<MTLDevice> d=[[NSClassFromString(@"NVMTLDevice") alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
    __weak id first=nil, second=nil, last=nil;
    @autoreleasepool { first=make(d,64,32); } assert(first);
    // Fill eight entries, touch the first, then force eviction of the second.
    for(unsigned i=0;i<7;i++){@autoreleasepool{id t=make(d,64,32);if(!i)second=t;}}
    @autoreleasepool {
        id<MTLTexture> root=first;IOSurfaceRef s=root.iosurface;
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:64 height:32 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
        id alias=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(parent(alias)==root);
    }
    @autoreleasepool { last=make(d,64,32); }
    assert(first && !second && last);
    uint64_t count=0,bytes=0;usage(d,&count,&bytes);assert(count==8 && bytes<=64ull*1024*1024);
    flush(d);assert(!first && !last);usage(d,&count,&bytes);assert(!count && !bytes);
    // Full-size buffers exceed the byte budget before the entry limit.
    for(unsigned i=0;i<12;i++){@autoreleasepool{id t=make(d,1920,1200);if(!i)first=t;last=t;}}
    usage(d,&count,&bytes);assert(count>0 && count<8 && bytes<=64ull*1024*1024 && !first && last);
    printf("HOLD BUDGET PASS: entries=%llu bytes=%llu; entry limit, LRU touch and byte eviction verified\n",count,bytes);
    // Eviction must release cache ownership without killing a caller's view.
    @autoreleasepool {
        id<MTLTexture> root=last;IOSurfaceRef s=root.iosurface;
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:1920 height:1200 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
        id alias=[d newTextureWithDescriptor:td iosurface:s plane:0];assert(parent(alias)==root);
        root=nil;flush(d);assert(last && parent(alias)==last);
    }
    assert(!last);usage(d,&count,&bytes);assert(!count && !bytes);
    // Encode a read, remove every caller/cache reference, then submit it.
    // Command-buffer ownership must keep the import alive through execution.
    @autoreleasepool {
        id<MTLTexture> src=make(d,64,32);IOSurfaceRef s=src.iosurface;
        assert(IOSurfaceLock(s,0,NULL)==0);uint32_t *pixels=IOSurfaceGetBaseAddress(s);
        for(unsigned i=0;i<2048;i++)pixels[i]=0xff123456u^i;
        IOSurfaceUnlock(s,0,NULL);
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:64 height:32 mipmapped:NO];td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
        id<MTLTexture> dst=[d newTextureWithDescriptor:td];assert(dst);
        id<MTLCommandQueue> q=[d newCommandQueue];id<MTLCommandBuffer> cb=[q commandBuffer];id<MTLBlitCommandEncoder> be=[cb blitCommandEncoder];
        [be copyFromTexture:src sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(64,32,1) toTexture:dst destinationSlice:0 destinationLevel:0 destinationOrigin:MTLOriginMake(0,0,0)];
        [be endEncoding];src=nil;flush(d);[cb commit];[cb waitUntilCompleted];assert(cb.status!=MTLCommandBufferStatusError);
        uint32_t read[2048];[dst getBytes:read bytesPerRow:256 fromRegion:MTLRegionMake2D(0,0,64,32) mipmapLevel:0];
        for(unsigned i=0;i<2048;i++)assert(read[i]==(0xff123456u^i));
    }
    puts("HOLD IN-FLIGHT PASS: cache/caller released before submit; GPU readback remains exact");
    puts("HOLD LIFETIME PASS: retained import survives transient wrappers; flush releases it after final alias");
    return 0;
} }
