#!/bin/bash
# Compare the two copy algorithms without changing LUT, EFI or boot arguments.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
LC_ALL=C; export LC_ALL
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in ordinary Tahoe.';exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd -P)
KEY=debug.nvaccel_stage_map_copy
original=$(sysctl -n "$KEY")
case "$original" in 0|1) ;; *) echo 'Expected copy mode 0 or 1.';exit 1;; esac
OUT="$HERE/compare-stage-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$OUT"
restore() {
 local result=$?
 trap - EXIT
 if ! sysctl -w "$KEY=$original" > "$OUT/restored-mode.txt" 2>&1; then
  echo "Could not restore copy mode; reboot returns to the original writeBytes path." >&2
  [ "$result" -ne 0 ] || result=1
 fi
 sync
 exit "$result"
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
printf '%s\n' "$original" > "$OUT/original-mode.txt"
cat /Library/NullMoth/g6mf-lut-limit > "$OUT/lut-limit.txt" 2> "$OUT/lut-limit-errors.txt" || true
sw_vers > "$OUT/os.txt"
echo 'Warm-up: for 45 seconds move windows and repeat the animations you will compare.'
sleep 45
for mode in 0 1; do
 echo "STAGE MAP MODE $mode: next 20-second window; use the SAME window movements in both runs."
 sysctl -w "$KEY=$mode" > "$OUT/mode-$mode.txt"
 [ "$(sysctl -n "$KEY")" = "$mode" ] || { echo 'Mode did not change.';exit 1; }
 bash "$HERE/profile-perf.sh" 2>&1 | tee "$OUT/profile-$mode.txt"
done
echo "STAGE MAP COMPARISON COMPLETE: $OUT"
echo 'The initial copy mode will now be restored. Reboot also restores the original writeBytes path.'
