#!/usr/bin/env python3
"""Exercise the actual staging/activation script against disposable EFI fixtures."""
from pathlib import Path
import tempfile,plistlib,subprocess,sys,struct,json
R=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='g6mf-efi-test-') as tmp:
 base=Path(tmp);bundle=base/'NMIntelProbe.kext';(bundle/'Contents/MacOS').mkdir(parents=True)
 info=plistlib.loads((R/'kexts/NMIntelFB/Info-probe.plist').read_bytes());(bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info));(bundle/'Contents/MacOS/NMIntelProbe').write_bytes(struct.pack('<8I',0xfeedfacf,0x01000007,3,11,0,0,0,0))
 for activate in [False,True]:
  media=base/('active' if activate else 'stage');(media/'EFI/OC/Kexts').mkdir(parents=True)
  cfg={'Kernel':{'Add':[{'BundlePath':'UserDriver.kext','Enabled':True}]},'NVRAM':{'Add':{'7C436110-AB2A-4BBB-A880-FE41995C9F82':{'boot-args':'-v debug=0x100 userflag=1','csr-active-config':bytes.fromhex('03080000')}},'Delete':{}},'DeviceProperties':{'Add':{'user':'retained'}},'ACPI':{'Add':[{'Path':'User.aml','Enabled':True}]}}
  original=plistlib.dumps(cfg);(media/'EFI/OC/config.plist').write_bytes(original);(media/'EFI/keep.bin').write_bytes(b'original')
  command=[sys.executable,str(R/'tools/g6mf_prepare_probe.py'),'--media',str(media),'--bundle',str(bundle)]+(['--activate'] if activate else [])
  subprocess.run(command,check=True,stdout=subprocess.PIPE,text=True)
  records=list(media.glob('NMProbe-*.json'));assert len(records)==1;record=json.loads(records[0].read_text());path=Path(record['stage']);new=plistlib.loads((path/'OC/config.plist').read_bytes())
  assert new['Kernel']['Add'][0]==cfg['Kernel']['Add'][0]
  assert new['DeviceProperties']==cfg['DeviceProperties'] and new['ACPI']==cfg['ACPI']
  nv=new['NVRAM']['Add']['7C436110-AB2A-4BBB-A880-FE41995C9F82'];assert nv['boot-args']=='-v debug=0x100 userflag=1 nmintelprobe=1';assert nv['csr-active-config']==bytes.fromhex('03080000')
  if activate:assert (Path(record['preserved_efi'])/'OC/config.plist').read_bytes()==original
  else:assert (media/'EFI/OC/config.plist').read_bytes()==original
  assert (path/'keep.bin').read_bytes()==b'original'
  if activate:
   subprocess.run([sys.executable,str(R/'tools/g6mf_restore_probe.py'),'--media',str(media)],check=True,stdout=subprocess.PIPE,text=True)
   assert (media/'EFI/OC/config.plist').read_bytes()==original
   assert json.loads(records[0].read_text())['active'] is False
 # The earlier bad build must not be re-enabled by an old offline kit.
 oldmedia=base/'old-version';(oldmedia/'EFI/OC').mkdir(parents=True);(oldmedia/'EFI/OC/config.plist').write_bytes(original)
 oldinfo=dict(info);oldinfo['CFBundleVersion']='0.1.1'
 (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(oldinfo))
 rejected=subprocess.run([sys.executable,str(R/'tools/g6mf_prepare_probe.py'),'--media',str(oldmedia),'--bundle',str(bundle),'--activate'],capture_output=True,text=True)
 assert rejected.returncode!=0 and 'Probe 0.1.1' in rejected.stderr
 assert (oldmedia/'EFI/OC/config.plist').read_bytes()==original
 (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
 # Invalid input must not move the user's EFI.
 bad=base/'bad';(bad/'EFI/OC').mkdir(parents=True);(bad/'EFI/OC/config.plist').write_bytes(original)
 (bundle/'Contents/MacOS/NMIntelProbe').write_bytes(b'not a kext')
 p=subprocess.run([sys.executable,str(R/'tools/g6mf_prepare_probe.py'),'--media',str(bad),'--bundle',str(bundle),'--activate'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert p.returncode!=0 and (bad/'EFI/OC/config.plist').read_bytes()==original
print('PASS: stage-only, activation, original EFI preservation, unrelated config preservation, invalid binary refusal, recorded EFI restore')
