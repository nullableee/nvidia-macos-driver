#!/usr/bin/env python3
"""Execute the real LUT installer/rollback with mock Darwin commands on temp files."""
from pathlib import Path
import tempfile,subprocess,hashlib
from itertools import product
R=Path(__file__).resolve().parents[1]
for scenario,initial in product(['pass','sign-fail','probe-fail','cap-missing','capture-fail','serial-fail','serial-marker-missing'],[None,'0\n']):
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);system=d/'system';bin=d/'bin';kit=d/'kit';bin.mkdir();kit.mkdir()
  plugin=system/'Library/GPUBundles/NVMTLDriver.bundle';(plugin/'Contents/MacOS').mkdir(parents=True)
  original=plugin/'Contents/MacOS/NVMTLDriver';original.write_text('original plugin bytes')
  (plugin/'Contents/Info.plist').write_text('original plist')
  vendor=plugin/'Contents/MacOS/NVMTLDriver.g6mf-original';vendor.write_text('vendor plugin bytes')
  config=system/'Library/NullMoth';config.mkdir();(config/'g6mf-lut-limit').write_text('1024\n')
  if initial is not None:(config/'g6mf-lut-serial').write_text(initial)
  for name,body in [('uname','echo Darwin'),('id','echo 0'),('sw_vers','echo 25G241'),('chown','exit 0'),('shasum','[ "${1:-}" != -a ] || shift 2; exec sha256sum "$@"'),('codesign','exit 1' if scenario=='sign-fail' else 'exit 0'),('ditto','mkdir -p "$2"; cp -a "$1/." "$2/"'),('PlistBuddy','case "$*" in *CFBundleIdentifier*) echo com.nullmoth.NVMTLDriver;; *NMIntelFB*) echo 0.1.4;; *) echo 0.1.4;; esac')]:
   f=bin/name;f.write_text('#!/bin/bash\n'+body+'\n');f.chmod(0o755)
  for source,dest in [('g6mf_install_serial.sh','install-lut.sh'),('g6mf_rollback_lut.sh','rollback-lut.sh')]:
   text=(R/'tools'/source).read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;').replace('/Library',str(system)+'/Library').replace('/Users/Shared',str(system)+'/Users/Shared').replace('/usr/libexec/PlistBuddy',str(bin/'PlistBuddy'))
   (kit/dest).write_text(text)
  (system/'Users/Shared').mkdir(parents=True)
  (kit/'identity.env').write_text('WRAPPER_TEXT_OFFSET=0\nWRAPPER_TEXT_SIZE='+str(original.stat().st_size)+'\nWRAPPER_TEXT_SHA='+hashlib.sha256(original.read_bytes()).hexdigest()+'\nORIGINAL_TEXT_OFFSET=0\nORIGINAL_TEXT_SIZE='+str(vendor.stat().st_size)+'\nORIGINAL_TEXT_SHA='+hashlib.sha256(vendor.read_bytes()).hexdigest()+'\n')
  (kit/'NVMTLDriver').write_text('candidate wrapper')
  probe=kit/'lut-probe';probe.write_text('#!/bin/bash\n'+('exit 1' if scenario=='probe-fail' else "echo 'SHADER PASS: fixture'" if scenario=='cap-missing' else "echo 'LUT CAP: 1024';echo 'SHADER PASS: fixture'" )+'\n');probe.chmod(0o755)
  serial=kit/'serial-probe';serial.write_text('#!/bin/bash\n'+('exit 1' if scenario=='serial-fail' else 'echo missing-marker' if scenario=='serial-marker-missing' else "echo 'SERIAL HOOK PASS: fixture'")+'\n');serial.chmod(0o755)
  (kit/'capture-boot.sh').write_text('#!/bin/bash\nexit '+('1' if scenario=='capture-fail' else '0')+'\n')
  (kit/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in kit.iterdir() if p.is_file()))
  result=subprocess.run(['bash',str(kit/'install-lut.sh')],text=True,capture_output=True)
  if scenario=='pass':
   assert result.returncode==0,result.stdout+result.stderr
   assert original.read_text()=='candidate wrapper'
   assert vendor.read_text()=='vendor plugin bytes'
   assert (config/'g6mf-lut-serial').read_text()=='1\n'
   backup=(kit/'last-lut-backup.txt').read_text().strip()
   rollback=subprocess.run(['bash',str(kit/'rollback-lut.sh'),backup,'/'],capture_output=True,text=True)
   assert rollback.returncode==0,rollback.stdout+rollback.stderr
  else:assert result.returncode!=0,scenario
  assert original.read_text()=='original plugin bytes',scenario
  assert (config/'g6mf-lut-limit').read_text()=='1024\n',scenario
  assert ((config/'g6mf-lut-serial').read_text() if (config/'g6mf-lut-serial').exists() else None)==initial,scenario
  assert vendor.read_text()=='vendor plugin bytes',scenario
  print('PASS: actual serial installer/rollback',scenario)
