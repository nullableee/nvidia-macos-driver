#!/usr/bin/env python3
"""Read-only audit of the exact extracted Tahoe CoreDisplay; never patches it.
Requires capstone 5.x. Apple binaries and generated disassembly stay outside Git.
"""
import argparse,bisect,hashlib,json,struct,uuid
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

def audit(path):
 b=path.read_bytes()
 if len(b)<32 or struct.unpack_from('<II',b)!=(0xfeedfacf,0x1000007):
  raise ValueError('Expected thin x86_64 Mach-O')
 ncmds,sizeofcmds=struct.unpack_from('<II',b,16)
 if ncmds>4096 or 32+sizeofcmds>len(b):raise ValueError('Invalid load commands')
 segments=[];symtab=None;identity=None;p=32
 for _ in range(ncmds):
  if p+8>32+sizeofcmds:raise ValueError('Truncated load command')
  c,z=struct.unpack_from('<II',b,p)
  if z<8 or p+z>32+sizeofcmds:raise ValueError('Invalid load command size')
  if c==0x1b and z==24:identity=str(uuid.UUID(bytes=b[p+8:p+24])).upper()
  if c==0x19 and z>=72:
   va,vs,off,size=struct.unpack_from('<QQQQ',b,p+24)
   if off+size>len(b):raise ValueError('Truncated segment')
   segments.append((va,off,size))
  if c==2 and z==24:symtab=struct.unpack_from('<IIII',b,p+8)
  p+=z
 if identity!='24682CF5-C129-3A3F-91C7-80A228552372':raise ValueError('Unsupported CoreDisplay UUID: '+str(identity))
 if not symtab:raise ValueError('Missing symbol table')
 so,ns,st,ss=symtab
 if so+16*ns>len(b) or st+ss>len(b):raise ValueError('Invalid symbol table')
 symbols={}
 for i in range(ns):
  ix,ty,se,d,va=struct.unpack_from('<IBBHQ',b,so+i*16)
  if va and ix<ss:
   end=b.find(b'\0',st+ix,st+ss)
   if end<0:raise ValueError('Unterminated symbol')
   symbols[va]=b[st+ix:end].decode('utf8',errors='replace')
 keys=sorted(symbols)
 names={
  'current':'__ZNK11CoreDisplay7Display15CurrentHeadroomENS_22HeadroomQueryQualifierE',
  'scale':'__ZN11CoreDisplay7Display17SetEDRScaleFactorEd',
  'property':'__ZN11CoreDisplay7Display15PropertyChangedEv',
  'shiny':'_CoreDisplay_Display_SetShinyData_Server'}
 md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
 result={'uuid':identity,'sha256':hashlib.sha256(b).hexdigest(),'read_only':True,'functions':{}}
 for role,name in names.items():
  found=[v for v,s in symbols.items() if s==name]
  if len(found)!=1:raise ValueError('Required symbol unavailable: '+name)
  start=found[0];k=bisect.bisect_right(keys,start);end=keys[k]
  match=[(v,o,n) for v,o,n in segments if v<=start<end<=v+n]
  if len(match)!=1:raise ValueError('Function not in file-backed segment')
  v,o,n=match[0];code=b[o+start-v:o+end-v]
  rows=[]
  for x in md.disasm(code,start):
   # These are candidate field accesses, not a proof that every base register
   # holds Display*. Stack slots at the same displacement are excluded.
   fields=[op.mem.disp for op in x.operands if op.type==3
           and x.reg_name(op.mem.base) not in ('rbp','rsp','rip')
           and op.mem.disp in (0x170,0x220,0x224,0x45c,0x460)]
   if fields:rows.append({'address':hex(x.address),'instruction':x.mnemonic+' '+x.op_str,'fields':[hex(f) for f in fields]})
  result['functions'][role]={'name':name,'address':hex(start),'candidate_field_accesses':rows}
 # Validate the locked-path unlock call and its neighbouring spill/reload.
 site=0x7ff805385cc3
 v,o,n=next(t for t in segments if t[0]<=site-8<site+10<=t[0]+t[2])
 off=o+site-v
 if b[off-8:off]!=bytes.fromhex('f30f1145e44c89ff') or b[off]!=0xe8 or b[off+5:off+10]!=bytes.fromhex('f30f1045e4'):
  raise ValueError('Locked return site no longer matches the analysed control flow')
 result['locked_return']={'call_address':hex(site),'call_target':hex(site+5+struct.unpack_from('<i',b,off+1)[0]),'displacement_aligned_4':(site+1)%4==0}
 result['limits']=['Static candidate accesses require data-flow review; this is not a complete invalidation proof.','No process memory, cache flags, instructions or files are modified.','No hardware performance claim.']
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:r=audit(a.binary)
 except (ValueError,struct.error,StopIteration,IndexError) as e:p.exit(1,'Audit refused: '+str(e)+'\n')
 a.out.write_text(json.dumps(r,indent=2)+'\n')
 print('Read-only headroom audit saved:',a.out)
