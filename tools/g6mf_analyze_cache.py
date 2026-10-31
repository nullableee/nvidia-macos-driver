from pathlib import Path
import sys,json,re,statistics

def read(p):
 d={}
 for line in p.read_text().splitlines():
  k,_,v=line.partition(': ')
  try:d[k]=int(v)
  except ValueError:pass
 return d

def phase(prefix):
 p=str(prefix);a=read(Path(p+'-before.txt'));b=read(Path(p+'-after.txt'))
 for k in ('debug.nvaccel_surface_gpu_timeouts','debug.nvaccel_copy_pageoff_fail','debug.nvaccel_iop_fail','debug.nvaccel_direct_held','debug.nvaccel_direct_timeout'):
  if b[k]!=a[k]:raise SystemExit('STOP: '+k+' changed; policies will be restored.')
 if b['debug.nvaccel_direct_present']!=1:raise SystemExit('STOP: direct present disabled itself.')
 n=b['debug.nvaccel_perf_total_count']-a['debug.nvaccel_perf_total_count'];ns=b['debug.nvaccel_perf_total_ns']-a['debug.nvaccel_perf_total_ns']
 seconds=(int(Path(p+'-end-ns.txt').read_text())-int(Path(p+'-start-ns.txt').read_text()))/1e9
 if seconds<=0:raise SystemExit('STOP: invalid shared clock interval.')
 result={'phase':prefix.name,'budget_mb':int(prefix.name.rsplit('-',1)[1]),'seconds':seconds,'copies_per_second':(b['debug.nvaccel_iop_ok_h4']-a['debug.nvaccel_iop_ok_h4'])/seconds,'handler_ms':ns/n/1e6 if n else None,'delta':{k:b[k]-a[k]for k in a if k in b}}
 groups=[]
 for line in Path(p+'-graphics.txt').read_text().splitlines():
  values={k:int(v)for k,v in re.findall(r'(\w+)=(\d+)',line)}
  if ' surfaces calls=' in line:groups.append({'surface':values,'time':line[:23]})
  elif ' cache mb=' in line and groups:groups[-1]['cache']=values
 matching=[g for g in groups if g.get('cache',{}).get('mb')==result['budget_mb']]
 result['policy_records']=len(matching)
 if len(matching)>=2:
  x,y=matching[0],matching[-1];s={k:y['surface'][k]-x['surface'][k]for k in y['surface']};c={k:y['cache'][k]-x['cache'][k]for k in ('evictions','evicted_bytes','entry_pressure','byte_pressure')}
  result['cache_delta']=c;result['surface_delta']=s;result['cache_hit_fraction']=s['vram_hit']/s['calls'] if s['calls'] else None
 elif matching:
  result['cache_telemetry']='policy verified by one record; eviction/hit deltas unavailable in this window'
  result['cache_snapshot']=matching[0]['cache']
 else:raise SystemExit('STOP: no matching cache-policy record; cannot verify the requested budget was active.')
 return result

if __name__=='__main__':
 if sys.argv[1]=='--check':print(json.dumps(phase(Path(sys.argv[2]))));sys.exit(0)
 folder=Path(sys.argv[1]);rows=[phase(Path(str(p)[:-len('-before.txt')]))for p in sorted(folder.glob('phase-*-before.txt'))]
 assert [r['budget_mb']for r in rows]==[64,128,128,64]
 for r in rows:print(r['phase'],'copies/s',round(r['copies_per_second'],2),'hit fraction',r.get('cache_hit_fraction'),'evictions',r.get('cache_delta',{}).get('evictions'))
 for budget in (64,128):print('Mean copies/s',budget,statistics.mean(r['copies_per_second']for r in rows if r['budget_mb']==budget))
 print('Live-background ABBA, not calibrated displayed FPS. Read sparse telemetry windows separately from full phase windows.')
 (folder/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
