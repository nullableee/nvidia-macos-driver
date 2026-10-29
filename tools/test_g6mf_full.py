#!/usr/bin/env python3
"""Exercise real EFI activation/restoration and rollback on disposable volumes."""
from pathlib import Path
import json,os,plistlib,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='g6mf-full-test-') as d:
 d=Path(d);media=d/'media';efi=media/'EFI';(efi/'OC').mkdir(parents=True)
 guid='7C436110-AB2A-4BBB-A880-FE41995C9F82'
 cfg={'Kernel':{'Add':[{'BundlePath':n,'Enabled':True} for n in ['Lilu.kext','AMFIPass.kext','NMIntelProbe.kext']], 'Quirks':{'DisableIoMapper':True}},'NVRAM':{'Add':{guid:{'boot-args':'-v keepsyms=1 nmintelprobe=1','csr-active-config':bytes.fromhex('03080000')}},'Delete':{}},'Misc':{'Security':{'SecureBootModel':'Disabled'}},'ACPI':{'Add':[]},'Booter':{'Quirks':{'ResizeAppleGpuBars':0}}}
 original=plistlib.dumps(cfg);(efi/'OC/config.plist').write_bytes(original);(efi/'OC/sentinel').write_bytes(b'unchanged')
 cmd=['python3',str(R/'tools/g6mf_prepare_full_efi.py'),'--media',str(media)]
 subprocess.run(cmd,check=True,stdout=subprocess.PIPE)
 assert (efi/'OC/config.plist').read_bytes()==original
 subprocess.run(cmd+['--activate'],check=True,stdout=subprocess.PIPE)
 active=plistlib.loads((efi/'OC/config.plist').read_bytes())
 assert active['ACPI']==cfg['ACPI'] and active['Booter']==cfg['Booter']
 assert active['Kernel']['Quirks']==cfg['Kernel']['Quirks']
 assert {x['BundlePath'] for x in active['Kernel']['Add'] if x['Enabled']}=={'Lilu.kext','AMFIPass.kext'}
 args=active['NVRAM']['Add'][guid]['boot-args'].split()
 assert all(x in args for x in ['-v','keepsyms=1','nmoptimus=1','-nmintelfboff','nvfb=1','nvaccel=1'])
 assert active['NVRAM']['Add'][guid]['csr-active-config']==bytes.fromhex('430a0000')
 assert (efi/'OC/sentinel').read_bytes()==b'unchanged'
 changed=(efi/'OC/config.plist').read_bytes();(efi/'OC/config.plist').write_bytes(original)
 refusal=subprocess.run(cmd+['--restore'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert refusal.returncode!=0 # refuse to discard an intervening config edit
 (efi/'OC/config.plist').write_bytes(changed)
 subprocess.run(cmd+['--restore'],check=True,stdout=subprocess.PIPE)
 assert (efi/'OC/config.plist').read_bytes()==original
 print('PASS: full EFI stages without mutation, activates headless profile, preserves BAR/ACPI, restores bytes and refuses changed config')
 # Substitute only command resolution; exercise the production rollback logic
 # against a temporary Data volume. No /Library paths on the host are touched.
 bin=d/'bin';bin.mkdir()
 for name,text in {'id':'echo 0','ditto':'cp -a "$1" "$2"','sync':'exit 0'}.items():
  f=bin/name;f.write_text('#!/bin/bash\n'+text+'\n');f.chmod(0o755)
 script=(R/'tools/g6mf_rollback_full.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;')
 rollback=d/'rollback.sh';rollback.write_text(script)
 volume=d/'Data';(volume/'Library/Extensions').mkdir(parents=True)
 keep=volume/'Library/Extensions/NMXGPU.kext';keep.mkdir();(keep/'data').write_bytes(b'keep Intel')
 target=volume/'Library/Extensions/NMIntelFB.kext';target.mkdir();(target/'data').write_bytes(b'new')
 backup=d/'backup';saved=backup/'files/Library/GPUBundles/nvmtl';saved.mkdir(parents=True);(saved/'old').write_bytes(b'previous userland')
 (backup/'READY').touch();(backup/'present.txt').write_text('Library/GPUBundles/nvmtl\n')
 bad=(backup/'present.txt').read_text();(backup/'present.txt').write_text('Library/Extensions/NVRM.kext\n')
 result=subprocess.run(['bash',str(rollback),str(backup),str(volume)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert result.returncode!=0 and target.exists() # fail before any removal
 (backup/'present.txt').write_text(bad)
 subprocess.run(['bash',str(rollback),str(backup),str(volume)],check=True,stdout=subprocess.PIPE)
 assert not target.exists()
 assert (volume/'Library/GPUBundles/nvmtl/old').read_bytes()==b'previous userland'
 assert (keep/'data').read_bytes()==b'keep Intel'
 assert (backup/'READY').exists()
 print('PASS: rollback restores saved shared userland, removes newly added bridge, preserves Intel kext and refuses incomplete backup before mutation')
for name in ['g6mf_install_full.sh','g6mf_rollback_full.sh','g6mf_collect_full.sh']:
 subprocess.run(['bash','-n',str(R/'tools'/name)],check=True)
print('PASS: shell syntax')
