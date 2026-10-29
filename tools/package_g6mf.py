#!/usr/bin/env python3
"""Create an offline kit only when all requested binaries match the build manifest."""
from pathlib import Path
import argparse,json,hashlib,shutil,tarfile,tempfile,subprocess,sys
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--target',choices=['all','probe'],default='all');a=p.parse_args()
build=a.build.resolve();out=a.out.resolve();manifest=json.loads((build/'build-manifest.json').read_text())
expected=['NMIntelProbe']+(['NMIntelFB','NVAccel','NVRMFB','NVRMAGDC'] if a.target=='all' else [])
for name in expected:
 entry=manifest['binaries'].get(name)
 if not entry:raise SystemExit('Missing build manifest entry: '+name)
 binary=build/(name+'.kext')/'Contents/MacOS'/name
 if hashlib.sha256(binary.read_bytes()).hexdigest()!=entry['sha256']:raise SystemExit('Binary hash mismatch: '+name)
subprocess.run([sys.executable,str(R/'tools/validate_g6mf_kext.py')]+[str(build/(n+'.kext')) for n in expected],check=True)
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='g6mf-package-') as temp:
 kit=Path(temp)/'NullMoth-G6MF-v1';kit.mkdir();(kit/'validation').mkdir()
 for name in expected:
  dest=kit/('probe' if name=='NMIntelProbe' else 'candidate')/(name+'.kext')
  shutil.copytree(build/(name+'.kext'),dest)
 for f in build.glob('*.log'):shutil.copy2(f,kit/'validation'/f.name)
 shutil.copy2(build/'build-manifest.json',kit/'validation/build-manifest.json')
 for src,dest in [('tools/g6mf_prepare_probe.py','prepare-probe.py'),('tools/g6mf_restore_probe.py','restore-probe.py'),('tools/g6mf_decode.py','decode-report.py'),('tools/g6mf_collect_macos.sh','collect-macos.sh'),('docs/G6MF-MUXLESS-V1.md','TECHNICAL-NOTES.md'),('docs/G6MF-PROBE-0.1.2.md','PROBE-0.1.2-FIX.md'),('LICENSE','LICENSE'),('NOTICE','NOTICE')]:shutil.copy2(R/src,kit/dest)
 (kit/'README-RU.txt').write_text('''G6 MF CI build — ''','utf-8')
 with (kit/'README-RU.txt').open('a',encoding='utf-8') as f:
  f.write(a.target+'\nSource commit: '+manifest.get('source_commit',manifest['base'])+'\n\n')
  f.write('''Распаковать архив в корень флешки 1401.
В Linux включить отдельный диагностический probe:
python3 /run/media/spotlight/1401/NullMoth-G6MF-v1/prepare-probe.py --activate

В обычной Tahoe собрать данные:
sudo bash /Volumes/1401/NullMoth-G6MF-v1/collect-macos.sh
Дождаться COLLECTION COMPLETE и вернуться в Linux.

Откат тестовой EFI из Linux:
python3 /run/media/spotlight/1401/NullMoth-G6MF-v1/restore-probe.py

Xcode на ноутбуке для этих шагов не нужен.
Исходная EFI сохраняется рядом. Установленный пакет macOS не изменяется.
Probe только читает Intel plane; Metal этим шагом не включается.
Candidate, если присутствует, требует соответствующего полного стека NullMoth.
CI проверяет сборку и CPU-тесты, но не работу графики на железе.
''')
 archive=out/'NullMoth-G6MF-v1.tar.gz'
 with tarfile.open(archive,'w:gz') as t:t.add(kit,arcname=kit.name)
(out/'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print('Offline kit:',archive)
