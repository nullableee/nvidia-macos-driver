#!/usr/bin/env python3
from pathlib import Path
import argparse,shutil,hashlib,json,struct,subprocess,tarfile
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--map-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
kit=a.out.resolve()/'NullMoth-G6MF-Bridge-v7-LUT'
if kit.exists():p.error('Kit directory already exists')
kit.mkdir(parents=True);(kit/'validation').mkdir()
for name,kind in [('NVMTLDriver',8),('lut-probe',2)]:
 f=a.build/name;assert struct.unpack_from('<4I',f.read_bytes())[:2]==(0xfeedfacf,0x1000007);assert struct.unpack_from('<4I',f.read_bytes())[3]==kind
 shutil.copy2(f,kit/name);(kit/name).chmod(0o755)
for src,dst in [('tools/g6mf_install_lut.sh','install-lut.sh'),('tools/g6mf_rollback_lut.sh','rollback-lut.sh'),('tools/g6mf_set_lut_limit.sh','set-lut-limit.sh'),('tools/g6mf_collect_perf.sh','collect-perf.sh'),('tools/g6mf_profile_perf.sh','profile-perf.sh'),('tools/g6mf_collect_macos.sh','collect-macos.sh'),('tools/g6mf_capture_boot.sh','capture-boot.sh'),('tools/g6mf_lut_wrapper.c','lut-wrapper.c'),('tools/g6mf_metal_probe.c','metal-probe.c'),('docs/G6MF-LUT-V7-RU.md','README-RU.md'),('LICENSE','LICENSE'),('NOTICE','NOTICE')]:shutil.copy2(R/src,kit/dst)
shutil.copy2(a.map_probe,kit/'map-probe');(kit/'map-probe').chmod(0o755)
shutil.copy2(a.build/'build-manifest.json',kit/'validation/build-manifest.json')
(kit/'identity.env').write_text('ORIGINAL_PLUGIN_SHA=ca6a7ec9133f90d2163ac4f07234891607c33afec7ebab2700c6bae5d3cd06ff\n')
for script in kit.glob('*.sh'):subprocess.run(['bash','-n',str(script)],check=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
(kit/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(kit))+'\n' for f in sorted(kit.rglob('*')) if f.is_file() and f.name!='SHA256SUMS'))
with tarfile.open(kit.with_suffix('.tar.gz'),'w:gz') as t:t.add(kit,arcname=kit.name)
print('Packaged:',kit)
