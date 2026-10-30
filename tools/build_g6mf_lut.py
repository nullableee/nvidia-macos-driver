#!/usr/bin/env python3
"""Build the C-only Metal loader experiment and test probe, without Apple SDK headers."""
from pathlib import Path
import argparse,subprocess,sys,json,hashlib
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--serial',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
cc=['xcrun','clang'] if sys.platform=='darwin' else ['clang']
symbols='_dlopen _dlsym _dlerror _getprogname _setprogname _strcmp _syslog _open _read _close _printf _puts _fflush _usleep _alarm _strstr ___stack_chk_fail ___stack_chk_guard dyld_stub_binder __NSConcreteGlobalBlock'.split()
(out/'libSystem.tbd').write_text('--- !tapi-tbd-v2\narchs: [ x86_64 ]\nplatform: macosx\ninstall-name: /usr/lib/libSystem.B.dylib\ncurrent-version: 1351.0.0\ncompatibility-version: 1.0.0\nexports:\n  - archs: [ x86_64 ]\n    symbols: [ '+', '.join(symbols)+' ]\n...\n')
commands=[]
serial_obj=[]
if a.serial:
 cmd=cc+['-target','x86_64-apple-macos15','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-c',str(R/'tools/g6mf_lut_serial.c'),'-o',str(out/'serial.o')];commands.append(cmd);subprocess.run(cmd,check=True);serial_obj=[str(out/'serial.o')]
products= [('NVMTLDriver','g6mf_lut_wrapper.c',[]),('lut-probe','g6mf_metal_probe.c',['-DG6MF_SHADER_PROBE','-DG6MF_LUT_PROBE'])]
if a.serial:products.append(('serial-probe','g6mf_serial_probe.c',['-fblocks']))
for name,source,flags in products:
 cmd=cc+['-target','x86_64-apple-macos15','-O2','-Wall','-Wextra','-Werror','-fno-builtin',*flags,*(['-DG6MF_SERIAL_LUT'] if a.serial and name=='NVMTLDriver' else []),'-c',str(R/'tools'/source),'-o',str(out/(name+'.o'))];commands.append(cmd);subprocess.run(cmd,check=True)
 if sys.platform=='darwin':cmd=cc+['-arch','x86_64','-mmacosx-version-min=15.0',*(['-bundle'] if name=='NVMTLDriver' else []),str(out/(name+'.o')),* (serial_obj if name=='NVMTLDriver' else []),'-o',str(out/name)]
 else:cmd=['ld64.lld','-arch','x86_64',*(['-bundle'] if name=='NVMTLDriver' else []),'-platform_version','macos','15.0','15.0','-o',str(out/name),str(out/(name+'.o')),* (serial_obj if name=='NVMTLDriver' else []),'-L'+str(out),'-lSystem']
 commands.append(cmd);subprocess.run(cmd,check=True)
(out/'build-manifest.json').write_text(json.dumps({'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True).strip()),'serial_lut':a.serial,'commands':commands,'hardware_validated':False,'sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in [x[0] for x in products]}},indent=2)+'\n')
print('Built original-plugin loader and separate WindowServer-policy Metal probe:',out)
