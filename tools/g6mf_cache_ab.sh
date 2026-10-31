#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
[ "$(id -u)" != 0 ] || { echo 'Run without sudo.';exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(sysctl -n kern.safeboot)" = 0 ] && [ "$(sysctl -n debug.nvrmfb_agdc)" = 1 ] || exit 1
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Library/GPUBundles/NVMTLDriver.bundle/Contents/Info.plist)" = 0.4.5 ] || exit 1
if [ -r "$HERE/installed-during-boot.txt" ] && [ "$(sysctl -n kern.boottime)" = "$(cat "$HERE/installed-during-boot.txt")" ];then echo 'Reboot first.';exit 1;fi
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
CONFIG=/Library/NullMoth/g6mf-surface-cache-mb
[ ! -L "$CONFIG" ] || exit 1
original_cache=absent
if [ -e "$CONFIG" ];then original_cache=$(cat "$CONFIG");case "$original_cache" in 64|128) ;; *) echo 'Invalid preexisting cache policy; stopped.';exit 1;;esac;fi
original_direct=$(sysctl -n debug.nvaccel_direct_present);original_diag=$(sysctl -n debug.nvaccel_latency_diag)
case "$original_direct:$original_diag" in 0:0|0:1|1:0|1:1) ;; *) exit 1;;esac
sudo -v
restore(){
 local rc=$? target=0
 trap - EXIT
 [ "$rc" != 0 ] || target=$original_direct
 if ! sudo -n bash "$HERE/set-cache-budget.sh" "$original_cache";then echo 'Cache policy restoration failed.' >&2;rc=1;fi
 if ! sudo -n sysctl -w "debug.nvaccel_direct_present=$target" "debug.nvaccel_latency_diag=$original_diag";then echo 'Switch restoration failed; reboot resets direct mode.' >&2;rc=1;fi
 exit "$rc"
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
sudo -n sysctl -w debug.nvaccel_direct_present=1 debug.nvaccel_latency_diag=1
OUT=$(mktemp -d "$HERE/cache-ab-$(date +%Y%m%d-%H%M%S).XXXXXX")
sw_vers > "$OUT/os.txt";sysctl kern.boottime > "$OUT/boot.txt"
ps -axo pid,pcpu,comm > "$OUT/processes-before.txt"
keys=(debug.nvaccel_direct_present debug.nvaccel_iop_ok_h4 debug.nvaccel_surface_gpu_timeouts debug.nvaccel_copy_pageoff_fail debug.nvaccel_iop_fail debug.nvaccel_direct_held debug.nvaccel_direct_timeout debug.nvaccel_direct_ok debug.nvaccel_perf_total_count debug.nvaccel_perf_total_ns)
echo 'Four automatic phases:64,128,128,64 MiB.12 test windows close automatically; leave other windows still.'
phase=0
for budget in 64 128 128 64;do
 phase=$((phase+1));prefix="$OUT/phase-$phase-mb-$budget"
 sudo -n bash "$HERE/set-cache-budget.sh" "$budget"
 start=$(date '+%Y-%m-%d %H:%M:%S')
 sysctl "${keys[@]}" > "$prefix-before.txt"
 "$HERE/clock-probe" > "$prefix-start-ns.txt"
 "$HERE/pressure-probe" > "$prefix-animation.txt" 2>&1
 grep -q '^ANIMATION COMPLETE' "$prefix-animation.txt"
 "$HERE/clock-probe" > "$prefix-end-ns.txt"
 sysctl "${keys[@]}" > "$prefix-after.txt"
 end=$(date '+%Y-%m-%d %H:%M:%S')
 /usr/bin/log show --style compact --start "$start" --end "$end" --predicate 'process == "WindowServer" AND eventMessage BEGINSWITH "G6MF 0.4.5 "' > "$prefix-graphics.txt" 2> "$prefix-graphics-errors.txt" || true
 python3 "$HERE/analyze-cache.py" --check "$prefix"
done
# Collect a separate loaded profile; sampling must not bias only one A/B phase.
sudo -n bash "$HERE/set-cache-budget.sh" 128
prefix="$OUT/profile-mb-128";start=$(date '+%Y-%m-%d %H:%M:%S')
sysctl "${keys[@]}" > "$prefix-before.txt";"$HERE/clock-probe" > "$prefix-start-ns.txt"
sudo -n sample "$(pgrep -x WindowServer)" 8 -file "$OUT/windowserver.sample.txt" > "$OUT/sample-status.txt" 2>&1 & sample_pid=$!
"$HERE/pressure-probe" > "$prefix-animation.txt" 2>&1
wait "$sample_pid" || true
if [ -f "$OUT/windowserver.sample.txt" ];then sudo -n chown "$(id -u):$(id -g)" "$OUT/windowserver.sample.txt";fi
grep -q '^ANIMATION COMPLETE' "$prefix-animation.txt"
"$HERE/clock-probe" > "$prefix-end-ns.txt";sysctl "${keys[@]}" > "$prefix-after.txt"
end=$(date '+%Y-%m-%d %H:%M:%S')
/usr/bin/log show --style compact --start "$start" --end "$end" --predicate 'process == "WindowServer" AND eventMessage BEGINSWITH "G6MF 0.4.5 "' > "$prefix-graphics.txt" 2> "$prefix-graphics-errors.txt" || true
python3 "$HERE/analyze-cache.py" --check "$prefix"
if [ -f "$OUT/windowserver.sample.txt" ];then sudo -n chown "$(id -u):$(id -g)" "$OUT/windowserver.sample.txt";fi
ps -axo pid,pcpu,comm > "$OUT/processes-after.txt"
python3 "$HERE/analyze-cache.py" "$OUT" | tee "$OUT/summary.txt"
echo "CACHE A/B COMPLETE: $OUT. Previous policy will be restored."
