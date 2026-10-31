#!/bin/bash
# Read-only performance counter collection for macOS.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
LC_ALL=C; export LC_ALL

if [ "$(uname -s)" != "Darwin" ] || [ "$(id -u)" -ne 0 ]; then
    echo 'Run with sudo bash on macOS.' >&2
    exit 1
fi

HERE=$(cd "$(dirname "$0")" && pwd -P)
OUT="$HERE/perf-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$OUT"

KEYS=(
    debug.nvaccel_iop_ok_h4
    debug.nvaccel_iop_enter
    debug.nvaccel_iop_validate
    debug.nvaccel_iop_empty
    debug.nvaccel_iop_fail
    debug.nvaccel_surface_gpu_timeouts
    debug.nvaccel_stage_map_ok
    debug.nvaccel_stage_map_fallback
    debug.nvaccel_copy_lock_miss
    debug.nvaccel_copy_pageoff_fail
    debug.nvaccel_iop_copy_skip
    debug.nmintel_perf_period_ns
    debug.nmintel_perf_gap_count
    debug.nmintel_perf_gap_ns
    debug.nmintel_perf_gap_max
    debug.nmintel_perf_callback_count
    debug.nmintel_perf_callback_ns
    debug.nmintel_perf_callback_max
)

for metric in entry fence ready copy total; do
    for field in count ns max; do
        KEYS+=("debug.nvaccel_perf_${metric}_${field}")
    done
done
for bin in 0 1 2 3 4 5; do
    KEYS+=("debug.nvaccel_perf_gap_bin${bin}")
done

snapshot() {
    sysctl "${KEYS[@]}" > "$OUT/$1.txt" 2> "$OUT/$1-errors.txt"
}

if ! snapshot before; then
    echo "Perf counters missing. Review $OUT/before-errors.txt" >&2
    exit 1
fi

start=$(date +%s)
echo 'For 20 seconds keep windows moving continuously; use the same movement in later comparisons.'
sleep 20

if ! snapshot after; then
    echo "Failed to read counters. Review $OUT/after-errors.txt" >&2
    exit 1
fi
end=$(date +%s)
seconds=$((end - start))
printf '%s\n' "$seconds" > "$OUT/elapsed-seconds.txt"

awk -v seconds="$seconds" '
    function numeric(s) { return (s ~ /^[0-9]+([.][0-9]+)?$/) }
    function delta(key) { return after[key] - before[key] }
    function require(key) {
        if (!(key in before) || !(key in after) || !numeric(before[key]) || !numeric(after[key])) {
            printf "Missing or invalid sysctl counter: %s\n", key > "/dev/stderr"
            bad = 1
        }
    }
    {
        key = $1
        sub(/:$/, "", key)
        if (NF >= 2) {
            if (FNR == NR) before[key] = $2
            else after[key] = $2
        }
    }
    END {
        require("debug.nvaccel_iop_ok_h4")
        require("debug.nmintel_perf_period_ns")
        require("debug.nmintel_perf_gap_count")
        require("debug.nmintel_perf_gap_ns")
        for (i = 1; i <= 5; i++) {
            split("entry fence ready copy total", names, " ")
            prefix = "debug.nvaccel_perf_" names[i] "_"
            require(prefix "count")
            require(prefix "ns")
            require(prefix "max")
        }
        for (i = 0; i < 6; i++) require("debug.nvaccel_perf_gap_bin" i)
        if (bad) exit 2

        split("stage_map_ok stage_map_fallback copy_lock_miss copy_pageoff_fail", extra, " ")
        for (i = 1; i <= 4; i++) {
            k = "debug.nvaccel_" extra[i]
            if (k in before && k in after) printf "%s: %.0f\n", extra[i], delta(k)
        }
        print "Cumulative counter deltas; window is approximate, not a calibrated display FPS benchmark."
        frames = delta("debug.nvaccel_iop_ok_h4")
        printf "Panel copies: %.0f over %d s (%.2f copies/s)\n", frames, seconds, frames / (seconds ? seconds : 1)

        split("entry fence ready copy total", names, " ")
        for (i = 1; i <= 5; i++) {
            prefix = "debug.nvaccel_perf_" names[i] "_"
            n = delta(prefix "count")
            ns = delta(prefix "ns")
            printf "%s: n=%.0f mean=%.4f ms; max since boot=%.4f ms\n", names[i], n, n ? ns/n/1000000 : 0, after[prefix "max"]/1000000
        }
        n = delta("debug.nmintel_perf_gap_count")
        ns = delta("debug.nmintel_perf_gap_ns")
        if (ns > 0) printf "VBL counter window estimate=%.6f s; panel copies/window=%.2f copies/s (sequential snapshots, not application FPS)\n", ns/1000000000, frames*1000000000/ns
        printf "VBL configured period=%.4f ms, observed mean=%.4f ms, intervals=%.0f\n", after["debug.nmintel_perf_period_ns"]/1000000, n ? ns/n/1000000 : 0, n
        print "Transaction interval histogram: <7, 7-12, 12-20, 20-28, 28-40, >=40 ms"
        for (i = 0; i < 6; i++) {
            key = "debug.nvaccel_perf_gap_bin" i
            sep = (i == 5 ? "\n" : " ")
            printf "%.0f%s", delta(key), sep
        }
    }
' "$OUT/before.txt" "$OUT/after.txt" | tee "$OUT/summary.txt"

cat /Library/NullMoth/g6mf-lut-serial > "$OUT/serial-config.txt" 2> "$OUT/serial-config-errors.txt" || true

# Mode and driver counters from this v10 experiment.
sysctl debug.nvaccel_stage_map_copy debug.nvaccel_muxless_copy64 > "$OUT/copy-mode.txt" 2> "$OUT/copy-mode-errors.txt" || true

if [ -f "$HERE/collect-macos.sh" ]; then
    bash "$HERE/collect-macos.sh" "$OUT"
else
    echo "Warning: collect-macos.sh not found; sysctl statistics saved only." >&2
fi

echo "PERF COLLECTION COMPLETE: $OUT"
