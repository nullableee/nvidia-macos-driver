/* Experimental loader for the exact existing NVMTL plugin. No Apple code patches.
 * Reduces the advertised 1D texture limit only inside WindowServer, opt-in file.
 */
extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern const char *dlerror(void);
extern const char *getprogname(void);
extern int strcmp(const char *,const char *);
extern int open(const char *,int,...);
extern long read(int,void *,unsigned long);
extern int close(int);
extern void syslog(int,const char *,...);
typedef unsigned long long (*WidthIMP)(void *,void *);
static WidthIMP originalWidth;
static unsigned long long cap;
static int logged;
#define REAL_PLUGIN "/Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/NVMTLDriver.g6mf-original"
#define CONFIG "/Library/NullMoth/g6mf-lut-limit"
static unsigned long long parseCap(const char *s,unsigned long n) {
    unsigned long long value=0;unsigned long i=0;
    if(!n)return 0;
    for(;i<n&&s[i]>='0'&&s[i]<='9';++i){value=value*10+(unsigned)(s[i]-'0');if(value>16384)return 0;}
    if(!i)return 0;
    for(;i<n;++i)if(s[i]!='\n'&&s[i]!='\r'&&s[i]!=' '&&s[i]!='\t')return 0;
    return value==1024||value==2048||value==4096||value==16384?value:0;
}
static unsigned long long limitedWidth(void *self,void *selector) {
    unsigned long long base=originalWidth(self,selector);
    unsigned long long result=cap&&cap<base?cap:base;
    if(base&&!__atomic_exchange_n(&logged,1,__ATOMIC_RELAXED))
        syslog(5,"G6MF-LUT: maxTextureWidth1D original=%llu advertised=%llu; WindowServer-only experiment",base,result);
    return result;
}
__attribute__((constructor)) static void loadOriginal(void) {
    void *real=dlopen(REAL_PLUGIN,2|8); /* RTLD_NOW | RTLD_GLOBAL */
    if(!real){syslog(3,"G6MF-LUT: original plugin load failed: %s",dlerror());return;}
    const char *process=getprogname();
    if(!process||strcmp(process,"WindowServer"))return;
    char text[32];int fd=open(CONFIG,0);if(fd<0)return;
    long n=read(fd,text,sizeof text);close(fd);
    if(n<=0||(unsigned long)n==sizeof text)return;
    cap=parseCap(text,(unsigned long)n);if(!cap)return;
    void *runtime=dlopen("/usr/lib/libobjc.A.dylib",2);if(!runtime)return;
    void *(*getClass)(const char *)=dlsym(runtime,"objc_getClass");
    void *(*selector)(const char *)=dlsym(runtime,"sel_registerName");
    void *(*getMethod)(void *,void *)=dlsym(runtime,"class_getInstanceMethod");
    void *(*getSuper)(void *)=dlsym(runtime,"class_getSuperclass");
    void *(*getIMP)(void *)=dlsym(runtime,"method_getImplementation");
    const char *(*getType)(void *)=dlsym(runtime,"method_getTypeEncoding");
    unsigned char (*addMethod)(void *,void *,void *,const char *)=dlsym(runtime,"class_addMethod");
    void *(*setIMP)(void *,void *)=dlsym(runtime,"method_setImplementation");
    if(!getClass||!selector||!getMethod||!getSuper||!getIMP||!getType||!addMethod||!setIMP)return;
    void *cls=getClass("NVMTLDevice"),*sel=selector("maxTextureWidth1D");
    void *method=cls&&sel?getMethod(cls,sel):0;
    const char *type=method?getType(method):0;
    if(!type||type[0]!='Q'){syslog(3,"G6MF-LUT: NVMTLDevice width method/ABI unavailable; leaving original limit");return;}
    WidthIMP base=(WidthIMP)getIMP(method);if(!base||base==limitedWidth)return;
    originalWidth=base;
    // Add an override on NVMTLDevice rather than modifying _MTLDevice's shared
    // inherited method (which would affect other GPUs in WindowServer).
    if(!addMethod(cls,sel,(void *)limitedWidth,type)) {
        void *parent=getSuper(cls),*own=getMethod(cls,sel);
        if(parent&&own==getMethod(parent,sel)) {
            syslog(3,"G6MF-LUT: could not add subclass override; leaving inherited implementation");return;
        }
        setIMP(own,(void *)limitedWidth);
    }
    syslog(5,"G6MF-LUT: installed NVMTLDevice-only override, cap=%llu",cap);
}
