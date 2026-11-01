#!/bin/bash
# Sequoia x86_64 plugin compile/link smoke test. NEVER installs or signs files.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
if [[ "$(uname -s)" != "Darwin" ]]; then echo "STOP: run on macOS" >&2; exit 2; fi
if [[ "$(id -u)" == 0 ]]; then echo "STOP: do not use sudo" >&2; exit 2; fi
if [[ "$(git -C "$ROOT" branch --show-current)" != "experiment/sequoia-descriptor-perf" ]]; then
    echo "STOP: switch to experiment/sequoia-descriptor-perf before building" >&2
    exit 2
fi
if [[ ! -f "$ROOT/plugin/nvmtl_descriptor_audit.h" ]]; then
    echo "STOP: missing descriptor audit header" >&2; exit 2
fi
if ! xcrun --find clang >/dev/null 2>&1; then
    echo "STOP: install Xcode Command Line Tools" >&2; exit 2
fi
HEADER_ROOT="${VULKAN_INCLUDE:-}"
if [[ -n "$HEADER_ROOT" && ! -f "$HEADER_ROOT/vulkan/vulkan.h" ]]; then
    echo "STOP: VULKAN_INCLUDE must be the directory containing vulkan/vulkan.h" >&2; exit 2
fi
if [[ -z "$HEADER_ROOT" ]]; then
    for candidate in "$HOME/Vulkan-Headers/include" \
                     "$HOME/nvmtl-build/Vulkan-Headers/include" \
                     "$HOME/Projects/Vulkan-Headers/include" \
                     "/usr/local/include" "/opt/homebrew/include"; do
        if [[ -f "$candidate/vulkan/vulkan.h" ]]; then HEADER_ROOT="$candidate"; break; fi
    done
fi
if [[ -z "$HEADER_ROOT" ]]; then
    echo "STOP: Vulkan-Headers not found. Set VULKAN_INCLUDE=/path/to/include" >&2
    echo "No compilation or system changes attempted." >&2
    exit 2
fi
# Diagnostic builds preserve nvlog() messages in a process-private file supplied
# by the smoke harness. Release behavior remains the default.
MODE="release"
if [[ "${G6MF_DIAGNOSTIC:-0}" == "1" ]]; then MODE="diagnostic"; fi
OUT="$HOME/Desktop/G6MF-descriptor-compile-$(date +%Y%m%d-%H%M%S)-$"
mkdir -p "$OUT"
echo "Repository revision: $(git -C "$ROOT" rev-parse --short HEAD)" | tee "$OUT/info.txt"
echo "Vulkan headers: $HEADER_ROOT" | tee -a "$OUT/info.txt"
echo "Build output: $OUT" | tee -a "$OUT/info.txt"
echo "Build mode: $MODE" | tee -a "$OUT/info.txt"
BUILD_DEFINE="-DNVMTL_RELEASE=1"
if [[ "$MODE" == "diagnostic" ]]; then BUILD_DEFINE="-DNVMTL_RELEASE=0"; fi
python3 "$ROOT/tools/test_g6mf_descriptor_audit.py" > "$OUT/audit-test.txt" 2>&1 || {
    cat "$OUT/audit-test.txt"; echo "STOP: audit test failed"; exit 3;
}
python3 "$ROOT/tools/test_g6mf_descriptor_reuse.py" > "$OUT/reuse-test.txt" 2>&1 || {
    cat "$OUT/reuse-test.txt"; echo "STOP: reuse test failed"; exit 3;
}
cd "$ROOT/plugin"
if ! xcrun clang -arch x86_64 -mmacosx-version-min=15.0 -bundle \
   -fobjc-arc -O1 "$BUILD_DEFINE" -Wno-protocol \
   -Wno-incomplete-implementation -Werror=unguarded-availability-new \
   -I"$HEADER_ROOT" \
   -o "$OUT/NVMTLDriver" NVMTLDevice.m \
   -framework Foundation -framework Metal -framework IOSurface \
   -framework IOKit -framework CoreFoundation \
   > "$OUT/build.stdout" 2> "$OUT/build.stderr"; then
    grep -n -E 'error:|fatal error:|Undefined symbols|ld: ' "$OUT/build.stderr" | head -30 || true
    echo "BUILD FAILED. Full log: $OUT/build.stderr"
    echo "No system files were changed."
    exit 4
fi
file "$OUT/NVMTLDriver" | tee -a "$OUT/info.txt"
if ! file "$OUT/NVMTLDriver" | grep -q 'x86_64'; then
    echo "STOP: missing x86_64 architecture" >&2; exit 5
fi
if xcrun --find vtool >/dev/null 2>&1; then
    xcrun vtool -show-build "$OUT/NVMTLDriver" | tee "$OUT/minos.txt"
    if ! grep -Eq 'minos[[:space:]]+15\.0([[:space:]]|$)' "$OUT/minos.txt"; then
        echo "STOP: binary is not marked minos 15.0" >&2; exit 5
    fi
else
    echo "WARNING: vtool unavailable; minos was set in clang arguments but not independently verified." | tee -a "$OUT/info.txt"
fi
shasum -a 256 "$OUT/NVMTLDriver" | tee "$OUT/sha256.txt"
echo "BUILD PASS: $OUT"
echo "NOT INSTALLED; no sudo, codesign, bundle replacement or restart."
