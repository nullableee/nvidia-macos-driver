#!/bin/bash
# Read-only WindowServer sampling alongside the existing counter measurement.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
LC_ALL=C; export LC_ALL
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in ordinary Tahoe.';exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd -P)
OUT="$HERE/profile-$(date +%Y%m%d-%H%M%S)-$$";mkdir "$OUT"
pid=$(pgrep -x WindowServer | head -1)
[ -n "$pid" ] || { echo 'WindowServer not found.';exit 1; }
ps -p "$pid" -o pid,etime,pcpu,pmem,command > "$OUT/windowserver-before.txt"
echo 'Sampling WindowServer for 20 seconds while collecting display timings. Keep windows moving when prompted.'
sample "$pid" 20 10 -file "$OUT/windowserver.sample.txt" > "$OUT/sample-status.txt" 2>&1 &
sampler=$!
finish() { if kill -0 "$sampler" 2>/dev/null; then kill "$sampler" 2>/dev/null || true;fi; }
trap finish EXIT
bash "$HERE/collect-perf.sh" 2>&1 | tee "$OUT/collector.txt"
status=0;wait "$sampler" || status=$?
printf '%s\n' "$status" > "$OUT/sample-exit-status.txt"
ps -p "$pid" -o pid,etime,pcpu,pmem,command > "$OUT/windowserver-after.txt" || true
sync
echo "PROFILE COLLECTION COMPLETE: $OUT"
