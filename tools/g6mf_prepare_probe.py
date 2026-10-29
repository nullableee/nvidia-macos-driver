#!/usr/bin/env python3
"""Prepare/activate a copy of the user's EFI with ONLY the read-only Intel probe."""
from pathlib import Path
import argparse,plistlib,shutil,datetime,json,hashlib,struct
p=argparse.ArgumentParser();p.add_argument('--media',type=Path,default=Path('/run/media/spotlight/1401'));p.add_argument('--activate',action='store_true');p.add_argument('--bundle',type=Path);args=p.parse_args()
media=args.media.resolve();efi=media/'EFI';config=efi/'OC/config.plist'
kit=Path(__file__).resolve().parent
bundle=(args.bundle or kit/'probe/NMIntelProbe.kext').resolve()
if not config.is_file():p.error('EFI/OC/config.plist missing on '+str(media))
info=plistlib.loads((bundle/'Contents/Info.plist').read_bytes());binary=bundle/'Contents/MacOS'/info['CFBundleExecutable'];b=binary.read_bytes()
magic,cpu,sub,kind=struct.unpack_from('<IIII',b)
if (magic,cpu,kind)!=(0xfeedfacf,0x01000007,11):p.error('probe binary is not MH_KEXT_BUNDLE')
if info.get('CFBundleVersion')=='0.1.1':p.error('Probe 0.1.1 was rejected by OpenCore; use rebuilt 0.1.2 or later')
if info['CFBundleIdentifier']!='com.nullmoth.NMIntelProbe' or set(info['IOKitPersonalities'])!={'NMIntelProbe'}:p.error('expected probe-only personality')
original=config.read_bytes();cfg=plistlib.loads(original)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
stage=media/('EFI-NMProbe-stage-'+stamp)
backup=media/('EFI-before-NMProbe-'+stamp)
if stage.exists() or backup.exists():p.error('timestamp collision; retry after one second')
shutil.copytree(efi,stage)
dest=stage/'OC/Kexts/NMIntelProbe.kext'
if dest.exists():shutil.rmtree(dest)
shutil.copytree(bundle,dest)
add=cfg['Kernel']['Add']
add[:]=[x for x in add if x.get('BundlePath')!='NMIntelProbe.kext']
add.append({'Arch':'x86_64','BundlePath':'NMIntelProbe.kext','Comment':'G6 MF read-only Intel scanout probe g6mf-v1','Enabled':True,'ExecutablePath':'Contents/MacOS/NMIntelProbe','MinKernel':'25.0.0','MaxKernel':'25.99.99','PlistPath':'Contents/Info.plist'})
guid='7C436110-AB2A-4BBB-A880-FE41995C9F82';nv=cfg['NVRAM']['Add'].setdefault(guid,{})
words=[w for w in nv.get('boot-args','').split() if not w.startswith('nmintelprobe=')];words.append('nmintelprobe=1');nv['boot-args']=' '.join(words)
delete=cfg['NVRAM'].setdefault('Delete',{}).setdefault(guid,[])
if 'boot-args' not in delete:delete.append('boot-args')
new=plistlib.dumps(cfg,sort_keys=False);(stage/'OC/config.plist').write_bytes(new)
# Read back the exact staged plist/binary; do not claim this replaces ocvalidate.
assert plistlib.loads((stage/'OC/config.plist').read_bytes())==cfg
assert (dest/'Contents/MacOS/NMIntelProbe').read_bytes()==b
record={'active':args.activate,'version':'g6mf-v1','original_config_sha256':hashlib.sha256(original).hexdigest(),'probe_config_sha256':hashlib.sha256(new).hexdigest(),'probe_sha256':hashlib.sha256(b).hexdigest(),'preserved_efi':str(backup) if args.activate else None,'stage':str(stage)}
if args.activate:
 efi.rename(backup)
 try:stage.rename(efi)
 except BaseException:
  backup.rename(efi);raise
 record['stage']=str(efi)
(media/('NMProbe-'+stamp+'.json')).write_text(json.dumps(record,indent=2)+'\n')
print('Probe EFI: '+record['stage'])
if args.activate:print('Original EFI preserved: '+str(backup))
else:print('Staged only. Use --activate to select this EFI for the next boot.')
print('Only NMIntelProbe.kext and nmintelprobe=1 were added. Graphics drivers and macOS volumes were not changed.')
