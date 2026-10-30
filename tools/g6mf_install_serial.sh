#!/bin/bash
# Upgrade the measured v7/v8 Metal wrapper with opt-in serial LUT scheduling.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
LC_ALL=C;export LC_ALL
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in Tahoe.';exit 1; }
[ "$(sw_vers -buildVersion)" = 25G241 ] || { echo 'Only measured Tahoe 25G241 is supported.';exit 1; }
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
. "$HERE/identity.env"
PLUGIN=/Library/GPUBundles/NVMTLDriver.bundle
BIN="$PLUGIN/Contents/MacOS/NVMTLDriver"
CONFIG=/Library/NullMoth/g6mf-lut-limit
SERIAL=/Library/NullMoth/g6mf-lut-serial
[ ! -L /Library/NullMoth ] && [ ! -L "$SERIAL" ] || exit 1
[ "$(cat "$CONFIG")" = 1024 ] || { echo "Expected measured LUT 1024.";exit 1; }
[ ! -L "$PLUGIN" ] && [ ! -L "$CONFIG" ] || exit 1
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PLUGIN/Contents/Info.plist")" = com.nullmoth.NVMTLDriver ] || exit 1
[ -f "$PLUGIN/Contents/MacOS/NVMTLDriver.g6mf-original" ] || { echo 'Expected working v7/v8 wrapper.';exit 1; }
[ ! -L "$BIN" ] && [ ! -L "$PLUGIN/Contents/MacOS/NVMTLDriver.g6mf-original" ] || exit 1
# codesign changes signatures; verify executable text fingerprints instead.
# These exact offsets/sizes come from the packaged, measured thin Mach-O files.
check_text() {
 local file=$1 offset=$2 size=$3 expected=$4
 [ "$(dd if="$file" bs=1 skip="$offset" count="$size" 2>/dev/null | shasum -a 256 | awk '{print $1}')" = "$expected" ]
}
check_text "$BIN" "$WRAPPER_TEXT_OFFSET" "$WRAPPER_TEXT_SIZE" "$WRAPPER_TEXT_SHA" || { echo 'Unknown current wrapper code; nothing changed.';exit 1; }
check_text "$PLUGIN/Contents/MacOS/NVMTLDriver.g6mf-original" "$ORIGINAL_TEXT_OFFSET" "$ORIGINAL_TEXT_SIZE" "$ORIGINAL_TEXT_SHA" || { echo 'Unknown original plugin code; nothing changed.';exit 1; }
codesign --verify --strict "$PLUGIN"
for entry in 'NMIntelFB 0.1.4' 'NVAccel 0.1.4'; do
 name=${entry% *};version=${entry#* }
 [ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "/Library/Extensions/$name.kext/Contents/Info.plist")" = "$version" ] || { echo 'Expected the measured v8 stack.';exit 1; }
done
BASE=/Users/Shared/G6MF-Backups
[ ! -L "$BASE" ] || exit 1
if [ -d "$BASE" ];then [ "$(stat -f '%u:%Lp' "$BASE")" = 0:700 ] || exit 1;else mkdir -m 700 "$BASE";fi
umask 077
WORK=$(mktemp -d /var/tmp/g6mf-lut.XXXXXX)
BACKUP='';CHANGING=0
STAGED=/Library/GPUBundles/.g6mf-lut-candidate-$$
finish() {
 status=$?;trap - EXIT
 if [ "$CHANGING" = 1 ];then
  echo 'LUT installation/probe failed; restoring original Metal bundle.' >&2
  bash "$HERE/rollback-lut.sh" "$BACKUP" / || { echo "RESTORE FAILED: $BACKUP" >&2;status=1; }
 fi
 rm -rf "$WORK" "$STAGED";exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
CANDIDATE="$WORK/NVMTLDriver.bundle"
ditto "$PLUGIN" "$CANDIDATE"
cp "$HERE/NVMTLDriver" "$CANDIDATE/Contents/MacOS/NVMTLDriver"
chmod 755 "$CANDIDATE/Contents/MacOS/"*
codesign --force --sign - "$CANDIDATE"
codesign --verify --strict "$CANDIDATE"
BACKUP=$(mktemp -d "$BASE/before-lut-$(date +%Y%m%d-%H%M%S).XXXXXX")
ditto "$PLUGIN" "$BACKUP/NVMTLDriver.bundle"
[ ! -f "$CONFIG" ] || cp -p "$CONFIG" "$BACKUP/lut-limit"
[ ! -f "$SERIAL" ] || cp -p "$SERIAL" "$BACKUP/lut-serial"
touch "$BACKUP/serial-config-managed"
cp "$HERE/rollback-lut.sh" "$BACKUP/rollback-lut.sh"
sw_vers -buildVersion > "$BACKUP/macos-build"
touch "$BACKUP/READY"
printf '%s\n' "$BACKUP" > "$HERE/last-lut-backup.txt"
[ ! -e "$STAGED" ] || exit 1
ditto "$CANDIDATE" "$STAGED"
chown -R root:wheel "$STAGED";chmod -R go-w,a+rX "$STAGED"
CHANGING=1
mv "$PLUGIN" "$BACKUP/live-original.bundle"
mv "$STAGED" "$PLUGIN"
[ ! -L "$SERIAL.new" ] || exit 1
printf '1\n' > "$SERIAL.new"
chown root:wheel "$SERIAL.new";chmod 644 "$SERIAL.new";mv -f "$SERIAL.new" "$SERIAL"
cp "$HERE/serial-probe" "$WORK/serial-probe";chmod 755 "$WORK/serial-probe"
echo 'Testing process-local data import binding, serial iterations and original dispatch delegation...'
"$WORK/serial-probe" > "$HERE/serial-probe.txt" 2>&1 || { cat "$HERE/serial-probe.txt";exit 1; }
cat "$HERE/serial-probe.txt"
grep -q '^SERIAL HOOK PASS:' "$HERE/serial-probe.txt"
cp "$HERE/lut-probe" "$WORK/lut-probe";chmod 755 "$WORK/lut-probe"
echo 'Testing the loader, the 1024 limit and NVIDIA compute in a separate process (up to four minutes)...'
"$WORK/lut-probe" > "$HERE/lut-probe.txt" 2>&1 || { cat "$HERE/lut-probe.txt";exit 1; }
cat "$HERE/lut-probe.txt"
grep -q '^LUT CAP: 1024$' "$HERE/lut-probe.txt"
grep -q '^SHADER PASS:' "$HERE/lut-probe.txt"
bash "$HERE/capture-boot.sh" --install
CHANGING=0
sync
echo 'SERIAL LUT READY. Reboot, then run profile-perf.sh. EFI, kexts and LUT width unchanged.'
