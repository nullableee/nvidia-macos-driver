#!/bin/bash
# Read APFS through apfs-fuse; no writes to the macOS device.
set -eu
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
[ "$(id -u)" = 0 ] || { echo 'Run with sudo bash.' >&2; exit 1; }
DEVICE=/dev/nvme0n1p3
OUT=/home/spotlight/workspace/G6MF-Hardware-2026-10-29/family-linux
MOUNT=/home/spotlight/workspace/g6mf-apfs-readonly
[ -b "$DEVICE" ] || { echo 'Expected APFS partition absent.' >&2; exit 1; }
[ ! -L "$OUT" ] && [ ! -L "$MOUNT" ] || exit 1
mkdir -p "$OUT" "$MOUNT"
mountpoint -q "$MOUNT" && { echo 'Mount point already in use.' >&2; exit 1; }
cleanup() { if mountpoint -q "$MOUNT"; then umount "$MOUNT"; fi; }
trap cleanup EXIT
apfsutil "$DEVICE" > "$OUT/apfs-volumes.txt" 2>&1 || true
for volume in 0 1 2 3 4 5 6 7; do
 echo "Reading APFS volume $volume..."
 if timeout 20 apfs-fuse -v "$volume" -o ro,allow_other "$DEVICE" "$MOUNT" </dev/null > "$OUT/mount-$volume.log" 2>&1; then
  for prefix in "$MOUNT" "$MOUNT/root"; do
   source="$prefix/System/Library/KernelCollections/SystemKernelExtensions.kc"
   if [ -f "$source" ]; then
    cp "$source" "$OUT/SystemKernelExtensions.kc"
    printf 'volume=%s source=%s\n' "$volume" "$source" > "$OUT/source.txt"
    sha256sum "$OUT/SystemKernelExtensions.kc" > "$OUT/SystemKernelExtensions.sha256"
    cleanup
    chown -R "${SUDO_UID:-0}:${SUDO_GID:-0}" "$OUT"
    echo "SYSTEM KC COLLECTED: $OUT"
    exit 0
   fi
  done
 fi
 cleanup
done
chown -R "${SUDO_UID:-0}:${SUDO_GID:-0}" "$OUT"
echo "System KC not found. Diagnostic logs: $OUT" >&2
exit 1
