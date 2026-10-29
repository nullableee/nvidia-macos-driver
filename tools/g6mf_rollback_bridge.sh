#!/bin/bash
# Restore the selected framebuffer/accelerator/AGDC update. EFI is restored separately from Linux.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
[ "$(id -u)" = 0 ] || exit 1
BACKUP=${1:?Pass absolute before-bridge backup};ROOT=${2:-/};ROOT=${ROOT%/}
case "$BACKUP" in /*) ;; *) exit 1;; esac
case "$ROOT" in ''|/*) ;; *) exit 1;; esac
[ -f "$BACKUP/READY" ] && [ -f "$BACKUP/NMIntelFB.kext/Contents/Info.plist" ] && [ -s "$BACKUP/AuxiliaryKernelExtensions.kc" ] || { echo 'Incomplete backup; nothing changed.';exit 1; }
if [ -f "$BACKUP/pair-update" ]; then
 [ -f "$BACKUP/NVAccel.kext/Contents/Info.plist" ] || { echo 'Incomplete paired backup; nothing changed.';exit 1; }
fi
if [ -f "$BACKUP/agdc-update" ]; then
 [ -f "$BACKUP/NVRMAGDC.kext/Contents/Info.plist" ] || { echo 'Incomplete AGDC backup; nothing changed.';exit 1; }
fi
[ -d "$ROOT/Library/Extensions" ] && [ -d "$ROOT/Library/KernelCollections" ] || exit 1
if [ -z "$ROOT" ]; then
 [ "$(sw_vers -buildVersion)" = "$(cat "$BACKUP/macos-build")" ] || { echo 'macOS build changed; refusing old KC.';exit 1; }
fi
for parent in "$ROOT/Library" "$ROOT/Library/Extensions" "$ROOT/Library/KernelCollections"; do
 [ ! -L "$parent" ] || { echo 'Symlink in target path.';exit 1; }
done
rm -rf "$ROOT/Library/Extensions/NMIntelFB.kext"
ditto "$BACKUP/NMIntelFB.kext" "$ROOT/Library/Extensions/NMIntelFB.kext"
if [ -f "$BACKUP/pair-update" ]; then
 rm -rf "$ROOT/Library/Extensions/NVAccel.kext"
 ditto "$BACKUP/NVAccel.kext" "$ROOT/Library/Extensions/NVAccel.kext"
 if [ -d "$BACKUP/accel-cache-26" ]; then
  rm -rf "$ROOT/Library/NullMoth/kexts/26"
  ditto "$BACKUP/accel-cache-26" "$ROOT/Library/NullMoth/kexts/26"
 fi
fi
if [ -f "$BACKUP/agdc-update" ]; then
 rm -rf "$ROOT/Library/Extensions/NVRMAGDC.kext"
 ditto "$BACKUP/NVRMAGDC.kext" "$ROOT/Library/Extensions/NVRMAGDC.kext"
fi
cp -p "$BACKUP/AuxiliaryKernelExtensions.kc" "$ROOT/Library/KernelCollections/AuxiliaryKernelExtensions.kc"
rm -f "$ROOT/Library/KernelCollections/AuxiliaryKernelExtensions.kc.g6mf-new"
sync
echo 'Saved graphics components and Auxiliary KC restored. EFI profile is restored separately.'
