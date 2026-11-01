#!/bin/bash
# Sequoia 15.8.2 (24H232), G6MF 0.4.7 only. No EFI, kexts or system Apple binaries touched.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.15/bin
export LC_ALL=C
umask 077
HERE=$(cd "$(dirname "$0")" && pwd -P)
MODE=${1:-check}
PLUGIN=/Library/GPUBundles/NVMTLDriver.bundle
BINARY=$PLUGIN/Contents/MacOS/NVMTLDriver
BASE=/Users/Shared/G6MF-Backups
POINTER=/Library/NullMoth/g6mf-seriallut-sequoia-backup
SERIAL=/Library/NullMoth/g6mf-lut-serial
LIMIT=/Library/NullMoth/g6mf-lut-limit
EXPECTED_METAL_TEXT=b4f197bdca3c281947e00a84c5bbd98af11037543a76c1d75218b7ce193f1686
PYTHON=$(command -v python3 || true)
die(){ echo "STOP: $*" >&2; exit 1; }
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ] || die 'Only x86_64 macOS.'
[ "$(sw_vers -buildVersion)" = 24H232 ] || die 'Only Sequoia 15.8.2 / build 24H232. No changes made.'
[ -n "$PYTHON" ] || die 'Python3 unavailable.'
[ "$(id -u)" -eq 0 ] || die 'Run with sudo.'
for x in /Library/GPUBundles /Library/NullMoth "$BASE" "$PLUGIN" "$BINARY" "$SERIAL" "$LIMIT" "$POINTER"; do
    [ ! -L "$x" ] || die "Refusing symlink: $x"
done
[ -d /Library/NullMoth ] && [ -d /Library/GPUBundles ] || die 'NullMoth runtime not installed.'
[ ! -e "$SERIAL" ] || [ -f "$SERIAL" ] || die 'Invalid serial policy type.'
[ ! -e "$LIMIT" ] || [ -f "$LIMIT" ] || die 'Invalid LUT policy type.'

write_setting(){
    local target=$1 value=$2 temp
    temp=$(mktemp /Library/NullMoth/.seriallut.XXXXXX)
    printf '%s\n' "$value" > "$temp"
    chown root:wheel "$temp";chmod 644 "$temp"
    mv -f "$temp" "$target"
}
restore_settings(){
    local folder=$1
    if [ -f "$folder/serial.present" ]; then
        cp -p "$folder/serial.config" "$SERIAL"
    else
        rm -f "$SERIAL"
    fi
    if [ -f "$folder/limit.present" ]; then
        cp -p "$folder/limit.config" "$LIMIT"
    else
        rm -f "$LIMIT"
    fi
}
trusted_backup(){
    [ -f "$POINTER" ] || die "Backup pointer missing: $POINTER"
    local folder
    folder=$(cat "$POINTER")
    case "$folder" in /Users/Shared/G6MF-Backups/seriallut-sequoia-*) ;; *) die 'Invalid backup path.';; esac
    [ -d "$folder" ] && [ ! -L "$folder" ] && [ -f "$folder/READY" ] || die "Backup missing: $folder"
    [ "$(stat -f '%u:%Lp' "$folder")" = 0:700 ] || die 'Backup ownership or permissions incorrect.'
    printf '%s\n' "$folder"
}
if [ "$MODE" = status ]; then
    echo "OS build: $(sw_vers -buildVersion)"
    echo "Serial policy: $(cat "$SERIAL" 2>/dev/null || echo absent)"
    echo "LUT limit policy: $(cat "$LIMIT" 2>/dev/null || echo absent)"
    echo "Installed executable: $BINARY"
    [ ! -f "$POINTER" ] || echo "Rollback backup: $(cat "$POINTER")"
    exit 0
fi
if [ "$MODE" = disable ]; then
    [ -f "$POINTER" ] || die 'No Sequoia Serial LUT installation recorded.'
    write_setting "$SERIAL" 0
    sync
    echo 'SERIAL LUT DISABLED for next WindowServer launch. Reboot. Metal 0.4.7 unchanged.'
    exit 0
fi
if [ "$MODE" = enable ]; then
    [ -f "$POINTER" ] || die 'No Sequoia Serial LUT installation recorded.'
    [ -d "$PLUGIN" ] || die 'Metal bundle missing.'
    write_setting "$SERIAL" 1
    sync
    echo 'SERIAL LUT ENABLED for next WindowServer launch. Reboot.'
    exit 0
