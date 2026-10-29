#!/bin/bash
# Usable from ordinary macOS or Recovery; no cmp, Python or Xcode required.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
[ "$(id -u)" = 0 ] || { echo 'Run as root (sudo in ordinary macOS).'; exit 1; }
BACKUP=${1:?Pass the absolute backup directory}; ROOT=${2:-/}
case "$BACKUP" in /*) ;; *) echo 'Backup must be absolute.'; exit 1;; esac
case "$ROOT" in /*) ;; *) echo 'Target root must be absolute.'; exit 1;; esac
ROOT=${ROOT%/}
[ -f "$BACKUP/READY" ] && [ -d "$BACKUP/files" ] || { echo 'Incomplete backup; nothing changed.'; exit 1; }
[ -d "$ROOT/Library/Extensions" ] || { echo 'Target must be the mounted macOS Data volume, containing Library/Extensions.'; exit 1; }
if [ -z "$ROOT" ]; then
 [ "$(sw_vers -buildVersion)" = "$(cat "$BACKUP/macos-build")" ] || { echo 'macOS build changed; kernel collection restoration needs review.'; exit 1; }
 for label in lastgood bootguard osupdate; do launchctl bootout "system/com.nullmoth.$label" 2>/dev/null || true; done
fi
# Fixed allowlist; never execute paths or commands supplied by a backup manifest.
PATHS='Library/Extensions/NVRM.kext
Library/Extensions/NVAccel.kext
Library/Extensions/NVRMFB.kext
Library/Extensions/NVRMAGDC.kext
Library/Extensions/NMIntelFB.kext
Library/GPUBundles/NVMTLDriver.bundle
Library/GPUBundles/NVIDIAShared.bundle
Library/GPUBundles/nvmtl
Library/GPUBundles/nvmtl-allow.txt
Library/NullMoth
Users/Shared/nvfw
Library/LaunchDaemons/com.nullmoth.lastgood.plist
Library/LaunchDaemons/com.nullmoth.bootguard.plist
Library/LaunchDaemons/com.nullmoth.osupdate.plist
Library/KernelCollections/AuxiliaryKernelExtensions.kc'
# Check every expected saved object before removing anything.
while IFS= read -r rel; do
 case "
$PATHS
" in *"
$rel
"*) ;; *) echo 'Invalid backup path record.'; exit 1;; esac
 [ -e "$BACKUP/files/$rel" ] || [ -L "$BACKUP/files/$rel" ] || { echo "Missing saved object: $rel"; exit 1; }
done < "$BACKUP/present.txt"
while IFS= read -r rel; do
 # Avoid following a changed target parent through a symlink.
 parent="$ROOT/$(dirname "$rel")"
 while [ "$parent" != / ] && [ -n "$parent" ]; do
  [ ! -L "$parent" ] || { echo "Symlink in target parent: $parent"; exit 1; }
  parent=${parent%/*}
 done
done <<< "$PATHS"
while IFS= read -r rel; do
 rm -rf "$ROOT/$rel"
 if [ -e "$BACKUP/files/$rel" ] || [ -L "$BACKUP/files/$rel" ]; then
  mkdir -p "$ROOT/$(dirname "$rel")"
  ditto "$BACKUP/files/$rel" "$ROOT/$rel"
 fi
done <<< "$PATHS"
if [ -z "$ROOT" ]; then
 for key in nullmoth-remove nullmoth-nv-starts nullmoth-nv-ok; do
  nvram -d "7C436110-AB2A-4BBB-A880-FE41995C9F82:$key" 2>/dev/null || true
 done
fi
sync
echo 'Driver files and Auxiliary KC restored. EFI is restored separately from Linux.'
echo 'Backup retained. Restart through the saved original EFI.'
