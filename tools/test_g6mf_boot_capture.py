#!/usr/bin/env python3
"""Verify capture installer writes a next-boot job, not an immediate capture."""
from pathlib import Path
import plistlib,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='g6mf-capture-test-') as d:
 d=Path(d);root=d/'system';kit=d/'kit';bin=d/'bin'
 kit.mkdir();bin.mkdir();(root/'Library/LaunchDaemons').mkdir(parents=True)
 for name,body in [('id','echo 0'),('chown','exit 0')]:
  f=bin/name;f.write_text('#!/bin/bash\n'+body+'\n');f.chmod(0o755)
 source=(R/'tools/g6mf_capture_boot.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin;',f'PATH={bin}:/usr/bin:/bin;').replace('/Library',str(root)+'/Library')
 script=kit/'capture-boot.sh';script.write_text(source);(kit/'map-probe').write_bytes(b'map probe fixture')
 subprocess.run(['bash',str(script),'--install'],check=True,stdout=subprocess.PIPE)
 plist=plistlib.loads((root/'Library/LaunchDaemons/com.nullmoth.g6mf-capture.plist').read_bytes())
 runtime=root/'Library/NullMoth/g6mf-capture'
 assert plist['RunAtLoad'] and plist['ProgramArguments']==['/bin/bash',str(runtime/'capture-boot.sh')]
 assert (runtime/'capture-boot.sh').read_text()==source
 assert (runtime/'map-probe').read_bytes()==b'map probe fixture'
 assert not (root/'Users').exists() # no runtime capture started by installation
subprocess.run(['bash','-n',str(R/'tools/g6mf_capture_boot.sh')],check=True)
print('PASS: boot capture installs copied APFS helpers and valid next-boot launchd plist without running them now')
