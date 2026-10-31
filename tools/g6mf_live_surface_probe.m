#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurface.h>
#import <IOKit/IOKitLib.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#import <mach/mach_time.h>
@interface NSObject(ProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
static double elapsed(uint64_t t){mach_timebase_info_data_t b;mach_timebase_info(&b);return (mach_absolute_time()-t)*(double)b.numer/b.denom/1e6;}
int main(int argc,char**argv){@autoreleasepool{
 if(argc!=2)return 1;setenv("NVMTL_ENABLE","1",1);
 if(!dlopen(argv[1],RTLD_NOW|RTLD_LOCAL)){fprintf(stderr,"%s\n",dlerror());return 2;}
 setenv("NVMTL_LIVE_SURFACE_REUSE",getenv("G6MF_TEST_REUSE")?:"0",1);
 Class cls=NSClassFromString(@"NVMTLDevice");Dl_info info={0};dladdr((__bridge void*)cls,&info);printf("class binary=%s\n",info.dli_fname?:"?");
 io_service_t accel=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));
 id<MTLDevice>d=[[cls alloc]initWithAcceleratorPort:accel];IOObjectRelease(accel);if(!d)return 3;
 id<MTLCommandQueue>q=[d newCommandQueue];
 for(int cycle=0;cycle<(getenv("G6MF_FULL")?3:8);cycle++){@autoreleasepool{
 unsigned w=getenv("G6MF_FULL")?1920:64+cycle*16,h=getenv("G6MF_FULL")?1200:32,row=w*(getenv("G6MF_HALF")?8:4);
 IOSurfaceRef surf=IOSurfaceCreate((__bridge CFDictionaryRef)@{(id)kIOSurfaceWidth:@(w),(id)kIOSurfaceHeight:@(h),(id)kIOSurfaceBytesPerElement:@(getenv("G6MF_HALF")?8:4),(id)kIOSurfaceBytesPerRow:@(row),(id)kIOSurfacePixelFormat:@(getenv("G6MF_HALF")?0x52476841:0x42475241)});
 if(!surf)return 4;
 MTLTextureDescriptor*td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:(getenv("G6MF_HALF")?MTLPixelFormatRGBA16Float:MTLPixelFormatBGRA8Unorm) width:w height:h mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead|MTLTextureUsageRenderTarget;
 id<MTLTexture>anchor=[d newTextureWithDescriptor:td iosurface:surf plane:0];if(!anchor)return 5;
 Ivar vi=class_getInstanceVariable([anchor class],"_vramOn");
 printf("cycle%d anchor_vram=%d\n",cycle,vi?*(BOOL*)((char*)(__bridge void*)anchor+ivar_getOffset(vi)):-1);
 __weak id weakAnchor=anchor;
 if(getenv("G6MF_DROP_ANCHOR"))anchor=nil;
 id<MTLTexture>dst=[d newTextureWithDescriptor:td];if(!dst)return 6;
 uint32_t*read=malloc(row*h);uint64_t start=mach_absolute_time();
 for(unsigned frame=0;frame<20;frame++){@autoreleasepool{
  if(IOSurfaceLock(surf,0,NULL))return 7;uint32_t*p=IOSurfaceGetBaseAddress(surf);
  for(unsigned i=0;i<row*h/4;i++)p[i]=0xff000000u ^ (i*1237u) ^ (frame*977u);
  IOSurfaceUnlock(surf,0,NULL);
  id<MTLTexture>t=[d newTextureWithDescriptor:td iosurface:surf plane:0];if(!t)return 8;
  if(getenv("G6MF_DROP_ANCHOR")){Ivar pi=class_getInstanceVariable([t class],"_parent");if(!weakAnchor||object_getIvar(t,pi)!=weakAnchor)return 12;}
  if(frame==0){ Ivar pi=class_getInstanceVariable([t class],"_parent"); id parent=pi?object_getIvar(t,pi):nil;printf("alias_parent_is_anchor=%d\n",parent==(anchor?:weakAnchor)); }
  id<MTLCommandBuffer>cb=[q commandBuffer];id<MTLBlitCommandEncoder>b=[cb blitCommandEncoder];
  [b copyFromTexture:t sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(w,h,1) toTexture:dst destinationSlice:0 destinationLevel:0 destinationOrigin:MTLOriginMake(0,0,0)];[b endEncoding];[cb commit];[cb waitUntilCompleted];
  if(cb.status==MTLCommandBufferStatusError){fprintf(stderr,"GPU error %s\n",cb.error.description.UTF8String);return 9;}
  if(frame & 1) {
   for(unsigned i=0;i<row*h/4;i++)read[i]=0xff000000u^(i*1237u)^(frame*977u)^0x00550000u;
   [dst replaceRegion:MTLRegionMake2D(0,0,w,h) mipmapLevel:0 withBytes:read bytesPerRow:row];
   id<MTLCommandBuffer>back=[q commandBuffer];id<MTLBlitCommandEncoder>be=[back blitCommandEncoder];
   [be copyFromTexture:dst sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(w,h,1) toTexture:t destinationSlice:0 destinationLevel:0 destinationOrigin:MTLOriginMake(0,0,0)];
   [be endEncoding];[back commit];[back waitUntilCompleted];
   if(back.status==MTLCommandBufferStatusError)return 11;
   [(anchor?:weakAnchor) getBytes:read bytesPerRow:row fromRegion:MTLRegionMake2D(0,0,w,h) mipmapLevel:0];
  } else {
  [dst getBytes:read bytesPerRow:row fromRegion:MTLRegionMake2D(0,0,w,h) mipmapLevel:0];
  }
  for(unsigned i=0;i<row*h/4;i++)if(read[i]!=(0xff000000u^(i*1237u)^(frame*977u)^((frame&1)?0x00550000u:0))){fprintf(stderr,"PIXEL FAIL cycle%d frame%u index%u got%x\n",cycle,frame,i,read[i]);return 10;}
 }}
 printf("cycle%d pixels PASS ms=%.3f anchor=%p\n",cycle,elapsed(start),(__bridge void*)anchor);fflush(stdout);free(read);CFRelease(surf);
 }}return 0;
}}
