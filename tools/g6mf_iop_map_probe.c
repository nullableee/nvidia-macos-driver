/* Read-only IOPresentmentGetMap diagnostic, based on agdc/iop-getmap.c.
 * Dynamic framework imports allow a ready x86_64 binary without target Xcode. */
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern int puts(const char *);
extern int printf(const char *, ...);
extern unsigned int alarm(unsigned int);
int main(void) {
 alarm(15);
 void *iop=dlopen("/System/Library/PrivateFrameworks/IOPresentment.framework/IOPresentment",2);
 void *cf=dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",2);
 if(!iop||!cf){puts("MAP UNKNOWN: framework load failed");return 2;}
 const void *(*getmap)(void)=(const void *(*)(void))dlsym(iop,"IOPresentmentGetMap");
 void (*show)(const void*)=(void (*)(const void*))dlsym(cf,"CFShow");
 if(!getmap||!show){puts("MAP UNKNOWN: entry point absent");return 2;}
 const void *map=getmap();
 if(!map){puts("MAP NULL");return 1;}
 puts("MAP PRESENT (not proof of successful frame presentation):");show(map);return 0;
}
