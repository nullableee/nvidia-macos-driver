// Isolated allocation benchmark; never loads a replacement into WindowServer.
// Fresh vs caller-retained private textures is an upper-bound experiment, not FPS.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOKit/IOKitLib.h>
#include <dlfcn.h>
#include <assert.h>
#include <time.h>
@interface NSObject(PrivateProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
static uint64_t now(void) {
    struct timespec t; assert(!clock_gettime(CLOCK_UPTIME_RAW, &t));
    return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}
int main(int argc, char **argv) { @autoreleasepool {
    assert(argc == 2 || argc == 3);
    void *module = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!module) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    setenv("NVMTL_PRIVATE_IMAGE_CACHE", argc == 3 ? argv[2] : "0", 1);
    void (*stats)(uint64_t[6]) = dlsym(module, "g6mf_private_image_stats");
    void (*flush)(void) = dlsym(module, "g6mf_private_image_flush");
    io_service_t port = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("NVAccel"));
    assert(port);
    id<MTLDevice> d = [[NSClassFromString(@"NVMTLDevice") alloc] initWithAcceleratorPort:port];
    IOObjectRelease(port); assert(d);
    id<MTLCommandQueue> q = [d newCommandQueue]; assert(q);
    const unsigned count = 120;
    const NSUInteger sizes[][2] = {{512, 256}, {960, 600}, {1920, 1200}};
    for (unsigned shape = 0; shape < 3; shape++) {
        for (unsigned half = 0; half < 2; half++) { @autoreleasepool {
            MTLPixelFormat fmt = half ? MTLPixelFormatRGBA16Float : MTLPixelFormatBGRA8Unorm;
            MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:fmt
                width:sizes[shape][0] height:sizes[shape][1] mipmapped:NO];
            td.storageMode = MTLStorageModePrivate;
            td.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
            // Warm allocator, render pass and queue before timed populations.
            for (unsigned phase = 0; phase < 5; phase++) { @autoreleasepool {
                unsigned iterations = phase == 0 ? 8 : count;
                BOOL reuse = phase == 2 || phase == 3;
                id<MTLTexture> retained = reuse ? [d newTextureWithDescriptor:td] : nil;
                uint64_t make = 0, encode = 0, submit = 0, drop = 0;
                uint64_t phaseStart = now();
                for (unsigned i = 0; i < iterations; i++) { @autoreleasepool {
                    uint64_t t = now();
                    id<MTLTexture> tex = retained ?: [d newTextureWithDescriptor:td]; assert(tex);
                    make += now() - t; t = now();
                    MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
                    rp.colorAttachments[0].texture = tex;
                    rp.colorAttachments[0].loadAction = MTLLoadActionClear;
                    rp.colorAttachments[0].storeAction = MTLStoreActionStore;
                    rp.colorAttachments[0].clearColor = MTLClearColorMake((i & 1) ? 1 : 0, 0, 0, 1);
                    id<MTLCommandBuffer> cb = [q commandBuffer];
                    id<MTLRenderCommandEncoder> enc = [cb renderCommandEncoderWithDescriptor:rp]; assert(enc);
                    [enc endEncoding]; encode += now() - t; t = now();
                    [cb commit]; [cb waitUntilCompleted];
                    assert(cb.status == MTLCommandBufferStatusCompleted);
                    submit += now() - t; t = now();
                    enc = nil; cb = nil; rp = nil; tex = nil;
                    drop += now() - t;
                }}
                uint64_t elapsed = now() - phaseStart;
                if (phase) printf("%lux%lu %s phase=%u %s n=%u make_us=%.3f encode_us=%.3f submit_wait_us=%.3f drop_us=%.3f total_us=%.3f\n",
                    (unsigned long)td.width, (unsigned long)td.height, half ? "RGBA16F" : "BGRA8",
                    phase, reuse ? "retained" : "fresh", iterations,
                    make / (1000.0 * iterations), encode / (1000.0 * iterations),
                    submit / (1000.0 * iterations), drop / (1000.0 * iterations), elapsed / (1000.0 * iterations));
                fflush(stdout);
            }}
        }}
    }
    if (stats) {
        uint64_t c[6]; stats(c);
        printf("CACHE hits=%llu misses=%llu puts=%llu evictions=%llu held=%llu bytes=%llu\n",
            c[0], c[1], c[2], c[3], c[4], c[5]);
        assert(c[4] <= 16 && c[5] <= (64ull << 20));
        assert(flush); flush(); stats(c); assert(!c[4] && !c[5]);
    }
    puts("PASS: isolated allocation/clear/completion benchmark; timings are not desktop FPS.");
    return 0;
}}
