#!/usr/bin/env python3
"""Stage next-boot EFI; activation is gated by the macOS shader/update script."""
from pathlib import Path
import argparse,datetime,hashlib,json,plistlib,shlex,shutil
p=argparse.ArgumentParser();p.add_argument('--media',type=Path,default=Path('/run/media/spotlight/1401'));p.add_argument('--kit',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--restore',action='store_true');a=p.parse_args()
media=a.media.resolve();kit=a.kit.resolve();efi=media/'EFI';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
if a.restore:
 plan=json.loads((kit/'plan.json').read_text());backup=media/plan['backup_efi']
 if backup.parent!=media or not backup.name.startswith('EFI-before-G6MF-Bridge-'):p.error('Invalid backup path')
 if not backup.is_dir():p.error('No bridge EFI backup to restore')
 if sha(efi/'OC/config.plist')!=plan['after_config_sha']:p.error('Current config changed; saved headless EFI retained for manual review')
 if sha(backup/'OC/config.plist')!=plan['before_config_sha']:p.error('Saved EFI config hash mismatch')
 parked=media/('EFI-after-G6MF-Bridge-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
 efi.rename(parked)
 try:backup.rename(efi)
 except BaseException:parked.rename(efi);raise
 (kit/'bridge-active.txt').unlink(missing_ok=True)
 print('Headless EFI restored. Corrected NMIntelFB remains installed but disabled by -nmintelfboff.');raise SystemExit(0)
if (kit/'plan.json').exists():p.error('A bridge plan already exists; do not replace it while testing')
before=sha(efi/'OC/config.plist');cfg=plistlib.loads((efi/'OC/config.plist').read_bytes());guid='7C436110-AB2A-4BBB-A880-FE41995C9F82'
nv=cfg['NVRAM']['Add'][guid];words=nv['boot-args'].split()
if not {'nmoptimus=1','-nmintelfboff','nvfb=1','nvaccel=1'}<=set(words):p.error('Expected the tested headless full-stack EFI')
words=[w for w in words if w!='-nmintelfboff']
if '-nvrmnoflip' not in words:words.append('-nvrmnoflip')
nv['boot-args']=' '.join(words)
delete=cfg['NVRAM'].setdefault('Delete',{}).setdefault(guid,[])
if 'boot-args' not in delete:delete.append('boot-args')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
stage=media/('EFI-G6MF-Bridge-stage-'+stamp);backup=media/('EFI-before-G6MF-Bridge-'+stamp)
shutil.copytree(efi,stage);(stage/'OC/config.plist').write_bytes(plistlib.dumps(cfg,sort_keys=False))
identity=json.loads((kit/'validation/update-identity.json').read_text())
plan={'staged_efi':stage.name,'backup_efi':backup.name,'before_config_sha':before,'after_config_sha':sha(stage/'OC/config.plist'),'old_kext_sha':identity['old_kext_sha'],'new_kext_sha':identity['new_kext_sha'],'activation_requires':'SHADER PASS and successful native Auxiliary KC update'}
(kit/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
variables={'MEDIA':'/Volumes/'+media.name,'STAGED_EFI':stage.name,'BACKUP_EFI':backup.name,'BEFORE_CONFIG_SHA':before,'AFTER_CONFIG_SHA':plan['after_config_sha'],'OLD_KEXT_SHA':plan['old_kext_sha'],'NEW_KEXT_SHA':plan['new_kext_sha']}
if 'new_accel_sha' in identity:
 variables.update(OLD_ACCEL_SHA=identity['old_accel_sha'],NEW_ACCEL_SHA=identity['new_accel_sha'])
if 'new_agdc_sha' in identity:
 variables.update(OLD_AGDC_SHA=identity['old_agdc_sha'],NEW_AGDC_SHA=identity['new_agdc_sha'])
(kit/'plan.env').write_text(''.join(k+'='+shlex.quote(v)+'\n' for k,v in variables.items()))
files=sorted(f for f in kit.rglob('*') if f.is_file() and f!=kit/'SHA256SUMS' and not f.is_symlink())
(kit/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(kit))+'\n' for f in files))
assert sha(efi/'OC/config.plist')==before
print('Bridge EFI staged only: '+str(stage))
print('Active EFI unchanged. On Tahoe run sudo bash '+variables['MEDIA']+'/'+kit.name+'/next-stage.sh')
