#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,datetime
p=argparse.ArgumentParser();p.add_argument('--media',type=Path,default=Path('/run/media/spotlight/1401'));a=p.parse_args();media=a.media.resolve()
for f in sorted(media.glob('NMProbe-*.json'),reverse=True):
 j=json.loads(f.read_text());saved=j.get('preserved_efi')
 if not j.get('active') or not saved:continue
 backup=Path(saved)
 if backup.parent!=media or not backup.name.startswith('EFI-before-NMProbe-'):p.error('Invalid backup path in record')
 if not (backup/'OC/config.plist').is_file():continue
 current=media/'EFI';cfg=current/'OC/config.plist'
 if not cfg.is_file() or hashlib.sha256(cfg.read_bytes()).hexdigest()!=j['probe_config_sha256']:p.error('Active EFI changed since probe activation; originals are still in '+str(backup))
 parked=media/('EFI-after-NMProbe-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S'))
 if parked.exists():p.error('Output already exists: '+str(parked))
 current.rename(parked)
 try:backup.rename(current)
 except BaseException:parked.rename(current);raise
 j['active']=False;j['restored']=True;f.write_text(json.dumps(j,indent=2)+'\n')
 print('Original EFI restored. Probe EFI retained at '+str(parked));break
else:print('No active probe EFI recorded; nothing changed.')
