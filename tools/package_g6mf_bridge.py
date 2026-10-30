#!/usr/bin/env python3
"""Package shader-gated bridge update; customer EFI is staged separately."""
from pathlib import Path
import argparse,hashlib,json,plistlib,shutil,struct,subprocess,sys,tarfile
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--shader-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--map-probe',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
m=json.loads((a.build/'build-manifest.json').read_text());bundle=a.build/'NMIntelFB.kext';binary=bundle/'Contents/MacOS/NMIntelFB'
assert sha(binary)==m['binaries']['NMIntelFB']['sha256']
version=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())['CFBundleVersion']
assert version in ('0.1.3','0.1.4')
perf=version=='0.1.4'
assert struct.unpack_from('<4I',a.shader_probe.read_bytes())[:2]==(0xfeedfacf,0x01000007)
assert struct.unpack_from('<4I',a.shader_probe.read_bytes())[3]==2
subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py'),str(bundle)],check=True)
kit=a.out.resolve()/('NullMoth-G6MF-Bridge-v6-Perf' if perf else 'NullMoth-G6MF-Bridge-v5')
if kit.exists():p.error('Kit directory exists; choose fresh output')
kit.mkdir(parents=True);(kit/'validation').mkdir()
shutil.copytree(bundle,kit/bundle.name)
accel=a.build/'NVAccel.kext'
assert sha(accel/'Contents/MacOS/NVAccel')==m['binaries']['NVAccel']['sha256']
subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py'),str(accel)],check=True)
shutil.copytree(accel,kit/accel.name)
agdc=a.build/'NVRMAGDC.kext'
assert sha(agdc/'Contents/MacOS/NVRMAGDC')==m['binaries']['NVRMAGDC']['sha256']
subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py'),str(agdc)],check=True)
shutil.copytree(agdc,kit/agdc.name)
for src,dst in [('tools/g6mf_prepare_bridge.py','prepare-bridge.py'),('tools/g6mf_next_stage.sh','next-stage.sh'),('tools/g6mf_install_bridge.sh','install-bridge-update.sh'),('tools/g6mf_rollback_bridge.sh','rollback-bridge-macos.sh'),('tools/g6mf_collect_bridge.sh','collect-bridge.sh'),('tools/g6mf_collect_macos.sh','collect-macos.sh'),('tools/g6mf_metal_probe.c','metal-probe.c'),('tools/g6mf_capture_boot.sh','capture-boot.sh'),('tools/g6mf_iop_map_probe.c','map-probe.c'),('docs/G6MF-BRIDGE-V5-RU.md','README-RU.md'),('LICENSE','LICENSE'),('NOTICE','NOTICE')]:shutil.copy2(R/src,kit/dst)
installer=kit/'install-bridge-update.sh'
installer.write_text(installer.read_text().replace('case "$(sw_vers -productVersion)"', '[ "$(sw_vers -buildVersion)" = 25G241 ] || { echo "This patch was checked only against Tahoe 25G241."; exit 1; }\ncase "$(sw_vers -productVersion)"'))
shutil.copy2(a.shader_probe,kit/'shader-probe');(kit/'shader-probe').chmod(0o755)
assert struct.unpack_from('<4I',a.map_probe.read_bytes())[:2]==(0xfeedfacf,0x01000007)
assert struct.unpack_from('<4I',a.map_probe.read_bytes())[3]==2
shutil.copy2(a.map_probe,kit/'map-probe');(kit/'map-probe').chmod(0o755)
identity={'name':'G6MF bridge v5','base':m['base'],'old_kext_sha':'1f0b7618698919c0e874f926f77e83aff3831e6c6d02350b4e5a982e9a4e011d','new_kext_sha':sha(binary),'old_accel_sha':'ab6dd6315ad5e24ceffb9d0fef4a54d91bcbc2bfcfd67aca0806eec3455eebcb','new_accel_sha':sha(accel/'Contents/MacOS/NVAccel'),'old_agdc_sha':'ffedc0ce0596aaab8076c3034b86f82024078ef67e1e02383eb951fceebf519d','new_agdc_sha':sha(agdc/'Contents/MacOS/NVRMAGDC'),'shader_probe_sha':sha(a.shader_probe),'fix':'CPU-only Intel scanout memory activates the family pipe without NVIDIA GPU mapping','shader_hardware_validated':False,'scanout_hardware_validated':False}
if perf:
 identity.update(name='G6MF performance diagnostics v6',old_accel_sha='7e397e85b614382a83861f780a394fb2eb49210b2085acd48d1bb9a821ee8cf4',fix='read-only timing counters on the working v5 display path')
 shutil.copy2(R/'tools/g6mf_install_perf.sh',kit/'install-perf.sh')
 shutil.copy2(R/'tools/g6mf_collect_perf.sh',kit/'collect-perf.sh')
 shutil.copy2(R/'tools/g6mf_profile_perf.sh',kit/'profile-perf.sh')
 shutil.copy2(R/'docs/G6MF-PERF-V6-RU.md',kit/'README-RU.md')
 for unused in ('next-stage.sh','prepare-bridge.py'):(kit/unused).unlink()
 variables={'OLD_KEXT_SHA':identity['old_kext_sha'],'NEW_KEXT_SHA':identity['new_kext_sha'],'OLD_ACCEL_SHA':identity['old_accel_sha'],'NEW_ACCEL_SHA':identity['new_accel_sha'],'OLD_AGDC_SHA':identity['old_agdc_sha'],'NEW_AGDC_SHA':identity['new_agdc_sha']}
 (kit/'plan.env').write_text(''.join(k+'='+v+'\n' for k,v in variables.items()))
(kit/'validation/update-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
shutil.copy2(a.build/'build-manifest.json',kit/'validation/build-manifest.json')
for name in ('NMIntelFB','NVAccel','NVRMAGDC'):
 for f in a.build.glob(name+'.*.log'):shutil.copy2(f,kit/'validation'/f.name)
(kit/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(kit))+'\n' for f in sorted(kit.rglob('*')) if f.is_file() and f!=kit/'SHA256SUMS'))
archive=kit.with_suffix('.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6) as t:t.add(kit,arcname=kit.name)
(kit.parent/'SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n')
print('Packaged:',kit)
