#!/bin/bash
# Update diagnostics on the already-working bridge; never changes EFI or boot args.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in ordinary Tahoe.';exit 1; }
[ "$(sw_vers -buildVersion)" = 25G241 ] || { echo 'Expected measured Tahoe build 25G241.';exit 1; }
args=$(sysctl -n kern.bootargs)
case " $args " in *' nmoptimus=1 '*) ;; *) echo 'Expected the working muxless profile.';exit 1;; esac
case " $args " in *' -nmintelfboff '*) echo 'Intel bridge is disabled; keep the working v5 EFI for this test.';exit 1;; esac
bash "$HERE/install-bridge-update.sh"
bash "$HERE/capture-boot.sh" --install
sync
echo 'PERF UPDATE READY. EFI unchanged. Reboot, then run collect-perf.sh.'
