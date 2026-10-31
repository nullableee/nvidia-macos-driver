#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOKit/IOKitLib.h>
#import <dlfcn.h>
#include <assert.h>
#include <time.h>
#include <cpuid.h>
#include <pthread.h>
#include <sys/qos.h>
static unsigned coretype(void){unsigned a,b,c,d;__cpuid_count(0x1a,0,a,b,c,d);return a>>24;}
@interface NSObject(DescriptorProbeInit)
- (id)initWithAcceleratorPort:(mach_port_t)p;
@end
int main(int argc,char **argv){@autoreleasepool{
    assert(argc==3);void *module=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(module);
    if(getenv("G6MF_QOS_UI"))pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE,0);
    setenv("G6MF_TEST_DIRTY_COPY",argv[2],1);
    setenv("NVMTL_METADATA_REUSE",argv[2],1);
    setenv("G6MF_TEST_QUEUE_STATS","1",1);
    void (*stats)(uint64_t*)=dlsym(module,"g6mf_descriptor_stats");assert(stats);
    io_service_t port=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("NVAccel"));
    id<MTLDevice> d=[[NSClassFromString(@"NVMTLDevice") alloc]initWithAcceleratorPort:port];IOObjectRelease(port);assert(d);
    NSMutableString *source=[NSMutableString stringWithString:@"#include <metal_stdlib>\nusing namespace metal;\nkernel void probe("];
    for(unsigned i=0;i<16;i++)[source appendFormat:@"texture2d<float,access::sample> t%u [[texture(%u)]],",i,i];
    [source appendString:@"sampler smp [[sampler(0)]],device uint* out [[buffer(0)]],constant uint& idx [[buffer(1)]],uint tid [[thread_position_in_grid]]) {if(tid==0) out[idx]="];
    for(unsigned i=0;i<16;i++)[source appendFormat:@"%@uint(t%u.sample(smp,float2(0.5),level(0.0)).x)",i?@"+":@"",i];[source appendString:@";}"];
    NSError *err=nil;id<MTLLibrary> lib=[d newLibraryWithSource:source options:nil error:&err];if(!lib){fprintf(stderr,"shader: %s\n",err.description.UTF8String);return 2;}
    id<MTLComputePipelineState> pipeline=[d newComputePipelineStateWithFunction:[lib newFunctionWithName:@"probe"] error:&err];if(!pipeline){fprintf(stderr,"pipeline: %s\n",err.description.UTF8String);return 3;}
    BOOL churn=getenv("G6MF_SAMPLER_CHURN")!=NULL, maskChurn=getenv("G6MF_MASK_CHURN")!=NULL, bufferChurn=getenv("G6MF_BUFFER_CHURN")!=NULL;
    id<MTLComputePipelineState> second=nil;
    if(maskChurn){NSString *other=[source stringByReplacingOccurrencesOfString:@"sampler(0)" withString:@"sampler(1)"];id<MTLLibrary> l=[d newLibraryWithSource:other options:nil error:&err];assert(l);second=[d newComputePipelineStateWithFunction:[l newFunctionWithName:@"probe"] error:&err];assert(second);}
    NSMutableArray *textures=[NSMutableArray new];
    MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatR32Float width:4 height:4 mipmapped:NO];td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead;
    for(unsigned i=0;i<17;i++){id<MTLTexture> t=[d newTextureWithDescriptor:td];assert(t);float pixels[16];for(unsigned j=0;j<16;j++)pixels[j]=100+i+((churn||maskChurn)?(j%4)*16+(j/4)*64:0);[t replaceRegion:MTLRegionMake2D(0,0,4,4) mipmapLevel:0 withBytes:pixels bytesPerRow:16];[textures addObject:t];}
    BOOL paired=!strcmp(argv[2],"pair");
    void (*selectMode)(int)=dlsym(module,"g6mf_descriptor_mode");if(paired)assert(selectMode);
    const unsigned order[]={0,1,1,0,1,0,0,1};
    for(unsigned phase=0;phase<(paired?8:1);phase++){@autoreleasepool{
    const char *currentMode=paired?(order[phase]?"1":"0"):argv[2];if(paired)selectMode(order[phase]);
    const unsigned n=2000;id<MTLBuffer> out=[d newBufferWithLength:n*4 options:MTLResourceStorageModeShared];assert(out);
    id<MTLBuffer> otherOut=[d newBufferWithLength:n*4 options:MTLResourceStorageModeShared];assert(otherOut);
    memset(out.contents,0,n*4);memset(otherOut.contents,0,n*4);
    id<MTLCommandQueue> q=[d newCommandQueue];id<MTLCommandBuffer> cb=[q commandBuffer];id<MTLComputeCommandEncoder> enc=[cb computeCommandEncoder];
    uint64_t before[4],after[4];stats(before);unsigned coreBefore=coretype();uint64_t start=clock_gettime_nsec_np(CLOCK_UPTIME_RAW),cpuStart=clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID);
    [enc setComputePipelineState:pipeline];[enc setBuffer:out offset:0 atIndex:0];
    MTLSamplerDescriptor *sd=[MTLSamplerDescriptor new];id<MTLSamplerState> sampler=[d newSamplerStateWithDescriptor:sd];assert(sampler);[enc setSamplerState:sampler atIndex:0];
    sd.minFilter=MTLSamplerMinMagFilterLinear;sd.magFilter=MTLSamplerMinMagFilterLinear;id<MTLSamplerState> linear=[d newSamplerStateWithDescriptor:sd];assert(linear);[enc setSamplerState:linear atIndex:1];
    for(unsigned i=0;i<16;i++)[enc setTexture:textures[i] atIndex:i];
    for(unsigned i=0;i<n;i++){
        if(churn)[enc setSamplerState:(i%3==2)?linear:sampler atIndex:0];
        if(maskChurn)[enc setComputePipelineState:(i&1)?second:pipeline];
        if(bufferChurn)[enc setBuffer:(i/64)&1?otherOut:out offset:0 atIndex:0];
        [enc setTexture:textures[(i&1)?16:0] atIndex:0];[enc setBytes:&i length:sizeof i atIndex:1];
        [enc dispatchThreads:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(1,1,1)];
    }
    [enc endEncoding];double cpuMS=(clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)-cpuStart)/1e6;unsigned coreAfter=coretype();double encodeMS=(clock_gettime_nsec_np(CLOCK_UPTIME_RAW)-start)/1e6;
    [cb commit];[cb waitUntilCompleted];if(cb.status==MTLCommandBufferStatusError){fprintf(stderr,"GPU: %s\n",cb.error.description.UTF8String);return 4;}
    uint32_t *read=out.contents;assert(read);
    for(unsigned i=0;i<n;i++){if(bufferChurn)read=(bufferChurn&&((i/64)&1)?otherOut:out).contents;unsigned offset=(maskChurn&&(i&1))||(churn&&i%3==2)?120:160;unsigned expected=1720+((i&1)?16:0)+((churn||maskChurn)?16*offset:0);if(read[i]!=expected){fprintf(stderr,"MISMATCH %u got%u expected%u\n",i,read[i],expected);return 5;}}
    stats(after);if(!strcmp(currentMode,"1")&&!maskChurn)assert(after[3]>before[3]);if(!strcmp(currentMode,"0"))assert(after[3]==before[3]);printf("DESCRIPTOR PASS mode=%s phase=%u dispatches=%u encode_ms=%.3f cpu_ms=%.3f core=%02x:%02x total_ms=%.3f sets=%llu writes=%llu copies=%llu fast_cases=%llu\n",currentMode,phase,n,encodeMS,cpuMS,coreBefore,coreAfter,(clock_gettime_nsec_np(CLOCK_UPTIME_RAW)-start)/1e6,after[0]-before[0],after[1]-before[1],after[2]-before[2],after[3]-before[3]);fflush(stdout);
    }}
    void (*queueStats)(uint64_t*)=dlsym(module,"g6mf_queue_stats");
    if(queueStats){uint64_t v[9];queueStats(v);for(unsigned i=0;i<9;i++)assert(v[i]>0);printf("QUEUE STATS PASS: scheduled=%llu completed=%llu pending_max=%llu\n",v[0],v[3],v[8]);}
    return 0;
}}
