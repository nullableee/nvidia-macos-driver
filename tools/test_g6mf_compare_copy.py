#!/usr/bin/env python3
"""Exercise the actual mode-switching script and its restoration trap."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
for initial in [0,1]:
 for fail in [False,True]:
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);bin=d/'bin';bin.mkdir();kit=d/'kit';kit.mkdir()
   state=d/'mode';state.write_text(str(initial)+'\n');seen=d/'seen'
   source=(R/'tools/g6mf_compare_copy.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin',f'PATH={bin}:/usr/bin:/bin').replace('/Library/NullMoth/g6mf-lut-limit',str(d/'lut'))
   (d/'lut').write_text('1024\n');(kit/'compare-copy.sh').write_text(source)
   commands={'uname':'echo Darwin','id':'echo 0','sw_vers':'echo 25G241','sleep':'exit 0','sync':'exit 0','sysctl':f'''case "$1" in
-n) cat '{state}';;
-w) value=${{2##*=}};printf '%s\\n' "$value" > '{state}';echo "$2";;
*) exit 1;;esac'''}
   for name,body in commands.items():
    f=bin/name;f.write_text('#!/bin/bash\nset -eu\n'+body+'\n');f.chmod(0o755)
   (kit/'profile-perf.sh').write_text(f'''#!/bin/bash
mode=$(cat '{state}')
echo "$mode" >> '{seen}'
''' + ('[ "$mode" != 1 ] || exit 7\n' if fail else '')+'echo PROFILE COLLECTION COMPLETE\n')
   result=subprocess.run(['bash',str(kit/'compare-copy.sh')],text=True,capture_output=True)
   assert result.returncode==(7 if fail else 0),result
   assert state.read_text().strip()==str(initial),result
   assert seen.read_text().splitlines()==['0','1'],result
   assert ('COPY COMPARISON COMPLETE' in result.stdout)==(not fail),result
print('PASS: real copy A/B script selects 0 then 1 and restores initial mode 0/1 on success and profile failure')
