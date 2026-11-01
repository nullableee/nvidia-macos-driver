extern void setprogname(const char *);
extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern const char *dlerror(void);
extern int printf(const char *,...);
extern int puts(const char *);
extern unsigned int alarm(unsigned int);
static unsigned counts[17];
int main(void){
 alarm(60);setprogname("WindowServer");
 if(!dlopen("/System/Library/Frameworks/CoreDisplay.framework/Versions/A/CoreDisplay",2)){printf("SERIAL FAIL: CoreDisplay load: %s\n",dlerror());return 1;}
 void *loader=dlopen("/Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/NVMTLDriver",2);
 if(!loader){printf("SERIAL FAIL: loader: %s\n",dlerror());return 1;}
 int (*test)(void)=dlsym(loader,"g6mfLUTSerialSelfTest");
 int (*delegate)(void *)=dlsym(loader,"g6mfLUTSerialDelegateProbe");
 if(!test||!delegate||!test()){
  const char *(*why)(void)=dlsym(loader,"g6mfLUTSerialReason");
  printf("SERIAL FAIL: %s; retain the existing desktop\n",why?why():"serial loader exports unavailable");return 1;
 }
 void (^block)(unsigned long)=^(unsigned long i){if(i<17)__atomic_fetch_add(&counts[i],1,__ATOMIC_RELAXED);};
 if(!delegate((void *)block)){puts("SERIAL FAIL: delegate unavailable");return 1;}
 for(unsigned i=0;i<17;++i)if(counts[i]!=1){puts("SERIAL FAIL: original dispatch iteration check");return 1;}
 puts("SERIAL HOOK PASS: exact CoreDisplay UUID/site, data import rebound, 1024 serial iterations and original dispatch delegation verified in this probe process.");
 puts("Real WindowServer LUT matching and performance still require a reboot and profile.");
 return 0;
}
