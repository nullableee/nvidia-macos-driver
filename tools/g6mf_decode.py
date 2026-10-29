#!/usr/bin/env python3
from pathlib import Path
import argparse,plistlib,json,struct
p=argparse.ArgumentParser();p.add_argument('report',type=Path);args=p.parse_args()
f=args.report/'ioreg-full.plist' if args.report.is_dir() else args.report
root=plistlib.loads(f.read_bytes());probes=[];bridges=[]
def walk(n):
 if n.get('IOObjectClass')=='NMIntelProbe':
  rec={'class':'NMIntelProbe','patch':n.get('NMMuxlessPatch'),'version':n.get('NMIntelProbeVersion'),'aperture_bytes':n.get('NMIntelApertureLength'),'pipes':{}}
  for pipe in 'ABCD':
   raw=n.get('NMIntelPipe'+pipe+'Raw');reject=n.get('NMIntelPipe'+pipe+'Reject')
   if not isinstance(raw,bytes) or len(raw)!=28:continue
   v=struct.unpack('<7I',raw);fields=dict(zip(['conf','ctl','stride','size','surf','offset','position'],v))
   rec['pipes'][pipe]={'raw':{k:hex(x) for k,x in fields.items()},'reject':reject,'width':(v[3]&65535)+1,'height':(v[3]>>16)+1,'pitch':(v[2]&4095)*64,'surface':hex(v[4]&~4095)}
  probes.append(rec)
 if n.get('IOObjectClass') in ['NVRMRenderBridge','NMIntelFB','NVAccel']:
  bridges.append({'class':n.get('IOObjectClass'),'patch':n.get('NMMuxlessPatch'),'name':n.get('IORegistryEntryName')})
 for c in n.get('IORegistryEntryChildren',[]):walk(c)
for n in root if isinstance(root,list) else [root]:walk(n)
print(json.dumps({'probes':probes,'bridge_services':bridges,'reject_codes':{0:'linear XRGB usable',1:'plane disabled',2:'format unsupported',3:'tiled',4:'transform/compression/offset',5:'geometry/stride',6:'outside aperture'},'note':'Probe snapshot is not a Metal, GPU completion or display-copy test.'},indent=2,ensure_ascii=False))
