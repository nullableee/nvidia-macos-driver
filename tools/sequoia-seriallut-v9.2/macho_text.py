#!/usr/bin/env python3
"""Compare only Mach-O __TEXT,__text bytes, which codesign does not change."""
from pathlib import Path
import argparse, hashlib, struct, sys

p=argparse.ArgumentParser()
p.add_argument('mach_o', type=Path)
p.add_argument('--expected', required=True)
a=p.parse_args()
b=a.mach_o.read_bytes()
assert len(b)>32 and struct.unpack_from('<II',b)==(0xfeedfacf,0x1000007), 'not a thin x86_64 Mach-O'
count,span=struct.unpack_from('<II',b,16)
assert 0 < count < 512 and span < 65536
pos=32
found=[]
for _ in range(count):
    cmd,size=struct.unpack_from('<II',b,pos)
    assert 8<=size<=len(b)-pos
    if cmd==0x19 and b[pos+8:pos+24].split(b'\0')[0]==b'__TEXT':
        sect=struct.unpack_from('<I',b,pos+64)[0]
        for i in range(sect):
            s=pos+72+80*i
            assert s+80<=pos+size
            if b[s:s+16].split(b'\0')[0]==b'__text' and b[s+16:s+32].split(b'\0')[0]==b'__TEXT':
                length=struct.unpack_from('<Q',b,s+40)[0]
                offset=struct.unpack_from('<I',b,s+48)[0]
                assert offset+length<=len(b), 'invalid text offset'
                found.append(hashlib.sha256(b[offset:offset+length]).hexdigest())
    pos+=size
assert len(found)==1, 'ambiguous __text section'
if found[0].lower()!=a.expected.lower():
    print('STOP: installed Metal code is not the validated G6MF Metal 0.4.7',file=sys.stderr)
    print('observed:',found[0],file=sys.stderr)
    sys.exit(1)
print('METAL 0.4.7 __text PASS:',found[0])
