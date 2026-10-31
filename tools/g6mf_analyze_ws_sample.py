#!/usr/bin/env python3
"""Summarize exclusive main-thread sample leaves and Mach-call ancestry.
Counts are sampling observations, never CPU percentages or per-frame timings.
"""
import argparse, collections, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('samples',nargs='+',type=Path)
p.add_argument('--focus',action='append',default=[],help='Exact symbol whose main-thread ancestry should be summarized (repeatable).')
a=p.parse_args()
results=[]
for path in a.samples:
 lines=path.read_text().splitlines()
 start=next(i for i,l in enumerate(lines) if 'ws_main_thread' in l)
 end=next((i for i in range(start+1,len(lines)) if 'Thread_' in lines[i]),len(lines))
 rows=[]
 for line in lines[start+1:end]:
  m=re.search(r'(\d+) (.*)',line)
  if m: rows.append((m.start(),int(m[1]),m[2].split('  (in ')[0]))
 leaves=collections.Counter();mach=collections.Counter();stack=[]
 focus={name:collections.Counter() for name in a.focus}
 for i,(depth,count,name) in enumerate(rows):
  while stack and stack[-1][0]>=depth:stack.pop()
  stack.append((depth,name))
  if i+1==len(rows) or rows[i+1][0]<=depth:leaves[name]+=count
  if name=='mach_msg2_trap':mach[' -> '.join(n for _,n in stack[-7:])]+=count
  if name in focus:focus[name][' -> '.join(n for _,n in stack[-11:])]+=count
 total=int(re.search(r'(\d+) Thread_',lines[start])[1])
 if sum(leaves.values())!=total:raise ValueError('Sample tree did not balance: '+str(path))
 results.append(dict(sample=str(path),main_samples=total,exclusive_leaves=leaves.most_common(20),mach_paths=mach.most_common(20)))
 if focus:results[-1]['focus_paths']={name:paths.most_common() for name,paths in focus.items()}
print(json.dumps(results,indent=2))
