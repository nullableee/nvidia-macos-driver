"""Compile the production predicate and reject changed live descriptors.

GPU probes separately cover table-page rollover and pipeline-mask changes.
"""
from pathlib import Path
import subprocess,tempfile
header=(Path(__file__).resolve().parents[1]/'plugin/nvmtl_descriptor_reuse.h').read_text()
fixture=r'''
#define CHECK(x) do { if (!(x)) return 1; } while (0)
int main(){
 uint64_t used[4]={1,0,1ull<<32,1}; // direct buffer0, sampler0, table
 uint64_t changed[4]={(1ull<<32)|2,0,0,0}; // bindless texture0, table-only buffer1
 CHECK(nvmtl_metadata_descriptors_unchanged(0,changed,used));
 changed[0]|=1;CHECK(!nvmtl_metadata_descriptors_unchanged(0,changed,used));changed[0]&=~1ull;
 changed[2]=1ull<<32;CHECK(!nvmtl_metadata_descriptors_unchanged(0,changed,used));changed[2]=0;
 CHECK(!nvmtl_metadata_descriptors_unchanged(1,changed,used));
 CHECK(!nvmtl_metadata_descriptors_unchanged(0,0,used));
 CHECK(!nvmtl_metadata_descriptors_unchanged(0,changed,0));
 uint64_t all[4]={~0ull,~0ull,~0ull,~0ull};
 CHECK(!nvmtl_metadata_descriptors_unchanged(0,changed,all));
 for(unsigned i=0;i<4;i++)changed[i]=0;
 CHECK(nvmtl_metadata_descriptors_unchanged(0,changed,used));
 return 0;
}
'''
variants={'production':header,'ignore-changed':header.replace('changed[k] & used[k]','0'),
          'ignore-storage':header.replace('storage_hi || ','')}
for name,text in variants.items():
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp);(p/'test.c').write_text(text+'\n'+fixture)
  subprocess.run(['xcrun','clang','-x','c','-std=c11',str(p/'test.c'),'-o',str(p/'test')],check=True,capture_output=True)
  result=subprocess.run([str(p/'test')],capture_output=True)
  assert (result.returncode==0)==(name=='production'),(name,result.stderr)
  print('PASS',name)
