"""Summarize direct-present ABBA windows; counters measure copies, not displayed FPS."""
from pathlib import Path
import sys,re,json,statistics

def read(p):
 result={}
 for line in p.read_text().splitlines():
  k,_,v=line.partition(': ')
  try:result[k]=int(v)
  except ValueError:pass
 return result

def phase(prefix):
 p=str(prefix);before=read(Path(p+'-before.txt'));after=read(Path(p+'-after.txt'))
 delta={k:after[k]-v for k,v in before.items() if k in after and '_max' not in k and k!='debug.nvaccel_direct_present'}
 seconds=(int(Path(p+'-end-ns.txt').read_text())-int(Path(p+'-start-ns.txt').read_text()))/1e9
 if seconds<=0:raise SystemExit('STOP: invalid shared-clock interval.')
 out={'phase':prefix.name,'mode':after['debug.nvaccel_direct_present'],'seconds':seconds,'copies_per_second':delta['debug.nvaccel_iop_ok_h4']/seconds,'delta':delta,'means_ms':{}}
 for name,base in [('handler','debug.nvaccel_perf_total'),('intel_copy','debug.nvaccel_perf_copy'),('cpu_write','debug.nvaccel_diag_po_write'),('direct_total','debug.nvaccel_direct_total'),('direct_ce','debug.nvaccel_direct_ce')]:
  n=delta[base+'_count'];out['means_ms'][name]=delta[base+'_ns']/n/1e6 if n else None
 return out

def check(out):
 d=out['delta']
 for k in ('debug.nvaccel_surface_gpu_timeouts','debug.nvaccel_copy_pageoff_fail','debug.nvaccel_iop_fail','debug.nvaccel_direct_held','debug.nvaccel_direct_timeout'):
  if d[k]!=0:raise SystemExit('STOP: '+k+' changed by '+str(d[k])+'; switches will be restored.')
 if out['copies_per_second']<=0:raise SystemExit('STOP: no panel copies in this window.')
 if out['mode']==1 and d['debug.nvaccel_direct_ok']==0:raise SystemExit('STOP: experimental path did not execute; cannot compare.')
 if out['mode']==0 and d['debug.nvaccel_direct_ok']!=0:raise SystemExit('STOP: unexpected direct-present activity in control.')

if __name__=='__main__':
 if sys.argv[1]=='--check-readback':
  before=read(Path(sys.argv[2]));after=read(Path(sys.argv[3]))
  for key in ('debug.nvaccel_surface_gpu_timeouts','debug.nvaccel_copy_pageoff_fail','debug.nvaccel_iop_fail','debug.nvaccel_direct_held','debug.nvaccel_direct_timeout'):
   if before[key]!=after[key]:raise SystemExit('STOP: '+key+' changed during CPU readback.')
  print('CPU readback counters: PASS');sys.exit(0)
 if sys.argv[1]=='--check':
  out=phase(Path(sys.argv[2]));check(out)
  if out['mode']!=int(sys.argv[3]):raise SystemExit('STOP: direct-present switch changed unexpectedly.')
  print(json.dumps(out,ensure_ascii=False));sys.exit(0)
 folder=Path(sys.argv[1]);rows=[]
 for p in sorted(folder.glob('phase-*-before.txt')):
  out=phase(Path(str(p)[:-len('-before.txt')]));check(out);rows.append(out)
 assert len(rows)==4 and [r['mode']for r in rows]==[0,1,1,0]
 print('Copies/s in snapshot windows (not unique displayed FPS):')
 for r in rows:print(r['phase'],round(r['copies_per_second'],2),'handler_ms',r['means_ms']['handler'],'direct',r['delta']['debug.nvaccel_direct_ok'])
 controls=statistics.mean(r['copies_per_second']for r in rows if not r['mode']);experiment=statistics.mean(r['copies_per_second']for r in rows if r['mode'])
 print(f'Mean control={controls:.2f}; experiment={experiment:.2f}; difference={(experiment/controls-1)*100:.2f}%')
 print('Background workload is live; this is an ABBA comparison, not a calibrated FPS or input-to-photon benchmark.')
 (folder/'summary.json').write_text(json.dumps({'phases':rows,'control_copies_per_second':controls,'experiment_copies_per_second':experiment},indent=2)+'\n')
