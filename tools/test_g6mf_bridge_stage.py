#!/usr/bin/env python3
"""Exercise shader gating and actual EFI rename/restore on disposable media."""
from pathlib import Path
import hashlib,json,os,plistlib,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def manifest(kit):
 (kit/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(kit))+'\n' for f in sorted(kit.rglob('*')) if f.is_file() and f!=kit/'SHA256SUMS'))
with tempfile.TemporaryDirectory(prefix='g6mf-bridge-tests-') as d:
 d=Path(d);bin=d/'bin';bin.mkdir()
 for n,s in {'id':'echo 0','uname':'echo Darwin','sleep':'exit 0','sync':'exit 0'}.items():
  f=bin/n;f.write_text('#!/bin/bash\n'+s+'\n');f.chmod(0o755)
 checksum=bin/'shasum';checksum.write_text('''#!/usr/bin/python3
import hashlib,sys
from pathlib import Path
a=sys.argv[1:]
if '-c' in a:
 for line in Path(a[a.index('-c')+1]).read_text().splitlines():
  expected,name=line.split('  ',1)
  if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:sys.exit(1)
else:
 f=Path(a[-1]);print(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f))
''');checksum.chmod(0o755)
 for mode in ('shader-fail','missing-marker','install-fail','efi-changed','capture-install-fail','pass'):
  media=d/mode;kit=media/'kit';(kit/'validation').mkdir(parents=True);(media/'EFI/OC').mkdir(parents=True)
  guid='7C436110-AB2A-4BBB-A880-FE41995C9F82'
  cfg={'NVRAM':{'Add':{guid:{'boot-args':'-v nmoptimus=1 nvfb=1 nvaccel=1 -nmintelfboff'}},'Delete':{}},'ACPI':{'sentinel':'keep'},'Booter':{'Quirks':{'ResizeAppleGpuBars':0}}}
  old=plistlib.dumps(cfg);(media/'EFI/OC/config.plist').write_bytes(old)
  (kit/'validation/update-identity.json').write_text(json.dumps({'old_kext_sha':'old','new_kext_sha':'new'}))
  prepare=['python3',str(R/'tools/g6mf_prepare_bridge.py'),'--media',str(media),'--kit',str(kit)]
  subprocess.run(prepare,check=True,stdout=subprocess.PIPE)
  assert (media/'EFI/OC/config.plist').read_bytes()==old
  env=kit/'plan.env';env.write_text('\n'.join('MEDIA='+str(media) if l.startswith('MEDIA=') else l for l in env.read_text().splitlines())+'\n')
  source=(R/'tools/g6mf_next_stage.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;')
  (kit/'next-stage.sh').write_text(source)
  shader='echo SHADER PASS: mock-compute;exit 0'
  if mode=='shader-fail':shader='echo FAIL shader;exit 1'
  if mode=='missing-marker':shader='echo no-pass-marker;exit 0'
  (kit/'shader-probe').write_text('#!/bin/bash\n'+shader+'\n')
  (kit/'collect-macos.sh').write_text('#!/bin/bash\ntouch "$1/collected"\n')
  update='touch "$(dirname "$0")/updated"'
  if mode=='install-fail':update='exit 37'
  if mode=='efi-changed':update+='\nprintf changed >> "'+str(media)+'/EFI/OC/config.plist"'
  (kit/'install-bridge-update.sh').write_text('#!/bin/bash\n'+update+'\n')
  if mode=='capture-install-fail':(kit/'capture-boot.sh').write_text('#!/bin/bash\nexit 41\n')
  manifest(kit)
  result=subprocess.run(['bash',str(kit/'next-stage.sh')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  assert (result.returncode==0)==(mode=='pass'),(mode,result.stdout)
  assert any(kit.glob('next-*/collected')),(mode,'shader and collection must actually run',result.stdout)
  plan=json.loads((kit/'plan.json').read_text())
  if mode=='pass':
   assert (kit/'updated').exists() and (media/plan['backup_efi']).is_dir()
   active=plistlib.loads((media/'EFI/OC/config.plist').read_bytes())
   args=active['NVRAM']['Add'][guid]['boot-args'].split()
   assert '-nmintelfboff' not in args and '-nvrmnoflip' in args
   assert active['ACPI']==cfg['ACPI'] and active['Booter']==cfg['Booter']
   subprocess.run(prepare+['--restore'],check=True,stdout=subprocess.PIPE)
   assert (media/'EFI/OC/config.plist').read_bytes()==old
  else:
   assert not (media/plan['backup_efi']).exists()
   if mode!='efi-changed':assert (media/'EFI/OC/config.plist').read_bytes()==old
   if mode in ('shader-fail','missing-marker','install-fail'):assert not (kit/'updated').exists()
  print('PASS: bridge transition',mode)
 # The production Recovery restore must preserve every unrelated kext.
 root=d/'Data';(root/'Library/Extensions/NVAccel.kext').mkdir(parents=True);(root/'Library/KernelCollections').mkdir()
 (root/'Library/Extensions/NMIntelFB.kext').mkdir();(root/'Library/Extensions/NMIntelFB.kext/new').touch()
 (root/'Library/KernelCollections/AuxiliaryKernelExtensions.kc').write_bytes(b'new-kc')
 backup=d/'backup';(backup/'NMIntelFB.kext/Contents').mkdir(parents=True);(backup/'NMIntelFB.kext/Contents/Info.plist').write_bytes(b'old-fb')
 (backup/'AuxiliaryKernelExtensions.kc').write_bytes(b'old-kc');(backup/'READY').touch()
 ditto=bin/'ditto';ditto.write_text('#!/bin/bash\ncp -a "$1" "$2"\n');ditto.chmod(0o755)
 rollback=d/'rollback.sh';rollback.write_text((R/'tools/g6mf_rollback_bridge.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;'))
 subprocess.run(['bash',str(rollback),str(backup),str(root)],check=True,stdout=subprocess.PIPE)
 assert (root/'Library/Extensions/NVAccel.kext').is_dir()
 assert (root/'Library/Extensions/NMIntelFB.kext/Contents/Info.plist').read_bytes()==b'old-fb'
 assert (root/'Library/KernelCollections/AuxiliaryKernelExtensions.kc').read_bytes()==b'old-kc'
 print('PASS: Recovery bridge rollback restores only framebuffer and KC')
 # Run the real installer against a disposable filesystem, substituting only
 # macOS command resolution and absolute system locations. kmutil cannot run
 # on Linux, so its success/missing-module/failure outcomes are injected.
 for n,s in {'chown':'exit 0','stat':'echo 0:700','sw_vers':'if [ "$1" = -productVersion ]; then echo 26.7.1; else echo 25G241; fi'}.items():
  f=bin/n;f.write_text('#!/bin/bash\n'+s+'\n');f.chmod(0o755)
 kmutil=bin/'kmutil';kmutil.write_text('''#!/usr/bin/python3
import os,sys
from pathlib import Path
a=sys.argv[1:];mode=os.environ['KMUTIL_CASE'];candidate=Path(a[a.index('-A')+1])
if a[0]=='create':
 live=candidate.name=='live.kc'
 if mode=='test-fail' or (mode=='live-fail' and live):sys.exit(1)
 candidate.write_bytes(b'new-kc')
else:
 for n in ('NVRM','NVAccel','NVRMFB','NVRMAGDC','NMIntelFB'):
  if not (mode=='missing-module' and n=='NMIntelFB'):print('com.nullmoth.'+n)
''');kmutil.chmod(0o755)
 for mode in ('success','test-fail','missing-module','live-fail','pair-success','pair-live-fail','agdc-success','agdc-live-fail'):
  system=d/('install-'+mode);ext=system/'Library/Extensions';kc=system/'Library/KernelCollections/AuxiliaryKernelExtensions.kc';base=system/'Users/Shared/G6MF-Backups';kit=system/'kit'
  (ext/'NMIntelFB.kext/Contents/MacOS').mkdir(parents=True);kc.parent.mkdir();base.mkdir(parents=True);kit.mkdir()
  (ext/'NMIntelFB.kext/Contents/Info.plist').write_bytes(b'old-info');(ext/'NMIntelFB.kext/Contents/MacOS/NMIntelFB').write_bytes(b'old-fb');kc.write_bytes(b'old-kc')
  (ext/'NVAccel.kext').mkdir();(ext/'NVAccel.kext/sentinel').write_bytes(b'untouched')
  (kit/'NMIntelFB.kext/Contents/MacOS').mkdir(parents=True);(kit/'NMIntelFB.kext/Contents/MacOS/NMIntelFB').write_bytes(b'new-fb');(kit/'NMIntelFB.kext/Contents/Info.plist').write_bytes(b'new-info')
  paired=mode.startswith(('pair-','agdc-'))
  agdc=mode.startswith('agdc-')
  if paired:
   (ext/'NVAccel.kext/Contents/MacOS').mkdir(parents=True);(ext/'NVAccel.kext/Contents/Info.plist').write_bytes(b'old-info');(ext/'NVAccel.kext/Contents/MacOS/NVAccel').write_bytes(b'old-accel')
   (kit/'NVAccel.kext/Contents/MacOS').mkdir(parents=True);(kit/'NVAccel.kext/Contents/Info.plist').write_bytes(b'new-info');(kit/'NVAccel.kext/Contents/MacOS/NVAccel').write_bytes(b'new-accel')
   cache=system/'Library/NullMoth/kexts/26';cache.mkdir(parents=True);(cache/'sentinel').write_bytes(b'old-cache')
  (kit/'plan.env').write_text('OLD_KEXT_SHA='+sha(ext/'NMIntelFB.kext/Contents/MacOS/NMIntelFB')+'\nNEW_KEXT_SHA='+sha(kit/'NMIntelFB.kext/Contents/MacOS/NMIntelFB')+'\n')
  if paired:
   with (kit/'plan.env').open('a') as f:f.write('OLD_ACCEL_SHA='+sha(ext/'NVAccel.kext/Contents/MacOS/NVAccel')+'\nNEW_ACCEL_SHA='+sha(kit/'NVAccel.kext/Contents/MacOS/NVAccel')+'\n')
  if agdc:
   for container,body in [(ext,b'old-agdc'),(kit,b'new-agdc')]:
    (container/'NVRMAGDC.kext/Contents/MacOS').mkdir(parents=True);(container/'NVRMAGDC.kext/Contents/Info.plist').write_bytes(b'info');(container/'NVRMAGDC.kext/Contents/MacOS/NVRMAGDC').write_bytes(body)
   with (kit/'plan.env').open('a') as f:f.write('OLD_AGDC_SHA='+sha(ext/'NVRMAGDC.kext/Contents/MacOS/NVRMAGDC')+'\nNEW_AGDC_SHA='+sha(kit/'NVRMAGDC.kext/Contents/MacOS/NVRMAGDC')+'\n')
  for source,dest in [('g6mf_install_bridge.sh','install-bridge-update.sh'),('g6mf_rollback_bridge.sh','rollback-bridge-macos.sh')]:
   code=(R/'tools'/source).read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;')
   code=code.replace('/Library',str(system)+'/Library').replace('/Users/Shared/G6MF-Backups',str(base))
   (kit/dest).write_text(code)
  manifest(kit)
  env=dict(os.environ,KMUTIL_CASE=mode.removeprefix('pair-').removeprefix('agdc-'))
  success=mode in ('success','pair-success','agdc-success')
  result=subprocess.run(['bash',str(kit/'install-bridge-update.sh')],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  assert (result.returncode==0)==success,(mode,result.stdout)
  expected=b'new-fb' if success else b'old-fb'
  assert (ext/'NMIntelFB.kext/Contents/MacOS/NMIntelFB').read_bytes()==expected,(mode,result.stdout)
  assert kc.read_bytes()==(b'new-kc' if success else b'old-kc'),(mode,result.stdout)
  if not (paired and success):assert (ext/'NVAccel.kext/sentinel').read_bytes()==b'untouched'
  if paired:
   assert (ext/'NVAccel.kext/Contents/MacOS/NVAccel').read_bytes()==(b'new-accel' if success else b'old-accel')
   if not success:assert (cache/'sentinel').read_bytes()==b'old-cache'
  if agdc:assert (ext/'NVRMAGDC.kext/Contents/MacOS/NVRMAGDC').read_bytes()==(b'new-agdc' if success else b'old-agdc')
  if mode in ('success','live-fail'):assert list(base.glob('before-bridge-*/READY'))
  print('PASS: production bridge installer',mode)
for name in ['g6mf_next_stage.sh','g6mf_install_bridge.sh','g6mf_rollback_bridge.sh','g6mf_collect_bridge.sh']:
 subprocess.run(['bash','-n',str(R/'tools'/name)],check=True)
