#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOKit/IOKitLib.h>
#import <dlfcn.h>
#include <assert.h>
#include <time.h>
@interface NSObject(RenderProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char **argv){@autoreleasepool{
 assert(argc==3);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);
 setenv("G6MF_TEST_DIRTY_COPY",argv[2],1);setenv("NVMTL_METADATA_REUSE",argv[2],1);
 void (*stats)(uint64_t*)=dlsym(module,"g6mf_descriptor_stats");assert(stats);
 void (*auditStats)(uint64_t*,unsigned)=dlsym(module,"g6mf_descriptor_audit_stats");
 uint64_t auditBefore[13]={0}, auditAfter[13]={0};
 if (auditStats) auditStats(auditBefore,13);
 io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));id<MTLDevice>d=[[NSClassFromString(@"NVMTLDevice")alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
 BOOL churn=getenv("G6MF_SAMPLER_CHURN")!=NULL,mask=getenv("G6MF_MASK_CHURN")!=NULL;
 NSString *source=@"#include <metal_stdlib>\nusing namespace metal;\nvertex float4 v(uint i [[vertex_id]]){float2 p[3]={float2(-1,-1),float2(3,-1),float2(-1,3)};return float4(p[i],0,1);}\nfragment float f(texture2d<float> a [[texture(0)]],texture2d<float> b [[texture(1)]],sampler s [[sampler(0)]]){return a.sample(s,float2(0.5)).x+b.sample(s,float2(0.5)).x;}\nfragment float g(texture2d<float> a [[texture(0)]],texture2d<float> b [[texture(1)]],sampler s [[sampler(1)]]){return a.sample(s,float2(0.5)).x+b.sample(s,float2(0.5)).x;}";
 BOOL fetch=getenv("G6MF_FETCH_INPUT")!=NULL,live=getenv("G6MF_FETCH_LIVE")!=NULL;
 if(fetch){
  if(!live)setenv("NVMTL_NO_FBFETCH","1",1); // WindowServer's existing default: separately bound zero attachment.
  source=[source stringByReplacingOccurrencesOfString:@"sampler s [[sampler(0)]])" withString:@"sampler s [[sampler(0)]],float prior [[color(0)]])"];
  source=[source stringByReplacingOccurrencesOfString:@"sampler s [[sampler(1)]])" withString:@"sampler s [[sampler(1)]],float prior [[color(0)]])"];
  source=[source stringByReplacingOccurrencesOfString:@"return a.sample" withString:@"return prior+a.sample"];
 }
 NSError *err=nil;id<MTLLibrary>lib=[d newLibraryWithSource:source options:nil error:&err];if(!lib){fprintf(stderr,"shader %s\n",err.description.UTF8String);return 2;}
 NSMutableArray *pipelines=[NSMutableArray new];
 for(NSString *name in @[@"f",@"g"]){MTLRenderPipelineDescriptor *pd=[MTLRenderPipelineDescriptor new];pd.vertexFunction=[lib newFunctionWithName:@"v"];pd.fragmentFunction=[lib newFunctionWithName:name];pd.colorAttachments[0].pixelFormat=MTLPixelFormatR32Float;id p=[d newRenderPipelineStateWithDescriptor:pd error:&err];if(!p){fprintf(stderr,"pipeline %s\n",err.description.UTF8String);return 3;}[pipelines addObject:p];}
 NSMutableArray *textures=[NSMutableArray new];MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatR32Float width:4 height:4 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead;
 for(unsigned i=0;i<3;i++){id<MTLTexture>t=[d newTextureWithDescriptor:td];assert(t);float px[16];for(unsigned j=0;j<16;j++)px[j]=100+i+((churn||mask)?(j%4)*16+(j/4)*64:0);[t replaceRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0 withBytes:px bytesPerRow:16];[textures addObject:t];}
 td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatR32Float width:64 height:32 mipmapped:NO];td.usage=MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead;id<MTLTexture>rt=[d newTextureWithDescriptor:td];assert(rt);
 MTLSamplerDescriptor *sd=[MTLSamplerDescriptor new];id<MTLSamplerState>nearest=[d newSamplerStateWithDescriptor:sd];sd.minFilter=MTLSamplerMinMagFilterLinear;sd.magFilter=MTLSamplerMinMagFilterLinear;id<MTLSamplerState>linear=[d newSamplerStateWithDescriptor:sd];assert(nearest&&linear);
 id<MTLCommandQueue>q=[d newCommandQueue];id<MTLCommandBuffer>cb=[q commandBuffer];MTLRenderPassDescriptor *rp=[MTLRenderPassDescriptor renderPassDescriptor];rp.colorAttachments[0].texture=rt;rp.colorAttachments[0].loadAction=MTLLoadActionClear;rp.colorAttachments[0].storeAction=MTLStoreActionStore;rp.colorAttachments[0].clearColor=MTLClearColorMake(0.25,0,0,0);
 id<MTLRenderCommandEncoder>enc=[cb renderCommandEncoderWithDescriptor:rp];assert(enc);uint64_t before[4],after[4];stats(before);uint64_t start=clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
 [enc setRenderPipelineState:pipelines[0]];[enc setFragmentTexture:textures[1] atIndex:1];[enc setFragmentSamplerState:nearest atIndex:0];[enc setFragmentSamplerState:linear atIndex:1];
 for(unsigned i=0;i<2048;i++){
  [enc setFragmentTexture:textures[(i&1)?2:0] atIndex:0];if(churn)[enc setFragmentSamplerState:(i%3==2)?linear:nearest atIndex:0];if(mask)[enc setRenderPipelineState:pipelines[i&1]];
  [enc setViewport:(MTLViewport){(double)(i%64),(double)(i/64),1,1,0,1}];[enc setScissorRect:(MTLScissorRect){i%64,i/64,1,1}];[enc drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
 }
 [enc endEncoding];double encode=(clock_gettime_nsec_np(CLOCK_UPTIME_RAW)-start)/1e6;[cb commit];[cb waitUntilCompleted];if(cb.status==MTLCommandBufferStatusError){fprintf(stderr,"GPU %s\n",cb.error.description.UTF8String);return 4;}
 float read[2048];[rt getBytes:read bytesPerRow:256 fromRegion:MTLRegionMake2D(0,0,64,32) mipmapLevel:0];
 for(unsigned i=0;i<2048;i++){unsigned offset=(mask&&(i&1))||(churn&&i%3==2)?120:160;float expected=201+((i&1)?2:0)+((churn||mask)?2*offset:0);if(fetch&&live)expected+=0.25f;if(read[i]!=expected){fprintf(stderr,"PIXEL %u got%f expected%f\n",i,read[i],expected);return 5;}}
 stats(after);if(getenv("G6MF_EXPECT_NO_METADATA"))assert(after[3]==before[3]);else if(!strcmp(argv[2],"1")&&!mask)assert(after[3]>before[3]);if(!strcmp(argv[2],"0"))assert(after[3]==before[3]);printf("RENDER PASS mode=%s draws=2048 encode_ms=%.3f sets=%llu writes=%llu copies=%llu fast_cases=%llu\n",argv[2],encode,after[0]-before[0],after[1]-before[1],after[2]-before[2],after[3]-before[3]);if (auditStats) {
   auditStats(auditAfter,13);
   printf("DESC_AUDIT events=%llu exact=%llu table=%llu noopt=%llu no_last=%llu layout=%llu stale=%llu storage=%llu mask=%llu changed=%llu other=%llu batch_hit=%llu batch_miss=%llu\n",
      (unsigned long long)(auditAfter[0]-auditBefore[0]), (unsigned long long)(auditAfter[1]-auditBefore[1]),
      (unsigned long long)(auditAfter[2]-auditBefore[2]), (unsigned long long)(auditAfter[3]-auditBefore[3]),
      (unsigned long long)(auditAfter[4]-auditBefore[4]), (unsigned long long)(auditAfter[5]-auditBefore[5]),
      (unsigned long long)(auditAfter[6]-auditBefore[6]), (unsigned long long)(auditAfter[7]-auditBefore[7]),
      (unsigned long long)(auditAfter[8]-auditBefore[8]), (unsigned long long)(auditAfter[9]-auditBefore[9]),
      (unsigned long long)(auditAfter[10]-auditBefore[10]), (unsigned long long)(auditAfter[11]-auditBefore[11]),
      (unsigned long long)(auditAfter[12]-auditBefore[12]));
 }
 return 0;
}}
