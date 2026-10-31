#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
[ "$(id -u)" != 0 ] || { echo 'Run without sudo; this script requests sudo for switches.';exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(sysctl -n kern.safeboot)" = 0 ] && [ "$(sysctl -n debug.nvrmfb_agdc)" = 1 ] || exit 1
sysctl -n debug.nvaccel_direct_present >/dev/null || { echo 'Boot NVAccel0.1.8 first.';exit 1; }
[ "$(sysctl -n debug.nvaccel_stage_map_copy)" = 0 ] || exit 1
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Library/GPUBundles/NVMTLDriver.bundle/Contents/Info.plist)" = 0.4.3 ] || exit 1
if [ -r "$HERE/installed-during-boot.txt" ] && [ "$(sysctl -n kern.boottime)" = "$(cat "$HERE/installed-during-boot.txt")" ];then echo 'Reboot first.';exit 1;fi
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
sudo -v
original_diag=$(sysctl -n debug.nvaccel_latency_diag)
case "$original_diag" in 0|1) ;; *) exit 1;;esac
restore(){
 local rc=$?
 trap - EXIT
 if ! sudo -n sysctl -w debug.nvaccel_direct_present=0 "debug.nvaccel_latency_diag=$original_diag";then
  echo 'Could not restore switches. Reboot resets direct present to0.' >&2;rc=1
 fi
 exit "$rc"
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
sudo -n sysctl -w debug.nvaccel_direct_present=0 debug.nvaccel_latency_diag=1
OUT=$(mktemp -d "$HERE/ab-$(date +%Y%m%d-%H%M%S).XXXXXX")
sw_vers > "$OUT/os.txt"
kmutil showloaded --list-only > "$OUT/loaded.txt" 2>&1 || true
ps -axo pid,pcpu,comm > "$OUT/processes-before.txt"
keys=(kern.boottime debug.nvaccel_direct_present debug.nvaccel_iop_ok_h4 debug.nvaccel_surface_gpu_timeouts debug.nvaccel_copy_pageoff_fail debug.nvaccel_iop_fail)
for name in attempts ok fallback held timeout total_count total_ns total_max ce_count ce_ns ce_max;do keys+=("debug.nvaccel_direct_$name");done
for name in entry fence ready copy total;do for field in count ns max;do keys+=("debug.nvaccel_perf_${name}_$field");done;done
for name in po_write po_ce;do for field in count ns;do keys+=("debug.nvaccel_diag_${name}_$field");done;done
snapshot(){ sysctl "${keys[@]}" > "$1"; }
echo 'Four automatic animation phases: OFF, ON, ON, OFF. Do not move other windows during the test.'
phase=0
for mode in 0 1 1 0;do
 phase=$((phase+1));prefix="$OUT/phase-$phase-mode-$mode"
 sudo -n sysctl -w "debug.nvaccel_direct_present=$mode"
 snapshot "$prefix-before.txt"
 "$HERE/clock-probe" > "$prefix-start-ns.txt"
 "$HERE/animation-probe" > "$prefix-animation.txt" 2>&1
 "$HERE/clock-probe" > "$prefix-end-ns.txt"
 snapshot "$prefix-after.txt"
 python3 "$HERE/analyze-ab.py" --check "$prefix" "$mode"
 if [ "$phase" = 2 ];then
  # Ordinary CPU readback must remain correct while the display uses the experimental path.
  snapshot "$OUT/cpu-readback-before.txt"
  env G6MF_TEST_REUSE=2 G6MF_DROP_ANCHOR=1 G6MF_FULL=1 "$HERE/pixel-probe" /Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/NVMTLDriver.g6mf-original > "$OUT/cpu-readback-on.txt" 2>&1
  snapshot "$OUT/cpu-readback-after.txt"
  python3 "$HERE/analyze-ab.py" --check-readback "$OUT/cpu-readback-before.txt" "$OUT/cpu-readback-after.txt"
 fi
done
sudo -n sysctl -w debug.nvaccel_direct_present=0
ps -axo pid,pcpu,comm > "$OUT/processes-after.txt"
python3 "$HERE/analyze-ab.py" "$OUT" | tee "$OUT/summary.txt"
echo "A/B COMPLETE: $OUT. Experimental path has been disabled."
