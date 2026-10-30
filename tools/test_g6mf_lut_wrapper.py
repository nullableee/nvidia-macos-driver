#!/usr/bin/env python3
"""Run production loader policy against mock ObjC runtime; no Metal emulation."""
from pathlib import Path
import subprocess,tempfile,re
R=Path(__file__).resolve().parents[1]
source=(R/'tools/g6mf_lut_wrapper.c').read_text().replace('__attribute__((constructor))','')
fixture=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
@@SOURCE@@
static const char *process,*configuration;
static int originalLoaded, ownExists, addFails, hasClass=1, badABI;
static WidthIMP baseMethod,ownMethod;
static int baseClass,childClass,selObject;
static unsigned long long full(void*a,void*b){(void)a;(void)b;return 16384;}
static unsigned long long local(void*a,void*b){(void)a;(void)b;return 8192;}
const char *getprogname(void){return process;}
void *dlopen(const char*p,int flags){(void)flags;if(!strcmp(p,REAL_PLUGIN))originalLoaded++;return (void*)1;}
const char *dlerror(void){return "fixture";}
int open(const char*p,int flags,...){(void)p;(void)flags;return configuration?7:-1;}
long read(int fd,void*out,unsigned long count){(void)fd;unsigned long n=strlen(configuration);if(n>count)n=count;memcpy(out,configuration,n);return n;}
int close(int fd){(void)fd;return 0;}
void syslog(int level,const char*fmt,...){(void)level;(void)fmt;}
static void *getClassMock(const char*s){return hasClass&&!strcmp(s,"NVMTLDevice")?&childClass:0;}
static void *selMock(const char*s){return !strcmp(s,"maxTextureWidth1D")?&selObject:0;}
static void *methodMock(void*cls,void*s){(void)s;return cls==&childClass&&ownExists?&ownMethod:&baseMethod;}
static void *superMock(void*c){(void)c;return &baseClass;}
static void *impMock(void*m){return *(void**)m;}
static const char *typeMock(void*m){(void)m;return badABI?"I16@0:8":"Q16@0:8";}
static unsigned char addMock(void*c,void*s,void*imp,const char*t){(void)c;(void)s;(void)t;if(ownExists||addFails)return 0;ownExists=1;ownMethod=(WidthIMP)imp;return 1;}
static void *setMock(void*m,void*imp){void*old=*(void**)m;*(void**)m=imp;return old;}
void *dlsym(void*h,const char*n){(void)h;
 if(!strcmp(n,"objc_getClass"))return getClassMock;
 if(!strcmp(n,"sel_registerName"))return selMock;
 if(!strcmp(n,"class_getInstanceMethod"))return methodMock;
 if(!strcmp(n,"class_getSuperclass"))return superMock;
 if(!strcmp(n,"method_getImplementation"))return impMock;
 if(!strcmp(n,"method_getTypeEncoding"))return typeMock;
 if(!strcmp(n,"class_addMethod"))return addMock;
 if(!strcmp(n,"method_setImplementation"))return setMock;
 return 0;
}
static void reset(void){originalWidth=0;cap=0;logged=0;originalLoaded=0;ownExists=0;addFails=0;hasClass=1;badABI=0;process="WindowServer";configuration="1024\n";baseMethod=full;ownMethod=local;}
int main(void){
 reset();loadOriginal();assert(originalLoaded==1&&ownExists&&baseMethod==full&&ownMethod(0,0)==1024);
 loadOriginal();assert(ownMethod(0,0)==1024); /* no recursion on repeated loader call */
 reset();process="Safari";loadOriginal();assert(originalLoaded==1&&!ownExists&&baseMethod==full);
 reset();ownExists=1;loadOriginal();assert(ownMethod(0,0)==1024&&baseMethod==full&&originalWidth==local);
 reset();addFails=1;loadOriginal();assert(!ownExists&&baseMethod==full);
 reset();badABI=1;loadOriginal();assert(!ownExists&&baseMethod==full);
 reset();hasClass=0;loadOriginal();assert(!ownExists);
 const char*invalid[]={"","x","1024x","16385","-1","99999999999999999999999999999999999"};
 for(unsigned i=0;i<sizeof invalid/sizeof*invalid;i++){reset();configuration=invalid[i];loadOriginal();assert(!ownExists);}
 reset();configuration="0\n";loadOriginal();assert(!ownExists);
 assert(parseCap("4096\n",5)==4096&&parseCap("2048",4)==2048);
 puts("PASS: real loader policy: original always loaded, WindowServer-only cap, superclass untouched, own-method override, repeat safety, ABI/config refusal; mock runtime only");
}
'''.replace('@@SOURCE@@',source)
for name in ('dlopen','dlsym','dlerror','getprogname','open','read','close','syslog'):
 fixture=re.sub(r'\b'+name+r'\b','fixture_'+name,fixture)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(fixture)
 subprocess.run(['clang','-std=c11','-fsanitize=address,undefined','-fno-builtin',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
