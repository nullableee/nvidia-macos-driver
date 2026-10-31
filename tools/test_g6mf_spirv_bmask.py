"""Exercise the production mask scanner, including its set namespaces and malformed input."""
from pathlib import Path
import ctypes, struct, subprocess, tempfile, sys, json
root=Path(__file__).resolve().parents[1]
source=(root/'plugin/nvmtl_vk.c').read_text()
# Upstream turned the plain scanner into a wrapper over
# nvmtl_spirv_bmask_x(p, n, out, skip_fetch); the extraction must cover that
# forward declaration, nvmtl_desc_mask_on and the scanner itself.
start=source.index('static int nvmtl_spirv_bmask_x(const void *p, size_t n, uint64_t out[4], int skip_fetch);')
function=source[start:source.index('\nenum { NVMTL_SLOT_NONE',start)]
constants=source[source.index('#define NVMTL_NBUF '):source.index('#define NVMTL_DISPATCH_PC_BYTES')]
preamble='#include <stdint.h>\n#include <stdlib.h>\n#include <string.h>\n#define NVMTL_NCOL 8\nstatic void nvlog(const char *fmt, ...) { (void)fmt; }\n'+constants
wrapper='\nint scan(const void *p,size_t n,uint64_t *out){ (void)!nvmtl_desc_mask_on(); return nvmtl_spirv_bmask(p,n,out); }\n'
wrapper1='\nint scan1(const void *p,size_t n,uint64_t *out){ (void)&nvmtl_spirv_bmask; (void)!nvmtl_desc_mask_on(); return nvmtl_spirv_bmask_x(p,n,out,1); }\n'
def module(entries):
 words=[0x07230203,0x10000,0,128,0]
 # Binding before DescriptorSet is deliberate: decoration order must not matter.
 for ident,setno,binding in entries: words += [(4<<16)|71,ident,33,binding]
 for ident,setno,binding in entries: words += [(4<<16)|71,ident,34,setno]
 return struct.pack('<%dI'%len(words),*words)
def compile_lib(path_c, path_dylib):
 subprocess.run(['xcrun','clang','-dynamiclib','-Wall','-Werror',str(path_c),'-o',str(path_dylib)],check=True,capture_output=True)
def cdl(name, sym):
 d=getattr(ctypes.CDLL(str(name)), sym)
 d.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint64)];d.restype=ctypes.c_int
 return d
def run(fn, blob):
 buf=ctypes.create_string_buffer(blob);out=(ctypes.c_uint64*4)();ok=fn(buf,len(blob),out);return ok,list(out)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp); results={}
 for variant in ('production','old-fetch-rejection','ignore-every-set3-binding'):
  f=function
  if variant=='old-fetch-rejection':f='\n'.join(l for l in f.splitlines() if 'if (w[i + 1] < bound && heap[w[i + 1]] == 2 && b >= 192' not in l)
  if variant=='ignore-every-set3-binding':f=f.replace(' && b >= 192 && b < 192 + NVMTL_NCOL','')
  c=p/(variant+'.c');lib=p/(variant+'.dylib');c.write_text(preamble+f+wrapper)
  compile_lib(c,lib)
  scan=cdl(lib,'scan')
  fixtures=[(module([(1,0,640),(2,0,160),(3,2,0),(4,3,192),(5,3,194)]),(1,[0,0,1<<32,1])),
   (module([(1,0,192)]),(0,[0]*4)),(module([(1,3,200)]),(0,[0]*4)),
   (module([(1,3,199)]),(1,[0]*4)),(module([(1,0,641),(2,0,480),(3,0,607)]),(1,[0]*4)),
   (module([(1,0,0),(2,0,191)]),(1,[1,0,1<<63,0])),
   (module([(1,2,999)]),(1,[0]*4))]
  failed=[i for i,(blob,expected) in enumerate(fixtures) if run(scan,blob)!=expected]
  for bad in (b'',module([])+b'X',module([])+struct.pack('<I',0),module([])+struct.pack('<I',4<<16)):
   if run(scan,bad)[0]:failed.append('malformed')
  assert bool(failed)==(variant!='production'),(variant,failed)
  print('PASS',variant,'rejected fixtures',failed)
  if variant=='production':
   c1=p/'skip-fetch.c';lib1=p/'skip-fetch.dylib';c1.write_text(preamble+f+wrapper1)
   compile_lib(c1,lib1)
   scan1=cdl(lib1,'scan1')
   skipfixtures=[(module([(2,3,200)]),(1,[0]*4)),          # other class marked + out-of-band binding: skip_fetch accepts it
    (module([(2,3,200),(1,0,2)]),(1,[4,0,0,0])),           # and ordinary bindings still land in the mask
    (module([(3,2,0)]),(1,[0,0,0,0]))]                     # in-band heap binding: skipped
   sbad=[i for i,(blob,expected) in enumerate(skipfixtures) if run(scan1,blob)!=expected]
   assert not sbad,('skip-fetch',sbad,[(blob,run(scan1,blob)) for blob,_ in skipfixtures])
   print('PASS skip-fetch sems=1 accepted')
  if variant=='production' and len(sys.argv)>1:
   counts={'modules':0,'accepted':0,'rejected':0}
   for item in Path(sys.argv[1]).glob('*.spv'):
    data=item.read_bytes()
    if data[:4]!=b'\x03\x02\x23\x07':continue
    counts['modules']+=1;counts['accepted' if run(scan,data)[0] else 'rejected']+=1
   print(json.dumps(counts))
