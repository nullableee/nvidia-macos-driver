from pathlib import Path
import tempfile,subprocess,os,json,hashlib
root=Path(__file__).resolve().parents[1]
mock=r'''#!/usr/bin/python3
import os,sys,json,time,signal
from pathlib import Path
state=Path(os.environ['MOCK_STATE']);d=json.loads(state.read_text());name=Path(sys.argv[0]).name;a=sys.argv[1:];case=os.environ['MOCK_CASE'];config=Path(os.environ['MOCK_CONFIG']);budget=int(config.read_text()) if config.exists() else 64
if name=='id':print(0 if os.getenv('MOCK_ROOT') else 501)
elif name=='stat':print(0)
elif name=='PlistBuddy':print('0.4.5')
elif name=='pgrep':print(200)
elif name=='clock-probe':print(time.time_ns())
elif name=='sample':Path(a[a.index('-file')+1]).write_text('sample mock')
elif name=='sysctl':
 if a[0]=='-w':
  for item in a[1:]:
   k,_,v=item.partition('=')
   if k.endswith('direct_present'):d['direct']=int(v)
   if k.endswith('latency_diag'):d['diag']=int(v)
  state.write_text(json.dumps(d));sys.exit(0)
 def get(k):
  if k=='kern.boottime':return '{ sec = 1 }'
  if k.endswith('nvrmfb_agdc'):return 1
  if k.endswith('direct_present'):return d['direct']
  if k.endswith('latency_diag'):return d['diag']
  if k.endswith('direct_held'):return d['held']
  if k.endswith('iop_ok_h4')or k.endswith('direct_ok')or k.endswith('perf_total_count'):return d['copies']
  if k.endswith('perf_total_ns'):return d['copies']*3000000
  return 0
 for k in a[1:] if a[0]=='-n' else a:print(str(get(k)) if a[0]=='-n' else k+': '+str(get(k)))
elif name=='pressure-probe':
 if case=='pressure-fail':sys.exit(4)
 if case=='interrupt':os.kill(os.getppid(),signal.SIGINT)
 d['copies']+=100
 if case=='held' and budget==128:d['held']+=1;d['direct']=0
 state.write_text(json.dumps(d));print('ANIMATION COMPLETE')
elif name=='log':
 if case=='no-logs':sys.exit(1)
 for i in range(1,2 if case=='single-record' else 4):
  hit=i*400 if budget==128 else i*100;evict=0 if budget==128 else i*50
  print(f'2026-10-30 22:00:0{i}.000 Df WindowServer[200:1] G6MF 0.4.5 surfaces calls={i*512} vram_hit={hit} created={i*512-hit}')
  print(f'2026-10-30 22:00:0{i}.000 Df WindowServer[200:1] G6MF 0.4.5 cache mb={budget} held=8 bytes=100 evictions={evict} evicted_bytes={evict*100} entry_pressure={evict} byte_pressure=0')
'''
with tempfile.TemporaryDirectory()as td:
 base=Path(td);bin=base/'bin';bin.mkdir()
 for n in ('id','stat','PlistBuddy','pgrep','sysctl','sample','log'):(bin/n).write_text(mock);(bin/n).chmod(0o755)
 for n,code in {'sudo':'if [ "$1" = -v ];then exit 0;fi;[ "$1" != -n ] || shift;export MOCK_ROOT=1;exec "$@"','chown':'exit 0'}.items():
  (bin/n).write_text('#!/bin/bash\n'+code+'\n');(bin/n).chmod(0o755)
 for case in ('pass','pass-existing','single-record','held','pressure-fail','interrupt','no-logs'):
  kit=base/case;kit.mkdir();lib=base/(case+'-library');lib.mkdir();config=lib/'g6mf-surface-cache-mb'
  if case=='pass-existing':config.write_text('128\n')
  state=base/(case+'.json');initial=0 if case=='pass-existing' else 1;state.write_text(json.dumps({'direct':initial,'diag':0,'held':0,'copies':0}))
  for src,dest in [('g6mf_cache_ab.sh','test-desktop.sh'),('g6mf_set_cache_budget.sh','set-cache-budget.sh')]:
   text=(root/'tools'/src).read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin',f'PATH={bin}:/usr/bin:/bin:/usr/sbin:/sbin').replace('/usr/libexec/PlistBuddy',str(bin/'PlistBuddy')).replace('/usr/bin/log',str(bin/'log')).replace('/Library/NullMoth',str(lib))
   (kit/dest).write_text(text)
  (kit/'analyze-cache.py').write_bytes((root/'tools/g6mf_analyze_cache.py').read_bytes())
  for n in ('pressure-probe','clock-probe'):(kit/n).write_text(mock);(kit/n).chmod(0o755)
  (kit/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'for p in sorted(kit.iterdir())))
  r=subprocess.run(['bash',str(kit/'test-desktop.sh')],env=dict(os.environ,MOCK_CASE=case,MOCK_STATE=str(state),MOCK_CONFIG=str(config)),capture_output=True,text=True)
  success=case in ('pass','pass-existing','single-record');assert (r.returncode==0)==success,(case,r.stdout,r.stderr)
  d=json.loads(state.read_text());assert d['direct']==(initial if success else 0)and d['diag']==0,(case,d)
  if case=='pass-existing':assert config.read_text()=='128\n'
  else:assert not config.exists(),case
  if success:
   summaries=list(kit.glob('cache-ab-*/summary.json'));assert summaries
   if case=='single-record':
    rows=json.loads(summaries[0].read_text());assert all(r['policy_records']==1 and 'cache_delta' not in r and 'cache_hit_fraction' not in r for r in rows)
  print('PASS',case,'policy and switches restored')
