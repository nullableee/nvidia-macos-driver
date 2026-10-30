#!/usr/bin/env python3
"""Compare production copy modes across alignment, padding and protected bounds."""
from pathlib import Path
import subprocess,tempfile,re
R=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
#include "nv_muxless_copy.h"
static void check(unsigned w,unsigned h,unsigned sp,unsigned dp,unsigned sa,unsigned da){
 const uint32_t guard=0xdeadbeef;
 std::vector<uint32_t>s(sp*h+16),a(dp*h+16,guard),b=a;
 for(unsigned i=0;i<s.size();i++)s[i]=i*0x9e3779b9u+17;
 const auto saved=s;
 assert(nvMuxlessCopy(a.data()+da,dp*h*4,dp*4,s.data()+sa,sp*h*4,sp*4,w,h,false));
 assert(nvMuxlessCopy(b.data()+da,dp*h*4,dp*4,s.data()+sa,sp*h*4,sp*4,w,h,true));
 assert(a==b && s==saved);
 for(unsigned i=0;i<b.size();i++){
  bool pixel=i>=da && (i-da)/dp<h && (i-da)%dp<w;
  if(pixel)assert(b[i]==s[sa+(i-da)/dp*sp+(i-da)%dp]);
  else assert(b[i]==guard);
 }
 b.assign(b.size(),guard);const auto untouched=b;
 assert(!nvMuxlessCopy(b.data()+da,dp*h*4-1,dp*4,s.data()+sa,sp*h*4,sp*4,w,h,true));
 assert(b==untouched);
 assert(!nvMuxlessCopy(b.data()+da,dp*h*4,dp*4,s.data()+sa,sp*h*4-1,sp*4,w,h,true));
 assert(b==untouched);
}
int main(){
 for(unsigned w=1;w<=65;w++)for(unsigned pad:{0u,1u,2u,7u})
  for(unsigned sa=0;sa<2;sa++)for(unsigned da=0;da<2;da++)
   check(w,7,w+pad,w+7-pad,sa,da);
 check(1920,1200,1920,1920,0,0);
 // Exact final source/destination pixels touch a PROT_NONE boundary. A wide
 // load/store must never reach into padding or the next page for an odd tail.
 size_t page=(size_t)sysconf(_SC_PAGESIZE);
 for(unsigned w:{1u,2u,7u,8u,9u,31u,32u,33u}){
  auto*s=(uint8_t*)mmap(nullptr,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
  auto*d=(uint8_t*)mmap(nullptr,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
  assert(s!=MAP_FAILED && d!=MAP_FAILED);
  assert(!mprotect(s+page,page,PROT_NONE) && !mprotect(d+page,page,PROT_NONE));
  auto*sp=(uint32_t*)(s+page-w*4);auto*dp=(uint32_t*)(d+page-w*4);
  for(unsigned x=0;x<w;x++)sp[x]=0xabc00000+x;
  assert(nvMuxlessCopy(dp,w*4,w*4,sp,w*4,w*4,w,1,true));
  for(unsigned x=0;x<w;x++)assert(dp[x]==sp[x]);
  munmap(s,2*page);munmap(d,2*page);
 }
 puts("PASS: production 32/64-bit copy equality, row padding/alignment, odd tails, exact protected-page boundaries, short-buffer refusal and full panel image; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++17','-O2','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(R/'kexts/NVRM/accel'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)

# The production header also compiles as a freestanding Darwin kernel leaf.
# Inspect optimized output: neither SIMD/FPU registers nor runtime copy helpers.
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 (p/'kernel.cpp').write_text('#include "nv_muxless_copy.h"\nextern "C" bool checked_copy(volatile uint32_t*d, uint64_t db, uint32_t dp, const volatile uint32_t*s, uint64_t sb, uint32_t sp, uint32_t w, uint32_t h, bool wide){return nvMuxlessCopy(d,db,dp,s,sb,sp,w,h,wide);}')
 subprocess.run(['clang++','-target','x86_64-apple-macos15','-mkernel','-fapple-kext','-ffreestanding','-std=c++17','-O2','-S','-I'+str(R/'kexts/NVRM/accel'),str(p/'kernel.cpp'),'-o',str(p/'kernel.s')],check=True)
 asm=(p/'kernel.s').read_text()
 assert not re.search(r'%(?:[xyz]mm[0-9]+|mm[0-7]|st\b)',asm),asm
 assert not re.search(r'\bcallq?\b',asm),asm
 assert 'sfence' in asm and 'movq' in asm
print('PASS: optimized Darwin kernel copy uses integer registers, sfence and no runtime helper calls')
