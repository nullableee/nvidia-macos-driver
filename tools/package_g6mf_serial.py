#!/usr/bin/env python3
"""Package a v7/v8 wrapper upgrade, without Apple or vendor driver binaries."""
from pathlib import Path
import argparse,hashlib,json,shutil,struct,subprocess,tarfile
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--v7-wrapper',type=Path,required=True);p.add_argument('--original-plugin',type=Path,required=True);p.add_argument('--map-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def text_identity(f):
 b=f.read_bytes();assert struct.unpack_from('<II',b)==(0xfeedfacf,0x1000007);q=32
 for _ in range(struct.unpack_from('<I',b,16)[0]):
  c,z=struct.unpack_from('<II',b,q)
  if c==0x19:
   for j in range(struct.unpack_from('<I',b,q+64)[0]):
    s=q+72+j*80
    if b[s:s+16].split(b'\0')[0]==b'__text':
     v,n,o=struct.unpack_from('<QQI',b,s+32);assert o+n<=len(b);return o,n,hashlib.sha256(b[o:o+n]).hexdigest()
  q+=z
 raise ValueError('Missing text section')
kit=a.out.resolve()/'NullMoth-G6MF-Bridge-v9-SerialLUT'
if kit.exists():p.error('Output kit already exists')
kit.mkdir(parents=True);(kit/'validation').mkdir()
manifest=json.loads((a.build/'build-manifest.json').read_text())
for name,kind in [('NVMTLDriver',8),('lut-probe',2),('serial-probe',2)]:
 f=a.build/name;assert sha(f)==manifest['sha256'][name];assert struct.unpack_from('<4I',f.read_bytes())[:2]==(0xfeedfacf,0x1000007);assert struct.unpack_from('<4I',f.read_bytes())[3]==kind
 shutil.copy2(f,kit/name);(kit/name).chmod(0o755)
for src,dst in [('tools/g6mf_install_serial.sh','install-serial.sh'),('tools/g6mf_rollback_lut.sh','rollback-lut.sh'),('tools/g6mf_set_serial_lut.sh','set-serial-lut.sh'),('tools/g6mf_collect_perf.sh','collect-perf.sh'),('tools/g6mf_profile_perf.sh','profile-perf.sh'),('tools/g6mf_collect_macos.sh','collect-macos.sh'),('tools/g6mf_capture_boot.sh','capture-boot.sh'),('tools/g6mf_lut_serial.c','lut-serial.c'),('tools/g6mf_lut_wrapper.c','lut-wrapper.c'),('tools/g6mf_serial_probe.c','serial-probe.c'),('docs/G6MF-SERIAL-LUT-V9-RU.md','README-RU.md'),('LICENSE','LICENSE'),('NOTICE','NOTICE')]:shutil.copy2(R/src,kit/dst)
assert sha(a.v7_wrapper)=='e8cad4a4aa91c235f30f679beec90a1b055ad806d5c7a0ab923ffd2a074fc8da'
assert sha(a.original_plugin)=='ca6a7ec9133f90d2163ac4f07234891607c33afec7ebab2700c6bae5d3cd06ff'
identity=''
for prefix,file in [('WRAPPER',a.v7_wrapper),('ORIGINAL',a.original_plugin)]:
 offset,size,digest=text_identity(file)
 identity+=f'{prefix}_TEXT_OFFSET={offset}\n{prefix}_TEXT_SIZE={size}\n{prefix}_TEXT_SHA={digest}\n'
(kit/'identity.env').write_text(identity)
shutil.copy2(a.map_probe,kit/'map-probe');(kit/'map-probe').chmod(0o755)
shutil.copy2(a.build/'build-manifest.json',kit/'validation/build-manifest.json')
for f in kit.glob('*.sh'):subprocess.run(['bash','-n',str(f)],check=True)
(kit/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(kit))+'\n' for f in sorted(kit.rglob('*')) if f.is_file() and f.name!='SHA256SUMS'))
with tarfile.open(kit.with_suffix('.tar.gz'),'w:gz') as t:t.add(kit,arcname=kit.name)
print('Packaged:',kit)
