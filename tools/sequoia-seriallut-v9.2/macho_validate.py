#!/usr/bin/env python3
"""Validate a complete, thin x86_64 Mach-O file, without arbitrary size thresholds.
Shared by prepare.py and install.sh so preflight and install validate the same things.
"""
import argparse
import struct
from pathlib import Path

MH_MAGIC_64=0xFEEDFACF
CPU_TYPE_X86_64=0x01000007
MH_EXECUTE=2
MH_BUNDLE=8
LC_SEGMENT_64=0x19

class MachOError(ValueError):
    pass

def validate_macho(data, expected_type, name='binary'):
    if len(data)<32:
        raise MachOError('%s: truncated Mach-O header (%d bytes)'%(name,len(data)))
    magic,cpu,subtype,kind,ncmds,sizecmds,flags,reserved=struct.unpack_from('<8I',data,0)
    if magic!=MH_MAGIC_64:
        raise MachOError('%s: wrong magic %#x (expected %#x)'%(name,magic,MH_MAGIC_64))
    if cpu!=CPU_TYPE_X86_64:
        raise MachOError('%s: wrong cpu %#x (expected %#x)'%(name,cpu,CPU_TYPE_X86_64))
    if kind!=expected_type:
        raise MachOError('%s: wrong Mach-O filetype %d (expected %d)'%(name,kind,expected_type))
    if not (0<ncmds<=1024) or sizecmds<8 or sizecmds>len(data)-32:
        raise MachOError('%s: invalid load command count/size %d/%d'%(name,ncmds,sizecmds))
    pos=32
    end=32+sizecmds
    text=False
    for i in range(ncmds):
        if pos+8>end:
            raise MachOError('%s: truncated load command %d'%(name,i))
        cmd,sz=struct.unpack_from('<II',data,pos)
        if sz<8 or sz%8 or pos+sz>end:
            raise MachOError('%s: invalid load command %d size %d'%(name,i,sz))
        if cmd==LC_SEGMENT_64 and sz>=72 and data[pos+8:pos+24].split(b'\0')[0]==b'__TEXT':
            text=True
            nsects=struct.unpack_from('<I',data,pos+64)[0]
            if nsects>(sz-72)//80:
                raise MachOError('%s: truncated __TEXT section table'%name)
        pos+=sz
    if pos!=end:
        raise MachOError('%s: load command size inconsistent'%name)
    if not text:
        raise MachOError('%s: __TEXT segment not present'%name)
    return {'bytes':len(data),'filetype':kind,'load_commands':ncmds}

def validate_file(path, expected_type):
    path=Path(path)
    result=validate_macho(path.read_bytes(),expected_type,path.name)
    print('MACH-O PASS: %s (%d bytes, x86_64, type=%d)'%(path.name,result['bytes'],result['filetype']))
    return result

def self_test():
    segment=struct.pack('<II16sQQQQiiII',LC_SEGMENT_64,72,b'__TEXT'+bytes(10),0x100000000,4096,0,0,7,5,0,0)
    assert len(segment)==72
    for kind in (MH_EXECUTE,MH_BUNDLE):
        tiny=struct.pack('<8I',MH_MAGIC_64,CPU_TYPE_X86_64,3,kind,1,72,0,0)+segment
        assert len(tiny)==104
        assert validate_macho(tiny,kind)['bytes']==104
        for bad in (tiny[:25],tiny[:80],tiny[:12]+struct.pack('<I',kind^1)+tiny[16:],tiny[:4]+struct.pack('<I',12)+tiny[8:]):
            try:validate_macho(bad,kind)
            except MachOError:pass
            else:raise AssertionError('invalid Mach-O accepted')
    print('MACH-O VALIDATOR SELF-TEST PASS (104-byte valid headers, rejects truncation/type/arch)')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('path',nargs='?')
    ap.add_argument('--type',type=int,choices=[MH_EXECUTE,MH_BUNDLE])
    ap.add_argument('--self-test',action='store_true')
    a=ap.parse_args()
    if a.self_test:self_test()
    else:
        if a.path is None or a.type is None:ap.error('provide path and --type')
        validate_file(a.path,a.type)
