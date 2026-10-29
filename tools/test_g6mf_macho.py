#!/usr/bin/env python3
"""Regress the rejected probe's atexit import and missing kernel terminator section."""
from pathlib import Path
import struct,plistlib,subprocess,tempfile,sys
R=Path(__file__).resolve().parents[1]
def fixture(directory,import_name=None,term=True):
 bundle=directory/'Probe.kext';(bundle/'Contents/MacOS').mkdir(parents=True)
 info={'CFBundleExecutable':'Probe','CFBundleIdentifier':'com.example.Probe','CFBundleVersion':'0.1.2'}
 (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
 b=bytearray(0x900);nsects=2 if term else 1;segsize=72+80*nsects
 struct.pack_into('<8I',b,0,0xfeedfacf,0x01000007,3,11,2,segsize+24,0,0)
 struct.pack_into('<II16s4Q4I',b,32,0x19,segsize,b'__DATA',0x1000,0x1000,0x400,0x200,7,3,nsects,0)
 for n,name in enumerate(['__mod_init_func']+(['__mod_term_func'] if term else [])):
  struct.pack_into('<16s16sQQ8I',b,32+72+n*80,name.encode(),b'__DATA',0x1000+n*8,8,0x400+n*8,3,0,0,9+n,0,0,0)
 strings=b'\0_kmod_info\0'+(import_name.encode()+b'\0' if import_name else b'')
 struct.pack_into('<6I',b,32+segsize,2,24,0x600,2 if import_name else 1,0x700,len(strings))
 struct.pack_into('<IBBHQ',b,0x600,1,0xf,1,0,0x1020)
 if import_name:struct.pack_into('<IBBHQ',b,0x610,len(b'\0_kmod_info\0'),1,0,0,0)
 b[0x700:0x700+len(strings)]=strings
 for off,text in [(0x420+16,info['CFBundleIdentifier']),(0x420+80,info['CFBundleVersion'])]:b[off:off+len(text)]=text.encode()
 (bundle/'Contents/MacOS/Probe').write_bytes(b)
 return bundle
with tempfile.TemporaryDirectory(prefix='g6mf-macho-') as temp:
 t=Path(temp)
 for name,imp,term,expected in [('kernel',None,True,None),('cxa','___cxa_atexit',True,'unsupported user-space runtime'),('atexit','_atexit',True,'unsupported user-space runtime'),('tls','__tlv_bootstrap',True,'unsupported user-space runtime'),('no-term',None,False,'constructor/destructor sections missing')]:
  bundle=fixture(t/name,imp,term)
  p=subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py'),str(bundle)],capture_output=True,text=True)
  assert (p.returncode==0)==(expected is None),(name,p.stdout,p.stderr)
  if expected:assert expected in p.stderr,(name,p.stderr)
print('PASS: kernel module metadata, cxa_atexit/atexit/TLS refusal and missing terminator refusal')
