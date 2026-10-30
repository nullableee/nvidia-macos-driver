#!/usr/bin/env python3
"""Run the shipped collector with a mock Darwin shell environment and real awk."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
def counters(increment):
 out={}
 for name in ['entry','fence','ready','copy','total']:
  out[f'debug.nvaccel_perf_{name}_count']=100+increment
  out[f'debug.nvaccel_perf_{name}_ns']=100000000+increment*2000000
  out[f'debug.nvaccel_perf_{name}_max']=5000000
 for n in range(6):out[f'debug.nvaccel_perf_gap_bin{n}']=100+(increment if n==5 else 0)
 out.update({'debug.nvaccel_iop_ok_h4':1000+increment,'debug.nmintel_perf_period_ns':6000000,'debug.nmintel_perf_gap_count':200+increment,'debug.nmintel_perf_gap_ns':1200000000+increment*6000000})
 return ''.join(f'{k}: {v}\n' for k,v in out.items())
for missing in [False,True]:
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);bin=d/'bin';bin.mkdir();kit=d/'kit';kit.mkdir()
  source=(R/'tools/g6mf_collect_perf.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin',f'PATH={bin}:/usr/bin:/bin')
  (kit/'collect-perf.sh').write_text(source)
  (d/'before').write_text(counters(0));(d/'after').write_text(counters(397))
  if missing:(d/'after').write_text((d/'after').read_text().replace('debug.nvaccel_perf_copy_count: 497\n',''))
  commands={'uname':'echo Darwin','id':'echo 0','sleep':'exit 0','date':f'''if [ "$1" = +%s ];then if [ -f '{d}/time' ];then echo 1020;else touch '{d}/time';echo 1000;fi;else echo test;fi''','sysctl':f'''if [ -f '{d}/seen' ];then cat '{d}/after';else touch '{d}/seen';cat '{d}/before';fi'''}
  for name,body in commands.items():
   p=bin/name;p.write_text('#!/bin/bash\n'+body+'\n');p.chmod(0o755)
  result=subprocess.run(['bash',str(kit/'collect-perf.sh')],text=True,capture_output=True)
  if missing:assert result.returncode!=0 and 'Missing or invalid' in result.stderr,result
  else:
   assert result.returncode==0,result.stderr
   assert '397 over 20 s (19.85 copies/s)' in result.stdout,result.stdout
   assert 'copy: n=397 mean=2.0000 ms' in result.stdout,result.stdout
   assert 'VBL counter window estimate=2.382000 s' in result.stdout,result.stdout
print('PASS: real collector formats valid snapshots and refuses missing counters; mock Darwin tools, no hardware FPS assertion')
