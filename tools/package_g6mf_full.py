#!/usr/bin/env python3
"""Compose Tahoe experiment from a pinned upstream release and validated patches.
No installation, EFI activation, network upload or claim of GPU qualification.
"""
from pathlib import Path
import argparse,hashlib,json,plistlib,shutil,subprocess,sys,tarfile,tempfile,posixpath
R=Path(__file__).resolve().parents[1]
BASE='f95f4d24a42f88f9bc71fba12c90bcfe8e060225'
ARCHIVE_SHA='90f4c677f0e15caae69d90136990c88556bed27ba4499fd580ebdf9dcdb9244e'
URL='https://github.com/nullmoth/nvidia-macos-driver/releases/download/v2.6.4/nullmoth-nvidia-2.6.4.tar.gz'
p=argparse.ArgumentParser();p.add_argument('--upstream-archive',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--metal-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
if sha(a.upstream_archive)!=ARCHIVE_SHA:p.error('Pinned upstream release archive hash mismatch')
m=json.loads((a.build/'build-manifest.json').read_text())
if m['base']!=BASE:p.error('Patched binaries must use the exact 2.6.4 source base')
names=['NMIntelFB','NVAccel','NVRMFB','NVRMAGDC']
for name in names:
 binary=a.build/(name+'.kext')/'Contents/MacOS'/name
 if sha(binary)!=m['binaries'][name]['sha256']:p.error('Build manifest hash mismatch: '+name)
subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py')]+[str(a.build/(n+'.kext')) for n in names],check=True)
if a.metal_probe.read_bytes()[:8]!=bytes.fromhex('cffaedfe07000001'):p.error('Metal diagnostic must be x86_64 Mach-O')
out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);kit=out/'NullMoth-G6MF-Full-v1'
if kit.exists():p.error('Output kit already exists; use a fresh output directory')
kit.mkdir();(kit/'validation').mkdir()
def checksums(root):
 files=sorted(f for f in root.rglob('*') if f.is_file() and not f.is_symlink() and f!=root/'SHA256SUMS')
 (root/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(root))+'\n' for f in files))
