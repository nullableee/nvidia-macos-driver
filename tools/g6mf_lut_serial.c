/* Optional, process-local dispatch_apply import rebinding. No executable pages
 * or headroom/cache fields are modified. Exact CoreDisplay UUID/site only. */
extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern const char *getprogname(void);
extern int strcmp(const char *,const char *);
extern int open(const char *,int,...);
extern long read(int,void *,unsigned long);
extern int close(int);
extern void syslog(int,const char *,...);
typedef unsigned long long U64;
typedef unsigned int U32;
typedef void (*Apply)(unsigned long,void *,void *);
struct Block { void *isa; int flags,reserved; void (*invoke)(void *,unsigned long); };
static Apply originalApply;
static U64 lutReturn,lutInvoke;
static int installed,seen;
static void **importSlot;
static const char *reason="serial experiment not requested";
static int eligible(unsigned long n,void *block,U64 caller) {
    return block && n>0 && n<=16384 && caller==lutReturn &&
           (U64)((struct Block *)block)->invoke==lutInvoke;
}
static void serialRun(unsigned long n,void *block) {
    struct Block *b=block;
    for(unsigned long i=0;i<n;++i)b->invoke(block,i);
}
static void routeApply(unsigned long n,void *queue,void *block,U64 caller) {
    if(!eligible(n,block,caller)){originalApply(n,queue,block);return;}
    if(!__atomic_exchange_n(&seen,1,__ATOMIC_RELAXED))
        syslog(5,"G6MF-LUT-SERIAL: matched real CoreDisplay LUT, entries=%lu; serial execution",n);
    serialRun(n,block);
}
__attribute__((noinline)) static void selectedApply(unsigned long n,void *queue,void *block) {
    routeApply(n,queue,block,(U64)__builtin_return_address(0));
}
static U32 u32(const unsigned char *p) { U32 v;__builtin_memcpy(&v,p,4);return v; }
static U64 u64(const unsigned char *p) { U64 v;__builtin_memcpy(&v,p,8);return v; }
static int same(const unsigned char *a,const unsigned char *b,unsigned n) {
    for(unsigned i=0;i<n;++i)if(a[i]!=b[i])return 0;return 1;
}
static const unsigned char uuid[16]={0x24,0x68,0x2c,0xf5,0xc1,0x29,0x3a,0x3f,0x91,0xc7,0x80,0xa2,0x28,0x55,0x23,0x72};
/* Runtime view of a loaded image, not an extracted-file offset. */
static int identify(const unsigned char *header,U64 *slide) {
    if(!header||u32(header)!=0xfeedfacf||u32(header+4)!=0x1000007)return 0;
    U32 count=u32(header+16),bytes=u32(header+20);if(count>512||bytes>65536)return 0;
    unsigned offset=32;int match=0,text=0;
    for(U32 i=0;i<count;++i){
        if(offset>32+bytes-8)return 0;
        const unsigned char *p=header+offset;U32 cmd=u32(p),size=u32(p+4);
        if(size<8||size>32+bytes-offset)return 0;
        if(cmd==0x1b&&size==24)match=same(p+8,uuid,16);
        if(cmd==0x19&&size>=72&&same(p+8,(const unsigned char *)"__TEXT\0",7)){
            if(u64(p+24)!=0x7ff805347000ull)return 0;
            *slide=(U64)header-u64(p+24);text=1;
        }
        offset+=size;
    }
    return match&&text;
}
/* Mach ABI uses int arrays for vm_region_basic_info_64. Supply a generously
 * sized buffer and only inspect its first two vm_prot_t fields. */
