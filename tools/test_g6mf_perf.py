#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
code=r'''
#include <cstdint>
#include <cassert>
#include <thread>
#include <vector>
static uint64_t tick;
static uint64_t mach_absolute_time(){return tick;}
static void absolutetime_to_nanoseconds(uint64_t t,uint64_t*n){*n=t*3;}
#include "nv_perf.h"
static void scopeReturn(NMPerfMetric &m){NMPerfScope sample(&m);tick+=7;return;}
int main(){
 NMPerfMetric scope{};scopeReturn(scope);
 assert(scope.count==1 && scope.ns==21 && scope.max==21);
 {NMPerfScope disabled(nullptr);tick+=100;}assert(scope.count==1);
 NMPerfMetric parallel{};std::vector<std::thread> threads;
 for(int i=1;i<=4;i++)threads.emplace_back([&parallel,i]{for(int n=0;n<10000;n++)nmPerfAdd(parallel,i);});
 for(auto&t:threads)t.join();assert(parallel.count==40000 && parallel.ns==100000 && parallel.max==4);
 uint64_t cuts[]={7000000,12000000,20000000,28000000,40000000};
 for(unsigned i=0;i<5;i++){assert(nmPerfGapBin(cuts[i]-1)==i);assert(nmPerfGapBin(cuts[i])==i+1);}
 assert(nmPerfGapBin(0)==0 && nmPerfGapBin(1000000000)==5);
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++17','-pthread','-fsanitize=address,undefined','-I'+str(R/'kexts/NVRM/accel'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: production timing accumulation, concurrent max/sum/count, early-return scope, clock conversion and histogram boundaries; CPU only')
