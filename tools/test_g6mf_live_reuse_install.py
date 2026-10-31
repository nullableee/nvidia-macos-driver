from pathlib import Path
import tempfile,subprocess,shutil,hashlib,os,plistlib,argparse
source=Path(__file__).resolve().parents[1]/'tools'
parser=argparse.ArgumentParser();parser.add_argument('--kit',type=Path);args=parser.parse_args()
version=(args.kit/'release-version.txt').read_text().strip() if args.kit else '0.4.5'
private=bool(args.kit and 'PRIVATE=' in (args.kit/'install.sh').read_text())
failures=['none','pixels','stress','lut','serial','sign','swizzle','hold','descriptor','render','queue','fetch-zero','fetch-live','cache64','cache128']+(['private-safety'] if private else [])
for fail,existing in [(f,False) for f in failures]+[('none',True),('lut',True),('hold',True)]+([('private-safety',True)] if private else []):
 with tempfile.TemporaryDirectory() as td:
  t=Path(td);kit=t/'kit';kit.mkdir();lib=t/'Library';plugin=lib/'GPUBundles/NVMTLDriver.bundle';mac=plugin/'Contents/MacOS';mac.mkdir(parents=True)
  (lib/'NullMoth').mkdir();(lib/'NullMoth/g6mf-lut-limit').write_text('1024\n');(lib/'NullMoth/g6mf-lut-serial').write_text('1\n')
  if existing:(lib/'NullMoth/g6mf-live-surface-reuse').write_text('1\n')
  if private and existing:(lib/'NullMoth/g6mf-private-image-cache').write_text('0\n')
  (mac/'NVMTLDriver').write_text('original-wrapper');(mac/'NVMTLDriver.g6mf-original').write_text('original-payload')
  (plugin/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion':'0.1','CFBundleShortVersionString':'0.1'}))
  (kit/'release-version.txt').write_text(version+'\n')
  (kit/'feature-mode.txt').write_text('2\n')
  backups=t/'backups';backups.mkdir();bin=t/'bin';bin.mkdir()
  for n in ['install.sh','restore.sh']:
   script=args.kit/n if args.kit else source/('g6mf_install_live_reuse.sh' if n=='install.sh' else 'g6mf_restore_live_reuse.sh')
   s=script.read_text().replace('/Library/',str(lib)+'/').replace('/Users/Shared/G6MF-Backups',str(backups)).replace('PATH=/usr/bin:/bin:/usr/sbin:/sbin',f'PATH={bin}:/usr/bin:/bin:/usr/sbin:/sbin')
   (kit/n).write_text(s)
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  (kit/'identity.env').write_text('OLD_WRAPPER_SHA='+sha(mac/'NVMTLDriver')+'\nOLD_ORIGINAL_SHA='+sha(mac/'NVMTLDriver.g6mf-original')+'\n')
  (kit/'NVMTLDriver.g6mf-original').write_text('candidate-payload')
  for n,body in {'queue-probe':f'exit {1 if fail=="queue" else 0}', 'descriptor-probe':f'exit {1 if fail=="descriptor" else 0}', 'render-probe':f'exit {1 if fail=="render" else 0}', 'hold-probe':f'exit {1 if fail=="hold" else 0}', 'swizzle-probe':f'exit {1 if fail=="swizzle" else 0}', 'pixel-probe':f'exit {1 if fail=="pixels" else 0}', 'stress-probe':f'exit {1 if fail=="stress" else 0}', 'lut-probe':('exit 1' if fail=='lut' else 'echo "LUT CAP: 1024";echo "SHADER PASS: yes"'), 'serial-probe':('exit 1' if fail=='serial' else 'echo "SERIAL HOOK PASS: yes"')}.items():
   f=kit/n;f.write_text('#!/bin/bash\n'+body+'\n');f.chmod(0o755)
  if fail in ('fetch-zero','fetch-live','cache64','cache128'):
   body='if [ "${G6MF_FETCH_INPUT:-}" = 1 ] && '+ ('[ "${G6MF_FETCH_LIVE:-}" = 1 ]' if fail=='fetch-live' else '[ -z "${G6MF_FETCH_LIVE:-}" ]')+';then exit 1;fi;exit 0'
   (kit/'render-probe').write_text('#!/bin/bash\n'+body+'\n')
  cp=kit/'cache-probe';cp.write_text('#!/bin/bash\n'+('if [ "$2" = 64 ];then exit 1;fi' if fail=='cache64' else 'if [ "$2" = 128 ];then exit 1;fi' if fail=='cache128' else 'exit 0')+'\n');cp.chmod(0o755)
  pp=kit/'private-safety';pp.write_text('#!/bin/bash\nexit '+('1' if fail=='private-safety' else '0')+'\n');pp.chmod(0o755)
  mocks={'sleep':'/bin/sleep 0.01','id':'echo 0','sw_vers':'echo 25G241','sysctl':'if [ "$2" = kern.safeboot ];then echo 0;else echo 1;fi','stat':'echo 0:700','chown':'exit 0','codesign':('exit 1' if fail=='sign' else 'exit 0'),'ditto':'cp -Rp "$1" "$2"'}
  for n,body in mocks.items():
   f=bin/n;f.write_text('#!/bin/bash\n'+body+'\n');f.chmod(0o755)
  (kit/'SHA256SUMS').write_text(''.join(f'{sha(f)}  {f.name}\n' for f in sorted(kit.iterdir()) if f.is_file()))
  r=subprocess.run(['bash',str(kit/'install.sh')],text=True,capture_output=True)
  if fail=='none':
   assert r.returncode==0,(fail,r.stdout,r.stderr)
   assert (mac/'NVMTLDriver.g6mf-original').read_text()=='candidate-payload'
   assert (lib/'NullMoth/g6mf-live-surface-reuse').read_text()=='2\n'
   assert plistlib.loads((plugin/'Contents/Info.plist').read_bytes())['CFBundleVersion']==version
   if private:assert (lib/'NullMoth/g6mf-private-image-cache').read_text()=='1\n'
   r=subprocess.run(['bash',str(kit/'restore.sh')],text=True,capture_output=True);assert r.returncode==0,(r.stdout,r.stderr)
  else: assert r.returncode!=0,(fail,r.stdout,r.stderr)
  assert (mac/'NVMTLDriver').read_text()=='original-wrapper',fail
  assert (mac/'NVMTLDriver.g6mf-original').read_text()=='original-payload',(fail,r.stdout,r.stderr)
  assert plistlib.loads((plugin/'Contents/Info.plist').read_bytes())['CFBundleVersion']=='0.1'
  if existing:assert (lib/'NullMoth/g6mf-live-surface-reuse').read_text()=='1\n',(fail,r.stdout,r.stderr)
  else:assert not (lib/'NullMoth/g6mf-live-surface-reuse').exists(),(fail,r.stdout,r.stderr)
  if private:
   if existing:assert (lib/'NullMoth/g6mf-private-image-cache').read_text()=='0\n'
   else:assert not (lib/'NullMoth/g6mf-private-image-cache').exists()
  print('PASS',fail,'existing-config' if existing else 'no-config',flush=True)
