#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in ordinary Tahoe.'; exit 1; }
OUT="$HERE/full-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$OUT"
echo 'Waiting 65 seconds for headless Metal publication...'
sleep 65
# FAT32 mount permissions must not decide whether the executable can run.
TEST=$(mktemp -d /var/tmp/g6mf-metal.XXXXXX)
trap 'rm -rf "$TEST"' EXIT
cp "$HERE/metal-probe" "$TEST/metal-probe"
chmod 755 "$TEST/metal-probe"
set +e
"$TEST/metal-probe" > "$OUT/metal-readback.txt" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$OUT/metal-readback-status.txt"
cat "$OUT/metal-readback.txt"
bash "$HERE/collect-macos.sh" "$OUT"
echo "FULL COLLECTION COMPLETE: $OUT"
