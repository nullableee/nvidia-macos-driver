#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#include <math.h>
@interface NSObject(ProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char**argv){@autoreleasepool{
 if(argc!=2||!dlopen(argv[1],RTLD_NOW|RTLD_LOCAL))return 1;
 setenv("NVMTL_LIVE_SURFACE_REUSE",getenv("G6MF_TEST_REUSE")?:"1",1);
 if(getenv("G6MF_TEST_METADATA"))setenv("NVMTL_METADATA_REUSE",getenv("G6MF_TEST_METADATA"),1);
 io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));id<MTLDevice>d=[[NSClassFromString(@"NVMTLDevice")alloc]initWithAcceleratorPort:port];IOObjectRelease(port);if(!d)return 2;
 IOSurfaceRef s=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@64,(id)kIOSurfaceHeight:@32,(id)kIOSurfaceBytesPerElement:@4,(id)kIOSurfaceBytesPerRow:@256,(id)kIOSurfacePixelFormat:@(0x42475241)});
 if(!s||IOSurfaceLock(s,0,NULL))return 3;uint32_t*p=IOSurfaceGetBaseAddress(s);for(int i=0;i<2048;i++)p[i]=0xff1e140a;IOSurfaceUnlock(s,0,NULL);
 MTLTextureDescriptor*td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:64 height:32 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
 id root=[d newTextureWithDescriptor:td iosurface:s plane:0];if(!root)return 4;
 td.swizzle=(MTLTextureSwizzleChannels){MTLTextureSwizzleBlue,MTLTextureSwizzleGreen,MTLTextureSwizzleRed,MTLTextureSwizzleAlpha};
 id<MTLTexture>alias=[d newTextureWithDescriptor:td iosurface:s plane:0];if(!alias)return 5;
 Ivar pi=class_getInstanceVariable([alias class],"_parent");if(!pi||object_getIvar(alias,pi)!=root)return 6;
 NSError*err=nil;
 id<MTLLibrary>lib=[d newLibraryWithSource:@"#include <metal_stdlib>\nusing namespace metal;kernel void swz(texture2d<float,access::read> src[[texture(0)]],device float4*out[[buffer(0)]],uint2 p[[thread_position_in_grid]]){out[p.y*64+p.x]=src.read(p);}" options:nil error:&err];
 id<MTLComputePipelineState>ps=lib?[d newComputePipelineStateWithFunction:[lib newFunctionWithName:@"swz"] error:&err]:nil;
 if(!ps){fprintf(stderr,"shader: %s\n",err.description.UTF8String);return 7;}
 id<MTLBuffer>out=[d newBufferWithLength:2048*16 options:MTLResourceStorageModeShared];id<MTLCommandQueue>q=[d newCommandQueue];id<MTLCommandBuffer>cb=[q commandBuffer];id<MTLComputeCommandEncoder>enc=[cb computeCommandEncoder];
 [enc setComputePipelineState:ps];[enc setTexture:alias atIndex:0];[enc setBuffer:out offset:0 atIndex:0];[enc dispatchThreads:MTLSizeMake(64,32,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];[enc endEncoding];[cb commit];[cb waitUntilCompleted];if(cb.status==MTLCommandBufferStatusError)return 8;
 float*v=out.contents;float want[4]={10.f/255,20.f/255,30.f/255,1};for(int i=0;i<8192;i++)if(fabsf(v[i]-want[i%4])>0.0001f){fprintf(stderr,"SWIZZLE FAIL %d %f vs %f\n",i,v[i],want[i%4]);return 9;}
 CFRelease(s);puts("SWIZZLE PASS: reused VRAM alias shader-read channel mapping, 2048 pixels");return 0;
}}
