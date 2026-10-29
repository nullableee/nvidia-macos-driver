#!/bin/bash
# Shader qualification gates the bridge update and next-boot EFI activation.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run: sudo bash next-stage.sh in ordinary Tahoe.';exit 1; }
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
. "$HERE/plan.env"
CFG="$MEDIA/EFI/OC/config.plist"
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
[ "$(hash "$CFG")" = "$BEFORE_CONFIG_SHA" ] || { echo 'Active EFI differs from the measured headless profile; nothing changed.';exit 1; }
[ "$(hash "$MEDIA/$STAGED_EFI/OC/config.plist")" = "$AFTER_CONFIG_SHA" ] || { echo 'Staged EFI mismatch; nothing changed.';exit 1; }
OUT="$HERE/next-$(date +%Y%m%d-%H%M%S)-$$";mkdir "$OUT"
TEST=$(mktemp -d /var/tmp/g6mf-shader.XXXXXX)
trap 'rm -rf "$TEST"' EXIT
cp "$HERE/shader-probe" "$TEST/shader-probe";chmod 755 "$TEST/shader-probe"
echo 'Waiting 10 seconds, then testing NVIDIA compute shaders (up to four minutes)...'
sleep 10
set +e
"$TEST/shader-probe" 2>&1 | tee "$OUT/shader.txt"
status=${PIPESTATUS[0]}
set -e
printf '%s\n' "$status" > "$OUT/shader-status.txt"
bash "$HERE/collect-macos.sh" "$OUT"
if [ "$status" != 0 ] || ! grep -q '^SHADER PASS:' "$OUT/shader.txt"; then
 echo 'SHADER TEST FAILED. Bridge and EFI were not changed. Return to Linux with this report.'
 exit 1
fi
echo 'Shader passed. Installing the graphics bridge update...'
bash "$HERE/install-bridge-update.sh" 2>&1 | tee "$OUT/bridge-update.txt"
if [ -f "$HERE/capture-boot.sh" ]; then
 bash "$HERE/capture-boot.sh" --install | tee "$OUT/capture-install.txt"
fi
# All native KC checks must finish before selecting the bridge EFI.
[ "$(hash "$CFG")" = "$BEFORE_CONFIG_SHA" ] || { echo 'EFI changed during testing; new bridge remains disabled.';exit 1; }
[ ! -e "$MEDIA/$BACKUP_EFI" ] || { echo 'EFI backup destination already exists; activation stopped.';exit 1; }
mv "$MEDIA/EFI" "$MEDIA/$BACKUP_EFI"
if ! mv "$MEDIA/$STAGED_EFI" "$MEDIA/EFI"; then
 mv "$MEDIA/$BACKUP_EFI" "$MEDIA/EFI"
 echo 'EFI activation failed; headless profile restored.';exit 1
fi
printf '%s\n' "$BACKUP_EFI" > "$HERE/bridge-active.txt"
sync
echo 'NEXT STAGE READY. Allow updated extensions if macOS requests it.'
echo 'Reboot through USB 1401, then run collect-bridge.sh.'
echo 'Do not run sysctl debug.nvaccelfb manually: NVRM will attempt arming at boot.'
