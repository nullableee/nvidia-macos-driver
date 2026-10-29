#!/bin/bash
# Bash 3.2. Payload and backup are staged on APFS, never backed up to FAT32.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ] || { echo 'Run in Intel macOS Tahoe.'; exit 1; }
[ "$(id -u)" = 0 ] || { echo 'Run with sudo bash.'; exit 1; }
case "$(sw_vers -productVersion)" in 26.*) ;; *) echo 'This kit is Tahoe-only.'; exit 1;; esac
umask 077
STAGE=$(mktemp -d /var/tmp/g6mf-full.XXXXXX)
trap 'rm -rf "$STAGE"' EXIT
echo 'Verifying kit and copying payload to the macOS disk...'
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
tar -xzf "$HERE/payload.tar.gz" -C "$STAGE"
chown -R root:wheel "$STAGE"
chmod -R go-w "$STAGE"
PAYLOAD="$STAGE/pkgroot"
(cd "$PAYLOAD" && shasum -a 256 --strict --quiet -c SHA256SUMS)
# Reject automatic selector adoption: this experiment uses the normal PCI match.
[ ! -e /Library/Extensions/NVPrimarySelector.kext ] || { echo 'STOP: existing primary selector needs separate review.'; exit 1; }
unset NM_PRIMARY_GPU CHECK
BACKUP_BASE=/Users/Shared/G6MF-Backups
[ ! -L "$BACKUP_BASE" ] || { echo 'STOP: backup parent is a symlink.'; exit 1; }
if [ -e "$BACKUP_BASE" ]; then
 [ "$(stat -f '%u:%Lp' "$BACKUP_BASE")" = 0:700 ] || { echo 'STOP: existing backup parent must be root-owned mode 700.'; exit 1; }
else mkdir -m 700 "$BACKUP_BASE"; fi
BACKUP=$(mktemp -d "$BACKUP_BASE/before-full-$(date +%Y%m%d-%H%M%S).XXXXXX")
cp "$HERE/rollback-macos.sh" "$BACKUP/rollback-macos.sh"
cp "$HERE/snapshot-paths.txt" "$BACKUP/snapshot-paths.txt"
sw_vers -buildVersion > "$BACKUP/macos-build"
nvram -x -p > "$BACKUP/nvram-before.plist"
mkdir "$BACKUP/files"
touch "$BACKUP/present.txt"
while IFS= read -r rel; do
 [ -n "$rel" ] || continue
 if [ -e "/$rel" ] || [ -L "/$rel" ]; then
  mkdir -p "$BACKUP/files/$(dirname "$rel")"
  ditto "/$rel" "$BACKUP/files/$rel"
  printf '%s\n' "$rel" >> "$BACKUP/present.txt"
 fi
done < "$HERE/snapshot-paths.txt"
touch "$BACKUP/READY"
echo "Rollback backup: $BACKUP"
LOG="$BACKUP/install.log"
set +e
/bin/bash "$PAYLOAD/install.sh" 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}
set -e
cp "$LOG" "$HERE/last-install.log" 2>/dev/null || true
if [ "$status" != 0 ]; then
 echo 'Install failed. Restoring the saved driver files and kernel collection...'
 /bin/bash "$BACKUP/rollback-macos.sh" "$BACKUP" /
 exit "$status"
fi
touch "$BACKUP/INSTALL-COMPLETE"
echo
echo 'INSTALL COMPLETE. First boot tests NVIDIA with the Intel bridge disabled.'
echo 'Do not arm debug.nvaccelfb yet. Allow extensions if macOS requests it.'
echo "Rollback: sudo bash '$BACKUP/rollback-macos.sh' '$BACKUP' /"
echo 'Reboot through the prepared 1401 EFI, then run collect-full.sh.'
