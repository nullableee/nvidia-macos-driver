#!/usr/bin/env python3
"""Stage a complete preserved EFI profile; driver kexts load from AuxKC only."""
from pathlib import Path
import argparse,datetime,hashlib,json,plistlib,shutil
p=argparse.ArgumentParser()
p.add_argument('--media',type=Path,default=Path('/run/media/spotlight/1401'))
p.add_argument('--activate',action='store_true')
p.add_argument('--restore',action='store_true')
a=p.parse_args();media=a.media.resolve();efi=media/'EFI'
digest=lambda b:hashlib.sha256(b).hexdigest()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
if a.restore:
 for record in sorted(media.glob('G6MF-Full-*.json'),reverse=True):
  j=json.loads(record.read_text())
  if not j.get('active'):continue
  backup=media/j['backup']
  if backup.parent!=media or not backup.name.startswith('EFI-before-G6MF-Full-'):p.error('Invalid EFI backup record')
  if not (backup/'OC/config.plist').is_file():p.error('Saved EFI is missing')
  if digest((efi/'OC/config.plist').read_bytes())!=j['config_sha256']:p.error('EFI config changed since activation; saved original retained for manual review')
  parked=media/('EFI-after-G6MF-Full-'+stamp)
  efi.rename(parked)
  try:backup.rename(efi)
  except BaseException:parked.rename(efi);raise
  j['active']=False;j['restored']=True;record.write_text(json.dumps(j,indent=2)+'\n')
  print('Previous EFI restored; test EFI retained at '+str(parked));break
 else:p.error('No active full-test EFI record')
 raise SystemExit(0)
original=(efi/'OC/config.plist').read_bytes();cfg=plistlib.loads(original)
add=cfg['Kernel']['Add']
required={'Lilu.kext','AMFIPass.kext'}
enabled={x.get('BundlePath') for x in add if x.get('Enabled')}
if not required<=enabled:p.error('Enabled Lilu and AMFIPass required; nothing changed')
driver_names={'NVRM.kext','NVAccel.kext','NVRMFB.kext','NVRMAGDC.kext','NMIntelFB.kext'}
if driver_names & enabled:p.error('NullMoth injection already configured; AuxKC must not duplicate EFI injection')
for x in add:
 if x.get('BundlePath')=='NMIntelProbe.kext':x['Enabled']=False
guid='7C436110-AB2A-4BBB-A880-FE41995C9F82'
nv=cfg['NVRAM']['Add'].setdefault(guid,{})
replace={'nvfb','nvaccel','nvfbheads','nmoptimus','nmintelprobe','amfi_get_out_of_my_way','amfi','ipc_control_port_options'}
words=[w for w in nv.get('boot-args','').split() if w.split('=')[0] not in replace and w not in ('nv_disable=1','-wegnoegpu','-nvaccelnoheadless','-nmintelfboff')]
words+=['nvfb=1','nvaccel=1','nvfbheads=4','-nvkmsnosmooth','nmoptimus=1','-nmintelfboff','amfi_get_out_of_my_way=0x1','amfi=0x80','ipc_control_port_options=0']
if 'WhateverGreen.kext' in enabled:words=[w for w in words if not w.startswith('gfxrst=')]+['gfxrst=4']
nv['boot-args']=' '.join(dict.fromkeys(words))
sip=nv.get('csr-active-config',bytes(4))
if not isinstance(sip,bytes) or len(sip)!=4:p.error('Expected four-byte csr-active-config')
nv['csr-active-config']=(int.from_bytes(sip,'little')|0x0a43).to_bytes(4,'little')
delete=cfg['NVRAM'].setdefault('Delete',{}).setdefault(guid,[])
for key in ('boot-args','csr-active-config'):
 if key not in delete:delete.append(key)
cfg['Misc']['Security']['SecureBootModel']='Disabled'
new=plistlib.dumps(cfg,sort_keys=False)
stage=media/('EFI-G6MF-Full-stage-'+stamp);backup=media/('EFI-before-G6MF-Full-'+stamp)
shutil.copytree(efi,stage);(stage/'OC/config.plist').write_bytes(new)
assert plistlib.loads((stage/'OC/config.plist').read_bytes())==cfg
record={'active':a.activate,'backup':backup.name if a.activate else None,'stage':stage.name,'config_sha256':digest(new),'original_config_sha256':digest(original),'mode':'NVIDIA headless first; -nmintelfboff keeps firmware Intel display'}
if a.activate:
 efi.rename(backup)
 try:stage.rename(efi)
 except BaseException:backup.rename(efi);raise
 record['stage']='EFI'
(media/('G6MF-Full-'+stamp+'.json')).write_text(json.dumps(record,indent=2)+'\n')
print(('Activated' if a.activate else 'Staged only')+': '+str(media/record['stage']))
print('First test: RTX/Metal offscreen; Intel bridge disabled by -nmintelfboff.')
print('boot-args: '+nv['boot-args'])
print('csr-active-config: '+nv['csr-active-config'].hex()+'; no BAR/ACPI changes; no driver injection added.')
if a.activate:print('Previous EFI: '+str(backup))
