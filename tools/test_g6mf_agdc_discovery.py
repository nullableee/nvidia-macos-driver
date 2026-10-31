#!/usr/bin/env python3
"""Check bounded production AGDC discovery scheduling, without kernel/hardware."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include "nv_agdc_discovery.h"
int main(){
 for(unsigned readyAt=1;readyAt<=20;readyAt++){
  unsigned calls=0,pauses=0;
  assert(nvAgdcAwaitTargets([]{return true;},[&]{return ++calls==readyAt;},[&]{pauses++;}));
  assert(calls==readyAt && pauses==readyAt-1);
 }
 unsigned calls=0,pauses=0;
 assert(!nvAgdcAwaitTargets([]{return true;},[&]{calls++;return false;},[&]{pauses++;}));
 assert(calls==20 && pauses==19);
 calls=pauses=0;
 assert(!nvAgdcAwaitTargets([]{return false;},[&]{calls++;return true;},[&]{pauses++;}));
 assert(calls==0 && pauses==0);
 bool wanted=true;
 assert(!nvAgdcAwaitTargets([&]{return wanted;},[&]{calls++;return false;},[&]{pauses++;wanted=false;}));
 assert(calls==1 && pauses==1);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(r/'kexts/NVRMAGDC'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: immediate/delayed discovery through last attempt, exhaustion bound and cancellation')
