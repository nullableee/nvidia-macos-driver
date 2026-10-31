#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOKit/IOKitLib.h>
#include <assert.h>
#include <dlfcn.h>
@interface NSObject(PrivateSafetyInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
static id<MTLCommandBuffer> clear(id<MTLCommandQueue> q, id<MTLTexture> t, unsigned level, BOOL red) {
    MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
    rp.colorAttachments[0].texture = t; rp.colorAttachments[0].level = level;
    rp.colorAttachments[0].loadAction = MTLLoadActionClear; rp.colorAttachments[0].storeAction = MTLStoreActionStore;
    rp.colorAttachments[0].clearColor = MTLClearColorMake(red, !red, 0, 1);
    id<MTLCommandBuffer> cb = [q commandBuffer];
    id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp]; assert(e); [e endEncoding];
    return cb;
}
static void finish(id<MTLCommandBuffer> cb) {
    [cb commit]; [cb waitUntilCompleted]; assert(cb.status == MTLCommandBufferStatusCompleted);
}
static void pixels(id<MTLTexture> t, unsigned level, BOOL red) {
    NSUInteger w = MAX(1, t.width >> level), h = MAX(1, t.height >> level);
    BOOL half = t.pixelFormat == MTLPixelFormatRGBA16Float;
    unsigned bpp = half ? 8 : 4; void *p = malloc(w * h * bpp); assert(p);
    [t getBytes:p bytesPerRow:w * bpp fromRegion:MTLRegionMake2D(0, 0, w, h) mipmapLevel:level];
    for (NSUInteger k = 0; k < w * h; k++) {
        if (half) assert(((uint64_t *)p)[k] == ((0x3c00ull << 48) | (red ? 0x3c00ull : 0x3c00ull << 16)));
        else assert(((uint32_t *)p)[k] == (red ? 0xffff0000u : 0xff00ff00u));
    }
    free(p);
}
int main(int argc, char **argv) { @autoreleasepool {
    assert(argc == 2); void *module = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL); assert(module);
    setenv("NVMTL_PRIVATE_IMAGE_CACHE", "1", 1);
    void (*flush)(void) = dlsym(module, "g6mf_private_image_flush");
    void (*stats)(uint64_t[6]) = dlsym(module, "g6mf_private_image_stats"); assert(flush && stats);
    io_service_t port = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("NVAccel")); assert(port);
    id<MTLDevice> d = [[NSClassFromString(@"NVMTLDevice") alloc] initWithAcceleratorPort:port]; IOObjectRelease(port); assert(d);
    id<MTLCommandQueue> q = [d newCommandQueue]; assert(q);
    MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:128 height:64 mipmapped:YES];
    td.mipmapLevelCount = 4; td.storageMode = MTLStorageModePrivate;
    td.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView;
    for (unsigned k = 0; k < 100; k++) { @autoreleasepool {
        id<MTLTexture> root = [d newTextureWithDescriptor:td]; assert(root);
        id<MTLTexture> alias = [root newTextureViewWithPixelFormat:td.pixelFormat]; assert(alias);
        for (unsigned level = 0; level < 4; level++) finish(clear(q, root, level, (k + level) & 1));
        root = nil; flush(); // aliases must keep the original root out of the free pool
        id<MTLTexture> other = [d newTextureWithDescriptor:td]; assert(other);
        finish(clear(q, other, 0, !(k & 1)));
        for (unsigned level = 0; level < 4; level++) pixels(alias, level, (k + level) & 1);
    }}
    flush();
    for (unsigned k = 0; k < 100; k++) { @autoreleasepool {
        id<MTLTexture> t = [d newTextureWithDescriptor:td]; assert(t);
        id<MTLCommandBuffer> cb = clear(q, t, 0, k & 1);
        __weak id weak = t; t = nil; assert(weak);
        flush(); // command ownership must survive even before submission
        id<MTLTexture> other = [d newTextureWithDescriptor:td]; assert(other);
        finish(clear(q, other, 0, !(k & 1)));
        t = weak; assert(t); // completion is allowed to release the CB's resource set
        finish(cb); pixels(t, 0, k & 1);
    }}
    flush();
    for (unsigned k = 0; k < 200; k++) { @autoreleasepool {
        id<MTLTexture> t = [d newTextureWithDescriptor:td]; assert(t);
        for (unsigned level = 0; level < 4; level++) {
            BOOL red = (k + level) & 1; finish(clear(q, t, level, red)); pixels(t, level, red);
        }
    }}
    uint64_t c[6]; stats(c); assert(c[0] >= 199 && c[4] <= 16 && c[5] <= (64ull << 20));
    printf("GPU PASS: all pixels, 4 mip levels, 100 alias lifetimes, 100 pre-submit releases, 200 reuse cycles; hits=%llu misses=%llu held=%llu bytes=%llu\n", c[0], c[1], c[4], c[5]);
    flush(); stats(c); assert(!c[4] && !c[5]);
    for (unsigned half = 0; half < 2; half++) {
        td.width = 1920; td.height = 1200; td.mipmapLevelCount = 1;
        td.pixelFormat = half ? MTLPixelFormatRGBA16Float : MTLPixelFormatBGRA8Unorm;
        for (unsigned k = 0; k < 20; k++) { @autoreleasepool {
            id<MTLTexture> t = [d newTextureWithDescriptor:td]; assert(t);
            finish(clear(q, t, 0, k & 1)); pixels(t, 0, k & 1);
        }}
    }
    stats(c); assert(c[4] <= 16 && c[5] <= (64ull << 20)); flush();
    puts("FULL FRAME PASS: every pixel of 40 recycled 1920x1200 BGRA8/RGBA16F frames.");
}}
