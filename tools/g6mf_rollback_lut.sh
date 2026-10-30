#!/bin/bash
# Restore only the Metal bundle and LUT experiment setting. Recovery accepts Data ROOT.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
[ "$(id -u)" = 0 ] || exit 1
BACKUP=${1:?Pass absolute before-lut backup};ROOT=${2:-/};ROOT=${ROOT%/}
case "$BACKUP" in /*) ;; *) exit 1;; esac
case "$ROOT" in ''|/*) ;; *) exit 1;; esac
[ -f "$BACKUP/READY" ] && [ -f "$BACKUP/NVMTLDriver.bundle/Contents/MacOS/NVMTLDriver" ] || { echo 'Incomplete LUT backup.';exit 1; }
PLUGIN="$ROOT/Library/GPUBundles/NVMTLDriver.bundle"
[ -d "$ROOT/Library/GPUBundles" ] || exit 1
if [ -z "$ROOT" ]; then [ "$(sw_vers -buildVersion)" = "$(cat "$BACKUP/macos-build")" ] || exit 1;fi
stage="$ROOT/Library/GPUBundles/.g6mf-lut-restore-$$"
[ ! -e "$stage" ] || exit 1
ditto "$BACKUP/NVMTLDriver.bundle" "$stage"
park="$ROOT/Library/GPUBundles/.g6mf-lut-failed-$$"
[ ! -e "$park" ] || exit 1
if [ -e "$PLUGIN" ];then mv "$PLUGIN" "$park";fi
if ! mv "$stage" "$PLUGIN";then [ ! -e "$park" ] || mv "$park" "$PLUGIN";exit 1;fi
if [ -e "$park" ];then mv "$park" "$BACKUP/failed-bundle-$$";fi
CONFIG="$ROOT/Library/NullMoth/g6mf-lut-limit"
if [ -f "$BACKUP/lut-limit" ];then cp -p "$BACKUP/lut-limit" "$CONFIG";else rm -f "$CONFIG";fi
if [ -f "$BACKUP/serial-config-managed" ];then
 SERIAL="$ROOT/Library/NullMoth/g6mf-lut-serial"
 if [ -f "$BACKUP/lut-serial" ];then cp -p "$BACKUP/lut-serial" "$SERIAL";else rm -f "$SERIAL";fi
fi
sync
echo 'Original Metal bundle restored. Reboot; EFI and kernel collection were not changed.'