fi
if [ "$MODE" = restore ]; then
    BACKUP=$(trusted_backup)
    [ -d "$BACKUP/original.bundle" ] || die 'Original Metal bundle not found.'
    codesign --verify --strict "$BACKUP/original.bundle" || die 'Backup failed signature check.'
    [ -d "$PLUGIN" ] || die 'Active Metal bundle missing; use Recovery to copy backup.'
    WORK=$(mktemp -d /Library/GPUBundles/.g6mf-serial-restore.XXXXXX)
    trap 'rm -rf "$WORK"' EXIT
    ditto "$BACKUP/original.bundle" "$WORK/restored.bundle"
    codesign --verify --strict "$WORK/restored.bundle" || die 'Staged restore signature failed.'
    mv "$PLUGIN" "$WORK/replaced.bundle"
    if ! mv "$WORK/restored.bundle" "$PLUGIN"; then
        mv "$WORK/replaced.bundle" "$PLUGIN" || true
        die 'Restore move failed.'
    fi
    if ! codesign --verify --strict "$PLUGIN"; then
        mv "$PLUGIN" "$WORK/failed.bundle"
        mv "$WORK/replaced.bundle" "$PLUGIN" || die 'CRITICAL: old bundle not restored; inspect backup.'
        die 'Restored bundle failed signature check; active bundle rolled back.'
    fi
    restore_settings "$BACKUP"
    rm -f "$POINTER"
    sync
    echo 'RESTORED original Metal 0.4.7 bundle and LUT settings. Reboot.'
    exit 0
fi
case "$MODE" in check|install) ;; *) die 'Usage: sudo bash install.sh check|install|status|disable|enable|restore';; esac
[ ! -f "$POINTER" ] || die 'Existing Serial LUT backup pointer; inspect or restore before reinstalling.'
[ -d "$PLUGIN" ] && [ -f "$BINARY" ] || die 'Installed Metal bundle is missing.'
[ "$(stat -f '%u' "$PLUGIN")" = 0 ] || die 'Installed Metal bundle not root-owned.'
[ ! -e "$PLUGIN/Contents/MacOS/NVMTLDriver.g6mf-original" ] || die 'A different Metal wrapper is already installed.'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PLUGIN/Contents/Info.plist")" = com.nullmoth.NVMTLDriver ] || die 'Unexpected Metal bundle identifier.'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$PLUGIN/Contents/Info.plist")" = 0.4.7 ] || die 'Expected installed G6MF Metal 0.4.7.'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$PLUGIN/Contents/Info.plist")" = NVMTLDriver ] || die 'Unexpected executable.'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Library/Extensions/NVAccel.kext/Contents/Info.plist)" = 0.1.8 ] || die 'Expected NVAccel 0.1.8.'
[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Library/Extensions/NMIntelFB.kext/Contents/Info.plist)" = 0.1.4 ] || die 'Expected NMIntelFB 0.1.4.'
[ "$(sysctl -n debug.nvaccel_igpu 2>/dev/null)" = 1 ] || die 'Intel muxless bridge is not active.'
codesign --verify --strict "$PLUGIN" || die 'Current Metal bundle signature invalid.'
"$PYTHON" "$HERE/macho_text.py" "$BINARY" --expected "$EXPECTED_METAL_TEXT" || die 'Unexpected Metal 0.4.7 binary.'
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS) || die 'Kit integrity mismatch.'
"$PYTHON" "$HERE/prepare.py" --verify-only || die 'CoreDisplay source audit missing or invalid.'
[ -d "$HERE/build" ] || die 'Run python3 prepare.py first to build x86_64 files.'
"$PYTHON" - "$HERE/build" <<'PY' || die 'Build manifest invalid.'
from pathlib import Path
import hashlib,json,sys
base=Path(sys.argv[1]); m=json.loads((base/'manifest.json').read_text())
sys.path.insert(0,str(base.parent))
from macho_validate import validate_file
assert m['audit']['uuid']=='37573E08-0E1B-3981-988C-0AFBCA6C9AA7'
assert m['audit']['macos_build']=='24H232'
for n,k in [('NVMTLDriver',8),('serial-probe',2),('lut-probe',2)]:
 b=(base/n).read_bytes()
 assert hashlib.sha256(b).hexdigest()==m['artifacts'][n],n
 validate_file(base/n,k)
