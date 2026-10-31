#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(id -u)" = 0 ] || { echo 'Run with sudo bash';exit 1; }
BACKUP=${1:-$(cat "$HERE/last-backup.txt")}
case "$BACKUP" in /Users/Shared/G6MF-Backups/before-live-reuse-*) ;; *) exit 1;; esac
[ ! -L "$BACKUP" ] && [ -f "$BACKUP/READY" ] && [ -d "$BACKUP/NVMTLDriver.bundle" ] || exit 1
[ "$(sw_vers -buildVersion)" = "$(cat "$BACKUP/macos-build")" ] || exit 1
PLUGIN=/Library/GPUBundles/NVMTLDriver.bundle
CONFIG=/Library/NullMoth/g6mf-live-surface-reuse
for dir in /Library/GPUBundles /Library/NullMoth "$PLUGIN" "$CONFIG";do [ ! -L "$dir" ] || exit 1;done
codesign --verify --strict "$BACKUP/NVMTLDriver.bundle"
STAGED=/Library/GPUBundles/.g6mf-restore-$$
[ ! -e "$STAGED" ] || exit 1
ditto "$BACKUP/NVMTLDriver.bundle" "$STAGED"
chown -R root:wheel "$STAGED"
if [ -e "$PLUGIN" ];then mv "$PLUGIN" "$BACKUP/replaced-$(date +%Y%m%d-%H%M%S)-$$.bundle";fi
mv "$STAGED" "$PLUGIN"
if [ -f "$BACKUP/feature-config" ];then cp -p "$BACKUP/feature-config" "$CONFIG";else rm -f "$CONFIG";fi
codesign --verify --strict "$PLUGIN"
sync
echo 'METAL BUNDLE RESTORED. Reboot normally.'
