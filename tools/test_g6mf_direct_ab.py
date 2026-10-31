"""Run the production A/B shell and analyzer with disposable sysctl/sudo/probe mocks."""
from pathlib import Path
import tempfile,subprocess,hashlib,os,json
root=Path(__file__).resolve().parents[1]
mock=r'''#!/usr/bin/python3
import os,sys,json
from pathlib import Path
state=Path(os.environ['MOCK_STATE']);d=json.loads(state.read_text());name=Path(sys.argv[0]).name;a=sys.argv[1:];case=os.environ['MOCK_CASE']
if name=='sysctl':
 if '-w' in a:
  for arg in a[1:]:
   k,_,v=arg.partition('=')
   if k.endswith('direct_present'):d['mode']=int(v);d['history'].append(int(v))
   if k.endswith('latency_diag'):d['diag']=int(v)
  state.write_text(json.dumps(d));sys.exit(0)
 def get(k):
  if k=='kern.boottime':return '{ sec = 1 }'
  if k.endswith('nvrmfb_agdc'):return 1
  if k.endswith('direct_present'):return d['mode']
  if k.endswith('latency_diag'):return d['diag']
  if k.endswith('iop_ok_h4'):return d['copies']
  if k.endswith('direct_ok'):return d['hits']
  if k.endswith('direct_held'):return d['held']
  if k.endswith('perf_total_count')or k.endswith('perf_copy_count'):return d['copies']
  if k.endswith('perf_total_ns'):return d['copies']*4000000
  if k.endswith('perf_copy_ns'):return d['copies']*1800000
  if k.endswith('direct_total_count')or k.endswith('direct_ce_count'):return d['hits']
  if k.endswith('direct_total_ns'):return d['hits']*2500000
  if k.endswith('direct_ce_ns'):return d['hits']*700000
  return 0
 for k in a[1:] if a and a[0]=='-n' else a:print(str(get(k)) if a[0]=='-n' else k+': '+str(get(k)))
elif name=='animation-probe':
 if case=='interrupt':
  import signal;os.kill(os.getppid(),signal.SIGINT)
 d['copies']+=100
 if d['mode']:
  if case!='nohits':d['hits']+=100
  if case=='held':d['held']+=1
 state.write_text(json.dumps(d));print('ANIMATION COMPLETE')
elif name=='pixel-probe':
 if case=='pixel-fail':sys.exit(7)
 if case=='readback-held':d['held']+=1
 d['pixel_calls']+=1;state.write_text(json.dumps(d));print('PIXELS PASS')
'''
with tempfile.TemporaryDirectory()as td:
 base=Path(td);bin=base/'bin';bin.mkdir()
 for name,code in {'id':'echo 501','PlistBuddy':'echo 0.4.3','kmutil':'exit 0','sudo':'if [ "$1" = -v ];then exit 0;fi;[ "$1" != -n ] || shift;exec "$@"'}.items():
  p=bin/name;p.write_text('#!/bin/bash\n'+code+'\n');p.chmod(0o755)
 (bin/'sysctl').write_text(mock);(bin/'sysctl').chmod(0o755)
 for case in ('pass','held','nohits','pixel-fail','readback-held','interrupt'):
  kit=base/case;kit.mkdir();state=base/(case+'.json');state.write_text(json.dumps({'mode':0,'diag':0,'copies':0,'hits':0,'held':0,'history':[],'pixel_calls':0}))
  shell=(root/'tools/g6mf_direct_ab.sh').read_text().replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin',f'PATH={bin}:/usr/bin:/bin:/usr/sbin:/sbin').replace('/usr/libexec/PlistBuddy',str(bin/'PlistBuddy'))
  (kit/'test-desktop.sh').write_text(shell)
  (kit/'analyze-ab.py').write_bytes((root/'tools/g6mf_analyze_direct_ab.py').read_bytes())
  (kit/'clock-probe').write_text('#!/usr/bin/python3\nimport time;print(time.time_ns())\n');(kit/'clock-probe').chmod(0o755)
  for n in ('animation-probe','pixel-probe'):(kit/n).write_text(mock);(kit/n).chmod(0o755)
  (kit/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'for p in sorted(kit.iterdir())if p.is_file()))
  r=subprocess.run(['bash',str(kit/'test-desktop.sh')],env=dict(os.environ,MOCK_STATE=str(state),MOCK_CASE=case),capture_output=True,text=True)
  assert (r.returncode==0)==(case=='pass'),(case,r.stdout,r.stderr)
  d=json.loads(state.read_text());assert d['mode']==0 and d['diag']==0,(case,d)
  if case=='pass':
   assert d['pixel_calls']==1 and d['history']==[0,0,1,1,0,0,0],d
   assert list(kit.glob('ab-*/summary.json'))
  print('PASS',case,'switches restored')
