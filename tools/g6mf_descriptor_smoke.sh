#!/bin/bash
# Runs the existing 2048-draw pixel-correctness probe against an isolated bundle.
# NEVER installs drivers, touches EFI, modifies installed bundle or restarts services.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
if [[ "$(uname -s)" != "Darwin" ]]; then echo "STOP: macOS required" >&2; exit 2; fi
if [[ "$(id -u)" == "0" ]]; then echo "STOP: do not run as root" >&2; exit 2; fi
if [[ $# -ne 1 ]]; then
    echo "Usage: bash tools/g6mf_descriptor_smoke.sh /absolute/path/to/NVMTLDriver" >&2
    exit 2
fi
DRIVER="$1"
if [[ "$DRIVER" != /* || ! -f "$DRIVER" ]]; then
    echo "STOP: use the absolute path to a compiled test NVMTLDriver" >&2; exit 2
fi
if [[ "$DRIVER" == "/Library/"* || "$DRIVER" == "/System/"* ]]; then
    echo "STOP: will not test an installed/system binary; use the Desktop build" >&2; exit 2
fi
if ! file "$DRIVER" | grep -q 'x86_64'; then
    echo "STOP: candidate is not x86_64" >&2; exit 2
fi
if [[ "$(git -C "$ROOT" branch --show-current)" != "experiment/sequoia-descriptor-perf" ]]; then
    echo "STOP: use experiment/sequoia-descriptor-perf" >&2; exit 2
fi
if ! nm -gj "$DRIVER" | grep -q '_g6mf_descriptor_audit_stats'; then
    echo "STOP: build is older than the audit snapshot API. Rebuild it first." >&2; exit 2
fi
OUT="$HOME/Desktop/G6MF-descriptor-smoke-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$OUT"
echo "Candidate: $DRIVER" | tee "$OUT/summary.txt"
shasum -a 256 "$DRIVER" | tee -a "$OUT/summary.txt"
echo "Writing logs under: $OUT" | tee -a "$OUT/summary.txt"
xcrun clang -arch x86_64 -mmacosx-version-min=15.0 -fobjc-arc -O1 \
    -o "$OUT/descriptor-render-probe" "$ROOT/tools/g6mf_descriptor_render_probe.m" \
    -framework Foundation -framework Metal -framework IOKit \
    >"$OUT/probe-build.stdout" 2>"$OUT/probe-build.stderr" || {
        cat "$OUT/probe-build.stderr" | tail -30 >&2; exit 3;
    }
run_case() {
    local name="$1"
    shift
    echo "START $name" | tee -a "$OUT/summary.txt"
    if env G6MF_DESC_AUDIT=1 "$@" "$OUT/descriptor-render-probe" "$DRIVER" 1 >"$OUT/$name.log" 2>&1; then
        grep -E 'RENDER PASS|DESC_AUDIT' "$OUT/$name.log" | tee -a "$OUT/summary.txt" || true
        echo "PASS $name" | tee -a "$OUT/summary.txt"
    else
        local rc=$?
        echo "FAIL $name rc=$rc (see $OUT/$name.log); aborting remaining tests." | tee -a "$OUT/summary.txt"
        tail -25 "$OUT/$name.log" >&2
        exit "$rc"
    fi
}
run_case baseline
run_case sampler_churn G6MF_SAMPLER_CHURN=1
run_case mask_churn G6MF_MASK_CHURN=1
echo "GPU SMOKE COMPLETE: $OUT"
echo "NO SYSTEM DRIVER CHANGES; no sudo, no WindowServer restart."