static int bindSlot(void **slot,void *expected,void *replacement,void *system) {
    int (*region)(U32,U64 *,U64 *,int,int *,U32 *,U32 *)=dlsym(system,"mach_vm_region");
    int (*protect)(U32,U64,U64,int,int)=dlsym(system,"mach_vm_protect");
    int (*deallocate)(U32,U32)=dlsym(system,"mach_port_deallocate");
    U32 *task=dlsym(system,"mach_task_self_");
    int (*pageSize)(void)=dlsym(system,"getpagesize");
    reason="Mach APIs unavailable or import unaligned";
    if(!region||!protect||!deallocate||!task||!pageSize||((U64)slot&7))return 0;
    U64 address=(U64)slot,size=0;int info[32]={0};U32 count=32,object=0;
    reason="import region query/protection refused";
    int rc=region(*task,&address,&size,9,info,&count,&object);
    if(object)deallocate(*task,object);
    if(rc||count<2||address>(U64)slot||size<8||(U64)slot-address>size-8||
       !(info[0]&1)||(info[0]&4))return 0; /* readable data, never executable */
    unsigned pageBytes=(unsigned)pageSize();
    if(pageBytes<4096||pageBytes>65536||(pageBytes&(pageBytes-1)))return 0;
    U64 page=(U64)slot&~((U64)pageBytes-1);
    if(page<address||page-address>size||pageBytes>size-(page-address))return 0;
    /* Modify only the containing data page, retaining its original protection. */
    reason="private writable data mapping refused";
    if(protect(*task,page,pageBytes,0,info[0]|2|0x10))return 0; /* VM_PROT_COPY */
    void *old=expected;
    int changed=__atomic_compare_exchange_n(slot,&old,replacement,0,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
    reason="import changed concurrently";
    if(protect(*task,page,pageBytes,0,info[0])){
        reason="original data protection restore failed; import rolled back";
        if(changed){old=replacement;__atomic_compare_exchange_n(slot,&old,expected,0,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);}
        protect(*task,page,pageBytes,0,info[0]);
        return 0;
    }
    return changed;
}
static void installSerial(void) {
    const char *process=getprogname();if(!process||strcmp(process,"WindowServer"))return;
    char setting[4];int fd=open("/Library/NullMoth/g6mf-lut-serial",0);if(fd<0)return;
    long n=read(fd,setting,4);close(fd);
    if(!((n==1&&setting[0]=='1')||(n==2&&setting[0]=='1'&&setting[1]=='\n')))return;
    reason="libSystem APIs unavailable";
    void *system=dlopen("/usr/lib/libSystem.B.dylib",2);if(!system)return;
    U32 (*imageCount)(void)=dlsym(system,"_dyld_image_count");
    const unsigned char *(*imageHeader)(U32)=dlsym(system,"_dyld_get_image_header");
    const char *(*imageName)(U32)=dlsym(system,"_dyld_get_image_name");
    Apply apply=dlsym(system,"dispatch_apply");
    if(!imageCount||!imageHeader||!imageName||!apply)return;
    reason="CoreDisplay image not found";
    for(U32 i=0;i<imageCount();++i){
        const char *name=imageName(i);
        if(!name||strcmp(name,"/System/Library/Frameworks/CoreDisplay.framework/Versions/A/CoreDisplay"))continue;
        reason="CoreDisplay UUID/header mismatch";
        U64 slide=0;if(!identify(imageHeader(i),&slide))break;
        const unsigned char *stub=(const unsigned char *)(0x7ff80543a230ull+slide);
        const unsigned char *call=(const unsigned char *)(0x7ff80540bbadull+slide);
        reason="CoreDisplay dispatch call/stub mismatch";
        if(stub[0]!=0xff||stub[1]!=0x25||call[0]!=0xe8)break;
        int displacement;__builtin_memcpy(&displacement,call+1,4);
        if((U64)(call+5)+displacement!=(U64)stub)break;
        __builtin_memcpy(&displacement,stub+2,4);
        void **slot=(void **)((U64)(stub+6)+displacement);
        reason="current import differs from original dispatch_apply";
        if(__atomic_load_n(slot,__ATOMIC_SEQ_CST)!=(void *)apply)break;
        /* Publishing immutable routing data precedes the atomic pointer swap. */
        originalApply=apply;lutReturn=(U64)(call+5);lutInvoke=0x7ff80540c3f2ull+slide;
        installed=bindSlot(slot,(void *)apply,(void *)selectedApply,system);
        if(installed){importSlot=slot;reason="installed";}
        break;
    }
    syslog(installed?5:3,"G6MF-LUT-SERIAL: import %s; exact UUID/site, original math and cache rules; %s",installed?"installed":"unavailable (original dispatch retained)",reason);
}
/* Called from the already validated loader constructor after loading the real
 * plugin. No separate constructor ordering dependency. */
void g6mfInstallLUTSerial(void){installSerial();}
static unsigned long testCount,testSum;
static void testInvoke(void *b,unsigned long i){(void)b;++testCount;testSum+=i;}
int g6mfLUTSerialSelfTest(void){
    if(!installed||!importSlot||__atomic_load_n(importSlot,__ATOMIC_SEQ_CST)!=(void *)selectedApply)return 0;
    struct Block b={0,0,0,testInvoke};testCount=testSum=0;serialRun(1024,&b);
    return testCount==1024&&testSum==523776;
}

int g6mfLUTSerialDelegateProbe(void *block){if(!installed)return 0;selectedApply(17,0,block);return 1;}

const char *g6mfLUTSerialReason(void){return reason;}
