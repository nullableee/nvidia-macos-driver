#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || exit 1
OUT="$HERE/bridge-$(date +%Y%m%d-%H%M%S)-$$";mkdir "$OUT"
echo 'For 15 seconds move windows on the built-in panel to generate display frames.'
sysctl debug.nvaccelfb debug.nvaccel_heads_published debug.nvaccel_heads_registered debug.nvaccel_heads_piped debug.nvaccel_iop_ok_h4 > "$OUT/counters-before.txt" 2>&1 || true
sleep 15
sysctl debug.nvaccelfb debug.nvaccel_heads_published debug.nvaccel_heads_registered debug.nvaccel_heads_piped debug.nvaccel_iop_ok_h4 > "$OUT/counters-after.txt" 2>&1 || true
bash "$HERE/collect-macos.sh" "$OUT"
echo "BRIDGE COLLECTION COMPLETE: $OUT"
