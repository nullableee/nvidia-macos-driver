#!/usr/bin/env python3
"""Validate kmod metadata and reject user-space C++ teardown in kernel binaries."""
from pathlib import Path
import argparse,plistlib,struct
p=argparse.ArgumentParser();p.add_argument('bundles',nargs='+',type=Path);a=p.parse_args()
for bundle in a.bundles:
 j=plistlib.loads((bundle/'Contents/Info.plist').read_bytes());b=(bundle/'Contents/MacOS'/j['CFBundleExecutable']).read_bytes()
 magic,cpu,sub,kind,ncmds=struct.unpack_from('<5I',b)
 assert (magic,cpu,kind)==(0xfeedfacf,0x01000007,11),(bundle,'not x86_64 kext')
 pos=32;segments=[];symtab=None;sections={}
 for i in range(ncmds):
  cmd,size=struct.unpack_from('<II',b,pos)
  if cmd==0x19:
   vm,vs,fo,fs=struct.unpack_from('<4Q',b,pos+24);segments.append((vm,vs,fo,fs))
   nsects=struct.unpack_from('<I',b,pos+64)[0]
   for n in range(nsects):
    sec=pos+72+n*80;name=b[sec:sec+16].split(b'\0')[0].decode()
    sections[name]=struct.unpack_from('<Q',b,sec+40)[0]
  if cmd==2:symtab=struct.unpack_from('<4I',b,pos+8)
  pos+=size
 assert symtab is not None
 symoff,count,stroff,strsize=symtab;value=None;imports=[]
 for i in range(count):
  strx,ty,section,desc,val=struct.unpack_from('<IBBHQ',b,symoff+i*16)
  end=b.index(b'\0',stroff+strx);name=b[stroff+strx:end].decode()
  if name=='_kmod_info':value=val
  if (ty & 0x0e)==0 and (ty & 1):imports.append(name)
 forbidden={'___cxa_atexit','_atexit','___cxa_thread_atexit','___cxa_thread_atexit_impl','__tlv_bootstrap','___dso_handle'}
 bad=sorted(set(imports)&forbidden)
 if bad:raise SystemExit(str(bundle)+': unsupported user-space runtime imports: '+', '.join(bad))
 if not sections.get('__mod_init_func') or not sections.get('__mod_term_func'):
  raise SystemExit(str(bundle)+': kernel module constructor/destructor sections missing')
 assert value is not None,(bundle,'no kmod_info')
 offsets=[fo+value-vm for vm,vs,fo,fs in segments if vm<=value<vm+fs]
 assert len(offsets)==1
 off=offsets[0];ident=b[off+16:off+80].split(b'\0')[0].decode();version=b[off+80:off+144].split(b'\0')[0].decode()
 assert ident==j['CFBundleIdentifier'],(bundle,ident,j['CFBundleIdentifier'])
 assert version==j['CFBundleVersion'],(bundle,version,j['CFBundleVersion'])
 print('PASS:',bundle.name,ident,version,'x86_64 kext; kmod_info matches; module init/term present; no atexit/TLS runtime')
