/* x86_64 macOS diagnostic. Uses public Objective-C/Metal entry points through
 * dlopen so the offline test needs neither Xcode nor a compiler on the laptop.
 * No display or WindowServer changes. A blit/readback is not a shader test.
 * APIs: developer.apple.com/documentation/metal/mtlblitcommandencoder
 */
typedef unsigned long Size;
typedef void *Obj;
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern char *dlerror(void);
extern int printf(const char *, ...);
extern int puts(const char *);
extern int fflush(void *);
extern int usleep(unsigned int);
extern unsigned int alarm(unsigned int);
extern char *strstr(const char *, const char *);
#ifdef G6MF_LUT_PROBE
extern void setprogname(const char *);
#endif
static void *send;
static void *(*sel)(const char *);
static Obj msg(Obj o, const char *s) { return ((Obj (*)(Obj,void *))send)(o,sel(s)); }
static Size number(Obj o, const char *s) { return ((Size (*)(Obj,void *))send)(o,sel(s)); }
static int fail(const char *s) { printf("FAIL: %s\n",s); return 1; }
#ifdef G6MF_SHADER_PROBE
typedef struct { Size width,height,depth; } Dimensions;
static int computeTest(Obj device, Obj (*cls)(const char *)) {
 const char *source="#include <metal_stdlib>\nusing namespace metal;\n"
  "kernel void g6mf_compute(device const uint *a [[buffer(0)]], device uint *b [[buffer(1)]], uint i [[thread_position_in_grid]]) { b[i]=(a[i]*1664525u+1013904223u)^(i*0x9e3779b9u); }\n";
 Obj text=((Obj (*)(Obj,void *,const char *))send)(cls("NSString"),sel("stringWithUTF8String:"),source);
 Obj error=0;
 puts("Compiling MSL compute source on the NVIDIA Metal device...");fflush(0);
 Obj lib=((Obj (*)(Obj,void *,Obj,Obj,Obj *))send)(device,sel("newLibraryWithSource:options:error:"),text,0,&error);
 if(!lib) {
  const char *why=(const char *)msg(msg(error,"description"),"UTF8String");
  printf("library error: %s\n",why?why:"no NSError description");
  return fail("MSL library compilation");
 }
 Obj name=((Obj (*)(Obj,void *,const char *))send)(cls("NSString"),sel("stringWithUTF8String:"),"g6mf_compute");
 Obj function=((Obj (*)(Obj,void *,Obj))send)(lib,sel("newFunctionWithName:"),name);
 if(!function)return fail("compute function lookup");
 puts("Creating NVIDIA compute pipeline...");fflush(0);
 Obj pipeline=((Obj (*)(Obj,void *,Obj,Obj *))send)(device,sel("newComputePipelineStateWithFunction:error:"),function,&error);
 if(!pipeline) {
  const char *why=(const char *)msg(msg(error,"description"),"UTF8String");
  printf("pipeline error: %s\n",why?why:"no NSError description");
  return fail("compute pipeline creation");
 }
 if(number(pipeline,"maxTotalThreadsPerThreadgroup")<32)return fail("compute pipeline cannot dispatch 32 threads");
 const Size count=1024,guard=32,bytes=(count+guard)*4;
 Obj input=((Obj (*)(Obj,void *,Size,Size))send)(device,sel("newBufferWithLength:options:"),bytes,0);
 Obj output=((Obj (*)(Obj,void *,Size,Size))send)(device,sel("newBufferWithLength:options:"),bytes,0);
 if(!input || !output)return fail("compute buffers");
 unsigned int *a=(unsigned int *)msg(input,"contents"),*b=(unsigned int *)msg(output,"contents");
 if(!a || !b)return fail("compute buffer mappings");
 Obj queue=msg(device,"newCommandQueue");
 if(!queue)return fail("compute queue");
 for(unsigned run=0;run<2;++run) {
  for(Size i=0;i<count+guard;++i) {a[i]=(unsigned int)i*17u+run*0x13579bdu;b[i]=0xdeadbeefu;}
  Obj cb=msg(queue,"commandBuffer"),encoder=msg(cb,"computeCommandEncoder");
  if(!cb || !encoder)return fail("compute command encoder");
  ((void (*)(Obj,void *,Obj))send)(encoder,sel("setComputePipelineState:"),pipeline);
  ((void (*)(Obj,void *,Obj,Size,Size))send)(encoder,sel("setBuffer:offset:atIndex:"),input,0,0);
  ((void (*)(Obj,void *,Obj,Size,Size))send)(encoder,sel("setBuffer:offset:atIndex:"),output,0,1);
  ((void (*)(Obj,void *,Dimensions,Dimensions))send)(encoder,sel("dispatchThreadgroups:threadsPerThreadgroup:"),(Dimensions){32,1,1},(Dimensions){32,1,1});
  msg(encoder,"endEncoding");msg(cb,"commit");
  Size status=0;
  for(unsigned n=0;n<600;++n){status=number(cb,"status");if(status>=4)break;usleep(100000);}
  if(status!=4)return fail("compute command error or timeout");
  for(Size i=0;i<count;++i) {
   unsigned int expected=(a[i]*1664525u+1013904223u)^((unsigned int)i*0x9e3779b9u);
   if(b[i]!=expected){printf("compute mismatch run=%u index=%lu got=%08x expected=%08x\n",run,i,b[i],expected);return fail("compute shader readback");}
  }
  for(Size i=count;i<count+guard;++i)if(b[i]!=0xdeadbeefu)return fail("compute shader overwrote guard region");
  printf("PASS: compute dispatch %u, 1024 output values matched, 32 guard words preserved.\n",run+1);fflush(0);
 }
 msg(input,"release");msg(output,"release");msg(queue,"release");msg(pipeline,"release");msg(function,"release");msg(lib,"release");
 puts("SHADER PASS: NVIDIA MSL compile, pipeline, two dispatches and CPU verification succeeded.");
 return 0;
}
#endif
int main(void) {
#ifdef G6MF_LUT_PROBE
 /* Exercise the WindowServer-only policy in a separate GPU test process. */
 setprogname("WindowServer");
#endif
#ifdef G6MF_SHADER_PROBE
 alarm(240);
#else
 alarm(90);
#endif
 void *objc=dlopen("/usr/lib/libobjc.A.dylib",2);
 void *metal=dlopen("/System/Library/Frameworks/Metal.framework/Metal",2);
 if(!objc || !metal) return fail(dlerror());
 send=dlsym(objc,"objc_msgSend"); sel=(void *(*)(const char *))dlsym(objc,"sel_registerName");
 Obj (*all)(void)=(Obj (*)(void))dlsym(metal,"MTLCopyAllDevices");
 Obj (*cls)(const char *)=(Obj (*)(const char *))dlsym(objc,"objc_getClass");
 if(!send || !sel || !all || !cls) return fail("Metal/Objective-C entry point absent");
 Obj pool=msg(msg(cls("NSAutoreleasePool"),"alloc"),"init");
 Obj devices=all(), device=0; Size count=number(devices,"count");
 printf("Metal devices: %lu\n",count);
 for(Size i=0;i<count;++i) {
  Obj d=((Obj (*)(Obj,void *,Size))send)(devices,sel("objectAtIndex:"),i);
  const char *name=(const char *)msg(msg(d,"name"),"UTF8String");
  printf("device[%lu]: %s registryID=0x%lx\n",i,name?name:"(null)",number(d,"registryID"));
  if(name && (strstr(name,"NVIDIA") || strstr(name,"GeForce") || strstr(name,"RTX"))) device=d;
 }
 fflush(0);
 if(!device) return fail("no NVIDIA Metal device; other GPUs do not count as success");
#ifdef G6MF_LUT_PROBE
 Size width=number(device,"maxTextureWidth1D");
 printf("LUT CAP: %lu\n",width);fflush(0);
 if(width!=1024)return fail("WindowServer test process did not see the experimental 1024 limit");
#endif
 const Size bytes=4096;
 Obj src=((Obj (*)(Obj,void *,Size,Size))send)(device,sel("newBufferWithLength:options:"),bytes,0);
 Obj dst=((Obj (*)(Obj,void *,Size,Size))send)(device,sel("newBufferWithLength:options:"),bytes,0);
 if(!src || !dst) return fail("shared buffer allocation");
 unsigned char *s=(unsigned char *)msg(src,"contents"),*d=(unsigned char *)msg(dst,"contents");
 if(!s || !d) return fail("shared buffer CPU mapping");
 for(Size i=0;i<bytes;++i) {s[i]=(unsigned char)(i*37+19);d[i]=0;}
 Obj queue=msg(device,"newCommandQueue"),cb=msg(queue,"commandBuffer"),blit=msg(cb,"blitCommandEncoder");
 if(!queue || !cb || !blit) return fail("command queue/buffer/blit encoder");
 ((void (*)(Obj,void *,Obj,Size,Obj,Size,Size))send)(blit,sel("copyFromBuffer:sourceOffset:toBuffer:destinationOffset:size:"),src,0,dst,0,bytes);
 msg(blit,"endEncoding");msg(cb,"commit");
 Size status=0;
 for(unsigned n=0;n<600;++n) {status=number(cb,"status");if(status>=4)break;usleep(100000);}
 if(status!=4) {
  const char *error=(const char *)msg(msg(msg(cb,"error"),"description"),"UTF8String");
  printf("command status=%lu error=%s\n",status,error?error:"none");
  return fail("GPU command error or 60 second completion timeout");
 }
 for(Size i=0;i<bytes;++i) if(d[i]!=(unsigned char)(i*37+19)) {
  printf("mismatch at %lu: %u\n",i,d[i]);return fail("GPU buffer readback mismatch");
 }
 puts("PASS: NVIDIA Metal command completed; 4096 byte blit/readback matched.");
 puts("This does not validate shader execution, scanout, WindowServer or head-4 copying.");
#ifdef G6MF_SHADER_PROBE
 if(computeTest(device,cls))return 1;
#endif
 msg(src,"release");msg(dst,"release");msg(queue,"release");msg(devices,"release");msg(pool,"drain");
 return 0;
}
