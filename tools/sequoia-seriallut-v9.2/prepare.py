#!/usr/bin/env python3
"""Read-only audit and local build of pinned G6MF v9 for Sequoia 24H232.
   Does NOT install a driver, edit EFI, or patch CoreDisplay on disk.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, shutil, struct, subprocess, sys
from pathlib import Path
from zipfile import ZipFile
from macho_validate import validate_file

ROOT = Path(__file__).resolve().parent
UUID = '37573E08-0E1B-3981-988C-0AFBCA6C9AA7'
TEXT_SHA = '942e14ede3f404499171471997480d364fbafb74577c414beaf2fa8fd76395d6'
TEXT_VM = 0x7ff80404c000
CALL = 0x7ff8041121ff
STUB = 0x7ff8041411f2
INVOKE = 0x7ff80411293c

def sha(b): return hashlib.sha256(b).hexdigest()
def ensure(ok, message):
    if not ok: raise RuntimeError('STOP: ' + message)
def u32(b, pos): return struct.unpack_from('<I', b, pos)[0]
def u64(b, pos): return struct.unpack_from('<Q', b, pos)[0]

def audit(audit_zip):
    with ZipFile(audit_zip) as z:
        meta = json.loads(z.read('CoreDisplay-info.json'))
        data = z.read('CoreDisplay-TEXT.bin')
    ensure(meta['macos_build'] == '24H232', 'CoreDisplay is not from Sequoia 24H232')
    ensure(meta['uuid'].upper() == UUID, 'CoreDisplay UUID mismatch')
    ensure(sha(data) == TEXT_SHA, 'CoreDisplay __TEXT hash mismatch')
    ensure(u32(data, 0) == 0xfeedfacf and u32(data, 4) == 0x1000007,
           'Not x86_64 Mach-O')
    cur = 32
    found_uuid = found_text = False
    for _ in range(u32(data, 16)):
        ensure(cur + 8 <= len(data), 'Mach-O load command truncated')
        cmd, size = struct.unpack_from('<II', data, cur)
        ensure(size >= 8 and cur + size <= len(data), 'Bad Mach-O load command')
        if cmd == 0x1b:
            import uuid
            found_uuid = str(uuid.UUID(bytes=data[cur+8:cur+24])).upper() == UUID
        if cmd == 0x19 and data[cur+8:cur+24].split(b'\0')[0] == b'__TEXT':
            found_text = u64(data,cur+24) == TEXT_VM
        cur += size
    ensure(found_uuid and found_text, 'Mach-O UUID/__TEXT load commands disagree')
    def code(address, size):
        pos = address - TEXT_VM
        ensure(pos >= 0 and pos+size <= len(data), 'Out-of-range __TEXT address')
        return data[pos:pos+size]
    call = code(CALL,5); stub = code(STUB,6)
    ensure(call == bytes.fromhex('e8eeef0200'), 'LUT dispatch call site bytes changed')
    ensure(stub == bytes.fromhex('ff254027f13b'), 'dispatch stub bytes changed')
    ensure(CALL + 5 + struct.unpack_from('<i',call,1)[0] == STUB,
           'LUT dispatch call does not reach expected stub')
    ensure(code(INVOKE,10) == bytes.fromhex('554889e5415741565348'),
           'LUT block invoke prologue changed')
    # This LEA directly materializes the very block function targeted by the hook.
    lea_site=0x7ff804111fb5
    lea=code(lea_site,7)
    ensure(lea[:3] == bytes.fromhex('488d05')
           and lea_site+7+struct.unpack_from('<i',lea,3)[0] == INVOKE,
           'LUT block pointer construction does not target the expected invoke')
    info={'macos_build':'24H232','uuid':UUID,'text_sha256':TEXT_SHA,
          'text_vmaddr':hex(TEXT_VM),'dispatch_call':hex(CALL),
          'dispatch_stub':hex(STUB),'dispatch_slot':hex(STUB+6+struct.unpack_from('<i',stub,2)[0]),
          'dispatch_return':hex(CALL+5),'lut_block_invoke':hex(INVOKE)}
    print('AUDIT MATCH:',UUID,'Sequoia 24H232')
    print('LUT dispatch call:',hex(CALL),'->',hex(STUB))
    print('LUT block invoke:',hex(INVOKE))
    print('Sequoia runtime addresses (unslid) verified against full CoreDisplay __TEXT')
    return info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--audit',type=Path,default=Path.home()/'Desktop/G6MF-Sequoia-CoreDisplay-audit.zip')
    ap.add_argument('--source',type=Path,default=ROOT/'src')
    ap.add_argument('--verify-only',action='store_true')
    a=ap.parse_args()
    info=audit(a.audit)
    if a.verify_only:
        print('READ-ONLY AUDIT PASS: nothing installed')
        return
    ensure(sys.platform=='darwin' and platform.machine()=='x86_64', 'build needs x86_64 macOS')
    ensure(subprocess.check_output(['sw_vers','-buildVersion'],text=True).strip()=='24H232',
           'build is pinned to Sequoia 24H232')
    tools=a.source
    if (tools/'tools/g6mf_lut_serial.c').is_file():
        tools=tools/'tools'
    src=tools/'g6mf_lut_serial.c'
    ensure(src.is_file(), 'missing fork source '+str(src))
    serial=src.read_text()
    replacements={
      '{0x24,0x68,0x2c,0xf5,0xc1,0x29,0x3a,0x3f,0x91,0xc7,0x80,0xa2,0x28,0x55,0x23,0x72}':
      '{0x37,0x57,0x3e,0x08,0x0e,0x1b,0x39,0x81,0x98,0x8c,0x0a,0xfb,0xca,0x6c,0x9a,0xa7}',
      '0x7ff805347000ull':'0x7ff80404c000ull',
      '0x7ff80543a230ull':'0x7ff8041411f2ull',
      '0x7ff80540bbadull':'0x7ff8041121ffull',
      '0x7ff80540c3f2ull':'0x7ff80411293cull',
    }
    for old,new in replacements.items():
        ensure(serial.count(old)==1, 'upstream serial hook anchor changed: '+old)
        serial=serial.replace(old,new,1)
    wrapper=tools/'g6mf_lut_wrapper.c'; probe=tools/'g6mf_serial_probe.c'
    metalprobe=tools/'g6mf_metal_probe.c'
    for f in (wrapper,probe,metalprobe):
        ensure(f.is_file(), 'missing source '+str(f))
    build=ROOT/'build'
    ensure(not build.exists(), 'build/ already exists; leave it in place for review')
    build.mkdir()
    try:
        (build/'serial-sequoia.c').write_text(serial)
        for file in (wrapper,probe,metalprobe):shutil.copy2(file,build/file.name)
        cc=['xcrun','clang','-arch','x86_64','-mmacosx-version-min=15.0','-O2','-Wall','-Wextra','-Werror','-fno-builtin']
        tasks=[
          cc+['-c',str(build/'serial-sequoia.c'),'-o',str(build/'serial.o')],
          cc+['-DG6MF_SERIAL_LUT','-c',str(build/'g6mf_lut_wrapper.c'),'-o',str(build/'wrapper.o')],
          cc+['-bundle',str(build/'wrapper.o'),str(build/'serial.o'),'-o',str(build/'NVMTLDriver')],
          cc+['-fblocks','-c',str(build/'g6mf_serial_probe.c'),'-o',str(build/'serial-probe.o')],
          cc+[str(build/'serial-probe.o'),'-o',str(build/'serial-probe')],
          cc+['-DG6MF_SHADER_PROBE','-DG6MF_LUT_PROBE','-c',str(build/'g6mf_metal_probe.c'),'-o',str(build/'lut-probe.o')],
          cc+[str(build/'lut-probe.o'),'-o',str(build/'lut-probe')],
        ]
        for cmd in tasks:subprocess.run(cmd,check=True)
        for n,k in [('NVMTLDriver',8),('serial-probe',2),('lut-probe',2)]:
            validate_file(build/n,k)
        data={'audit':info,'artifacts':{name:sha((build/name).read_bytes())
                                         for name in ('NVMTLDriver','serial-probe','lut-probe')},
              'built_from':str(tools),'installation_tested':False}
        (build/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
        print('BUILD PASS: 3 complete x86_64 Mach-O files verified (no arbitrary 10-KB requirement)')
        print('NO INSTALLATION. Next: sudo bash install.sh check')
    except BaseException:
        # Keep build directory for error diagnostics; do not install.
        raise

if __name__=='__main__':
    try:main()
    except Exception as exc: print('ERROR:',exc,file=sys.stderr);sys.exit(1)
