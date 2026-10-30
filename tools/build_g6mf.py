#!/usr/bin/env python3
"""Build G6 MF probe and patched kexts; never installs them or modifies EFI."""
from pathlib import Path
import argparse,subprocess,sys,plistlib,json,hashlib,struct,platform,os
R=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--sdk',type=Path,required=True,help='MacKernelSDK root (Headers/ and Library/)');a.add_argument('--ogkm',type=Path,help='NVIDIA open-gpu-kernel-modules 615.78.08 source');a.add_argument('--ld',type=Path,help='cctools ld64; required on Linux (lld does not implement -kext)');a.add_argument('--out',type=Path,required=True);a.add_argument('--probe-only',action='store_true');args=a.parse_args()
sdk=args.sdk.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
if not (sdk/'Headers/IOKit/graphics/IOFramebuffer.h').exists():a.error('MacKernelSDK headers missing')
if not args.probe_only and (not args.ogkm or not (args.ogkm/'src/nvidia-modeset/kapi/interface/nvkms-kapi.h').exists()):a.error('--ogkm must point to the NVIDIA source tree')
if sys.platform!='darwin' and not args.ld:a.error('Linux requires --ld pointing to cctools ld64, not ld64.lld')
compiler=['xcrun','clang++'] if sys.platform=='darwin' else ['clang++']
common=compiler+['-target','x86_64-apple-macos15','-fapple-kext','-mkernel','-nostdinc','-I'+str(sdk/'Headers'),'-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DAPPLE','-DNeXT','-std=c++17','-fno-rtti','-fno-exceptions','-fno-builtin','-fno-common','-fno-stack-protector','-fno-use-cxa-atexit','-fno-register-global-dtors-with-atexit','-Wall','-Wno-unused-parameter','-Wno-inconsistent-missing-override','-Wno-unused-function','-O2','-g0','-ffile-prefix-map='+str(R)+'=/nullmoth']
# Recent LLVM can lower llvm.global_dtors back into __cxa_atexit calls in
# the backend, even after the frontend was told not to use an exit runtime.
# Kexts need __mod_term_func instead. Detect the backend switch for both
# Apple Clang and upstream Clang; final import validation is mandatory.
backend_switch='-disable-atexit-based-global-dtor-lowering'
feature_cmd=compiler+['-target','x86_64-apple-macos15','-mkernel','-x','c++','-c','-','-o',os.devnull,'-mllvm',backend_switch]
feature=subprocess.run(feature_cmd,input='',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'backend-options.log').write_text(feature.stdout)
if feature.returncode==0:common+=['-mllvm',backend_switch]
include_dirs=['src/nvidia/arch/nvalloc/unix/include','src/nvidia/arch/nvalloc/common/inc','src/nvidia/arch/nvalloc/common/inc/gsp','src/common/sdk/nvidia/inc','src/common/sdk/nvidia/inc/hw','src/common/inc','src/common/shared/inc','src/nvidia/inc','src/nvidia/inc/os','src/nvidia/inc/kernel','src/nvidia/kernel/inc','src/nvidia/interface','src/common/nvlink/interface','src/common/inc/swref','src/common/inc/swref/published','src/nvidia/inc/libraries','src/nvidia/src/libraries','src/nvidia/generated','src/nvidia/src/mm/uvm/interface','src/common/uproc/os/libos-v2.0.0/include','src/common/uproc/os/common/include','src/common/inc/displayport','src/common/nvlink/inband/interface','src/nvidia-modeset/os-interface/include','src/nvidia-modeset/kapi/interface','src/nvidia-modeset/kapi/include','src/common/unix/nvidia-push/interface','src/nvidia-modeset/interface','src/nvidia-modeset/include','src/common/unix/common/inc','src/common/modeset','src/common/unix/common/utils/interface']
includes=['-I'+str(args.ogkm.resolve()/p) for p in include_dirs] if args.ogkm else []
components=[('NMIntelProbe','kexts/NMIntelFB/intelprobe.cpp','kexts/NMIntelFB/Info-probe.plist',['-Ikexts/NMIntelFB'])]
if not args.probe_only:components += [
 ('NMIntelFB','kexts/NMIntelFB/intelfb.cpp','kexts/NMIntelFB/Info.plist',['-Ikexts/NMIntelFB','-Ikexts/NVRM']),
 ('NVAccel','kexts/NVRM/accel/nvrm-accel.cpp','kexts/NVRM/accel/Info.plist',includes+['-DNM_TAHOE','-Ikexts/NVRM','-Ikexts/NVRM/accel','-Ikexts/NVRM/accel/iofam','-Ikexts/NVRM/accel/re']),
 ('NVRMAGDC','kexts/NVRMAGDC/nvrm-agdc.cpp','kexts/NVRMAGDC/Info.plist',['-Ikexts/NVRMAGDC']),
 ('NVRMFB','kexts/NVRMFB/fb/nvrm-fb.cpp','kexts/NVRMFB/fb/Info.plist',includes+['-Ikexts/NVRMFB','-Ikexts/NVRMFB/fb'])]
manifest={'base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'patch':'g6mf-copy-v8','host':platform.platform(),'binaries':{},'commands':[],'hardware_validated':False,'native_kmutil_validated':False,'backend_dtor_switch':feature.returncode==0}
def run(cmd,log):
 manifest['commands'].append(cmd)
 p=subprocess.run(cmd,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 log.write_text(p.stdout)
 if p.returncode:print(p.stdout,file=sys.stderr);raise SystemExit(p.returncode)
for name,source,info,extra in components:
 obj=out/(name+'.o');bundle=out/(name+'.kext');binary=bundle/'Contents/MacOS'/name;binary.parent.mkdir(parents=True,exist_ok=True)
 run(common+extra+['-c',str(R/source),'-o',str(obj)],out/(name+'.compile.log'))
 libs=sdk/'Library/universal'
 if args.ld:
  cmd=[str(args.ld.resolve()),'-arch','x86_64','-kext','-macosx_version_min','15.0','-o',str(binary),str(obj),'-L'+str(libs),'-lkmodc++','-lkmod']
 else:
  cmd=['xcrun','clang++','-arch','x86_64','-mmacosx-version-min=15.0','-fapple-kext','-nostdlib','-Xlinker','-kext',str(obj),'-L'+str(libs),'-lkmodc++','-lkmod','-lcc_kext','-o',str(binary)]
 run(cmd,out/(name+'.link.log'))
 b=binary.read_bytes();magic,cpu,sub,kind=struct.unpack_from('<IIII',b)
 if magic!=0xfeedfacf or cpu!=0x01000007 or kind!=11:raise SystemExit('Not an x86_64 MH_KEXT_BUNDLE: '+str(binary))
 j=plistlib.loads((R/info).read_bytes());(bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(j))
 run([sys.executable,str(R/'tools/validate_g6mf_kext.py'),str(bundle)],out/(name+'.validate.log'))
 manifest['binaries'][name]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'filetype':'MH_KEXT_BUNDLE','bundle':str(bundle.relative_to(out))}
 print(name,len(b),'bytes, x86_64 kext linked')
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