print('BUILD MANIFEST PASS')
PY
WORK=$(mktemp -d /Library/GPUBundles/.g6mf-serial-candidate.XXXXXX)
BACKUP='';CHANGING=0;COMMITTED=0
finish(){
    local rc=$?
    trap - EXIT
    if [ "$CHANGING" = 1 ] && [ "$COMMITTED" = 0 ]; then
        echo 'Installation or probe failed; rolling back Metal bundle and policies.' >&2
        if [ -d "$WORK/previous.bundle" ]; then
            [ ! -d "$PLUGIN" ] || mv "$PLUGIN" "$WORK/failed.bundle" || true
            mv "$WORK/previous.bundle" "$PLUGIN" || echo "CRITICAL: original bundle saved in $BACKUP/original.bundle" >&2
        fi
        [ -z "$BACKUP" ] || restore_settings "$BACKUP" || true
        rm -f "$POINTER" || true
        echo 'Rolled back; no reboot required after failed check.' >&2
    fi
    rm -rf "$WORK"
    exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
CANDIDATE=$WORK/candidate.bundle
ditto "$PLUGIN" "$CANDIDATE"
M=$CANDIDATE/Contents/MacOS
# The installed Metal 0.4.7 executable was previously the main binary of
# NVMTLDriver.bundle. Its existing signature seals that bundle's Info.plist.
# Merely RENAMING that executable makes the old bundle-linked signature fail
# verification when codesign discovers it as a nested subcomponent.
# Re-sign it OUTSIDE a bundle as standalone Mach-O, then embed and sign the
# outer candidate. This follows Apple's nested-code inside-out ordering.
mv "$M/NVMTLDriver" "$WORK/metal-original-standalone" || die 'Cannot stage original Metal executable.'
codesign --force --sign - "$WORK/metal-original-standalone" || die 'Cannot standalone-sign original Metal executable.'
codesign --verify --strict "$WORK/metal-original-standalone" || die 'Standalone Metal executable signature failed.'
"$PYTHON" "$HERE/macho_text.py" "$WORK/metal-original-standalone" --expected "$EXPECTED_METAL_TEXT" || die 'Original Metal code changed while re-signing.'
mv "$WORK/metal-original-standalone" "$M/NVMTLDriver.g6mf-original" || die 'Cannot embed signed Metal executable.'
cp "$HERE/build/NVMTLDriver" "$M/NVMTLDriver"
chmod 755 "$M/NVMTLDriver" "$M/NVMTLDriver.g6mf-original"
chown -R root:wheel "$CANDIDATE"
chmod -R go-w,a+rX "$CANDIDATE"
codesign --force --sign - "$CANDIDATE" || die 'Candidate signing failed.'
codesign --verify --strict "$M/NVMTLDriver.g6mf-original" || die 'Embedded original Metal signature failed.'
codesign --verify --deep --strict "$CANDIDATE" || die 'Candidate nested signature check failed.'
"$PYTHON" "$HERE/macho_text.py" "$M/NVMTLDriver.g6mf-original" --expected "$EXPECTED_METAL_TEXT"
echo 'CHECK PASS: exact Sequoia CoreDisplay site, Metal 0.4.7 and wrapper bundle verified.'
if [ "$MODE" = check ]; then
    echo 'NOT INSTALLED. Run: sudo bash install.sh install'
    exit 0
fi
[ ! -L "$BASE" ] || die 'Backup base is a symlink.'
if [ ! -d "$BASE" ]; then mkdir -m 700 "$BASE"; chown root:wheel "$BASE"; fi
[ "$(stat -f '%u:%Lp' "$BASE")" = 0:700 ] || die 'Backup base must be root-owned mode 700.'
BACKUP=$(mktemp -d "$BASE/seriallut-sequoia-$(date +%Y%m%d-%H%M%S).XXXXXX")
chmod 700 "$BACKUP";chown root:wheel "$BACKUP"
ditto "$PLUGIN" "$BACKUP/original.bundle"
codesign --verify --strict "$BACKUP/original.bundle" || die 'Backup failed integrity check.'
if [ -f "$SERIAL" ]; then touch "$BACKUP/serial.present";cp -p "$SERIAL" "$BACKUP/serial.config";fi
if [ -f "$LIMIT" ]; then touch "$BACKUP/limit.present";cp -p "$LIMIT" "$BACKUP/limit.config";fi
cp "$HERE/install.sh" "$BACKUP/restore.sh"
chmod 700 "$BACKUP/restore.sh"
sw_vers -buildVersion > "$BACKUP/macos-build"
printf 'G6MF Sequoia Serial LUT original Metal 0.4.7\n' > "$BACKUP/READY"
printf '%s\n' "$BACKUP" > "$POINTER"
chown root:wheel "$POINTER";chmod 600 "$POINTER"
CHANGING=1
mv "$PLUGIN" "$WORK/previous.bundle"
mv "$CANDIDATE" "$PLUGIN"
write_setting "$LIMIT" 1024
write_setting "$SERIAL" 1
codesign --verify --strict "$PLUGIN" || die 'Live bundle code signature failed.'
run_probe(){
    local name=$1 seconds=$2;shift 2
    local log=$WORK/$name.log pid rc
    echo "PROBE: $name"
    "$@" > "$log" 2>&1 & pid=$!
    SECONDS=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$SECONDS" -ge "$seconds" ]; then
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -KILL "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            tail -30 "$log"
            die "$name timed out"
        fi
        sleep 1
    done
    if ! wait "$pid"; then
        tail -40 "$log";die "$name failed"
    fi
    tail -8 "$log"
}
run_probe serial 60 "$HERE/build/serial-probe"
run_probe lut-and-shader 240 "$HERE/build/lut-probe"
sync
COMMITTED=1;CHANGING=0
echo 'SERIAL LUT V9 READY for Sequoia 24H232; reboot with existing USB OpenCore.'
echo "BACKUP: $BACKUP"
echo "RESTORE: sudo bash '$BACKUP/restore.sh' restore"
echo "DISABLE for next reboot: sudo bash '$BACKUP/restore.sh' disable"
echo 'EFI, kexts, NVIDIA firmware and Apple CoreDisplay binaries unchanged.'