with tempfile.TemporaryDirectory(prefix='g6mf-full-package-') as temp:
 temp=Path(temp)
 with tarfile.open(a.upstream_archive) as t:
  for member in t:
   name=member.name
   if name.startswith('/') or '..' in Path(name).parts or not (name=='pkgroot' or name.startswith('pkgroot/')):p.error('Invalid upstream archive member')
   if member.issym() or member.islnk():
    target=posixpath.normpath(posixpath.join(posixpath.dirname(name),member.linkname) if member.issym() else member.linkname)
    if member.linkname.startswith('/') or not target.startswith('pkgroot/'):p.error('Upstream link escapes payload')
   elif not (member.isfile() or member.isdir()):p.error('Unexpected upstream archive member type')
  t.extractall(temp,filter='data')
 payload=temp/'pkgroot'
 # Verify original contents before applying replacements.
 for line in (payload/'SHA256SUMS').read_text().splitlines():
  expected,rel=line.split(None,1);rel=rel.lstrip('* ')
  target=payload/rel
  if target.resolve().is_relative_to(payload.resolve()) and target.is_file():
   if sha(target)!=expected:p.error('Original release file hash mismatch: '+rel)
  else:p.error('Invalid original checksum path: '+rel)
 def replace(src,dst):
  if dst.exists():shutil.rmtree(dst)
  shutil.copytree(src,dst)
 ext=payload/'Library/Extensions'
 for name in names:replace(a.build/(name+'.kext'),ext/(name+'.kext'))
 replace(a.build/'NVAccel.kext',payload/'Library/NullMoth/kexts/26/NVAccel.kext')
 install=payload/'install.sh';text=install.read_text()
 old='KEXTS="NVRM NVAccel NVRMFB NVRMAGDC"'
 if text.count(old)!=1:p.error('Upstream installer KEXTS anchor changed')
 text=text.replace(old,'KEXTS="NVRM NVAccel NVRMFB NVRMAGDC NMIntelFB"')
 # Preserve OS approval handling but avoid modifying the policy SQLite DB.
 text=text.replace('if [ -f "$KPDB" ] && [ -x /usr/bin/sqlite3 ]; then','if false; then # G6MF: let macOS handle extension approval')
 install.write_text(text)
 uninstall=payload/'uninstall.sh';text=uninstall.read_text().replace('KEXTS="NVRM NVAccel NVRMFB NVRMAGDC NVPrimarySelector"','KEXTS="NVRM NVAccel NVRMFB NVRMAGDC NMIntelFB NVPrimarySelector"');uninstall.write_text(text)
 shutil.copy2(payload/'BASELINE-IDENTITY.json',payload/'UPSTREAM-BASELINE-IDENTITY.json')
 identity={'package':'G6MF experimental 2.6.4 + muxless v1.2','upstream_source':BASE,'upstream_archive_sha256':ARCHIVE_SHA,'upstream_url':URL,'replaced':names,'first_boot':'NVIDIA headless; -nmintelfboff','hardware_validated':False,'metal_readback_validated':False,'native_kmutil_validated':False}
 (payload/'BASELINE-IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
 (payload/'VERSION').write_text('2.6.4\n')
 # Confirm preserved NVRM, plugin, firmware and every other untouched file.
 changed_prefixes=('Library/Extensions/NVAccel.kext/','Library/Extensions/NVRMFB.kext/','Library/Extensions/NVRMAGDC.kext/','Library/NullMoth/kexts/26/NVAccel.kext/')
 changed_files={'install.sh','uninstall.sh','BASELINE-IDENTITY.json','VERSION','Library/NullMoth/kexts/26/SHA256SUMS'}
 original_lines=(payload/'SHA256SUMS').read_text().splitlines();untouched=0
 for line in original_lines:
  expected,rel=line.split(None,1);rel=rel.lstrip('* ')
  if rel in changed_files or rel.startswith(changed_prefixes):continue
  if sha(payload/rel)!=expected:p.error('Unexpected modification of upstream component: '+rel)
  untouched+=1
 identity['unchanged_upstream_files_verified']=untouched
 (payload/'BASELINE-IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
 checksums(payload/'Library/NullMoth/kexts/26')
 (payload/'MANIFEST.txt').write_text('\n'.join(sorted(str(f.relative_to(payload)) for f in payload.rglob('*') if f.is_file() and f.name not in ('MANIFEST.txt','SHA256SUMS')))+'\n')
 checksums(payload)
 with tarfile.open(kit/'payload.tar.gz','w:gz') as t:t.add(payload,arcname='pkgroot')
 for src,dest in [('tools/g6mf_install_full.sh','install-macos.sh'),('tools/g6mf_rollback_full.sh','rollback-macos.sh'),('tools/g6mf_prepare_full_efi.py','prepare-efi.py'),('tools/g6mf_collect_full.sh','collect-full.sh'),('tools/g6mf_collect_macos.sh','collect-macos.sh'),('tools/g6mf_metal_probe.c','metal-probe.c'),('docs/G6MF-FULL-KIT-RU.md','README-RU.md'),('LICENSE','LICENSE'),('NOTICE','NOTICE')]:shutil.copy2(R/src,kit/dest)
 shutil.copy2(a.metal_probe,kit/'metal-probe');(kit/'metal-probe').chmod(0o755)
 # Keep this list in lockstep with the fixed rollback allowlist.
 rollback=(R/'tools/g6mf_rollback_full.sh').read_text();paths=rollback.split("PATHS='",1)[1].split("'",1)[0]
 (kit/'snapshot-paths.txt').write_text(paths+'\n')
 shutil.copy2(a.build/'build-manifest.json',kit/'validation/build-manifest.json')
 (kit/'validation/full-manifest.json').write_text(json.dumps(identity,indent=2)+'\n')
 checksums(kit)
archive=out/(kit.name+'.tar.gz')
with tarfile.open(archive,'w:gz') as t:t.add(kit,arcname=kit.name)
(out/'SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n')
print('Full experimental offline kit:',kit)
print('Archive:',archive)
print('Preserved upstream files verified:',untouched)
