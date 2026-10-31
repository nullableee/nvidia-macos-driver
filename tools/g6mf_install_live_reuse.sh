#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(id -u)" = 0 ] || { echo 'Run with sudo bash';exit 1; }
[ "$(sw_vers -buildVersion)" = 25G241 ] || exit 1
[ "$(sysctl -n kern.safeboot)" = 0 ] && [ "$(sysctl -n debug.nvrmfb_agdc)" = 1 ] || exit 1
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
. "$HERE/identity.env"
PLUGIN=/Library/GPUBundles/NVMTLDriver.bundle
CONFIG=/Library/NullMoth/g6mf-live-surface-reuse
BASE=/Users/Shared/G6MF-Backups
for dir in /Library/GPUBundles /Library/NullMoth "$PLUGIN" "$CONFIG" "$BASE";do [ ! -L "$dir" ] || exit 1;done
[ "$(stat -f '%u:%Lp' "$BASE")" = 0:700 ] || exit 1
[ "$(cat /Library/NullMoth/g6mf-lut-limit)" = 1024 ] && [ "$(cat /Library/NullMoth/g6mf-lut-serial)" = 1 ] || exit 1
for item in NVMTLDriver NVMTLDriver.g6mf-original;do
 current=$(shasum -a 256 "$PLUGIN/Contents/MacOS/$item" | awk '{print $1}')
 if [ "$item" = NVMTLDriver ];then expected=$OLD_WRAPPER_SHA;else expected=$OLD_ORIGINAL_SHA;fi
 [ "$current" = "$expected" ] || { echo 'Installed Metal bundle changed; stopped.';exit 1; }
done
codesign --verify --strict "$PLUGIN"
feature=1
if [ -f "$HERE/feature-mode.txt" ];then feature=$(cat "$HERE/feature-mode.txt");fi
case "$feature" in 1|2) ;; *) echo 'Invalid feature mode';exit 1;; esac
umask 077
WORK=$(mktemp -d /var/tmp/g6mf-live-reuse.XXXXXX)
BACKUP='';CHANGING=0
STAGED=/Library/GPUBundles/.g6mf-live-reuse-$$
finish(){
 local rc=$?
 trap - EXIT
 if [ "$CHANGING" = 1 ];then
  echo 'Candidate failed; restoring saved Metal bundle.' >&2
  bash "$HERE/restore.sh" "$BACKUP" || { echo "RESTORE FAILED; retain $BACKUP" >&2;rc=1; }
 fi
 rm -rf "$WORK" "$STAGED"
 exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
run_probe(){
 local name=$1 limit=$2 pid start rc=0
 shift 2
 "$@" > "$HERE/$name.txt" 2>&1 & pid=$!;start=$SECONDS
 while kill -0 "$pid" 2>/dev/null;do
  if [ "$((SECONDS-start))" -ge "$limit" ];then kill -TERM "$pid" 2>/dev/null || true;sleep 1;kill -KILL "$pid" 2>/dev/null || true;wait "$pid" 2>/dev/null || true;echo "Probe timeout: $name";return 1;fi
  sleep 1
 done
 wait "$pid" || rc=$?
 tail -12 "$HERE/$name.txt"
 return "$rc"
}
CANDIDATE="$WORK/NVMTLDriver.bundle"
ditto "$PLUGIN" "$CANDIDATE"
cp "$HERE/NVMTLDriver.g6mf-original" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
if [ -f "$HERE/release-version.txt" ];then
 release=$(cat "$HERE/release-version.txt")
 [[ "$release" =~ ^0\.4\.[0-9]+$ ]] || { echo 'Invalid package release';exit 1; }
 /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $release" "$CANDIDATE/Contents/Info.plist"
 /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $release" "$CANDIDATE/Contents/Info.plist"
fi
codesign --force --sign - "$CANDIDATE"
codesign --verify --strict "$CANDIDATE"
if [ "$feature" = 2 ];then
 run_probe hold 90 "$HERE/hold-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
 run_probe bounded-stress 90 env G6MF_TEST_REUSE=2 "$HERE/stress-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
 run_probe pixels 90 env G6MF_TEST_REUSE=2 G6MF_DROP_ANCHOR=1 G6MF_FULL=1 "$HERE/pixel-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
 run_probe half-pixels 90 env G6MF_TEST_REUSE=2 G6MF_DROP_ANCHOR=1 G6MF_HALF=1 "$HERE/pixel-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
else
 run_probe pixels 90 env G6MF_TEST_REUSE=1 G6MF_FULL=1 "$HERE/pixel-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
 run_probe half-pixels 90 env G6MF_TEST_REUSE=1 G6MF_HALF=1 "$HERE/pixel-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
fi
run_probe swizzle 90 env G6MF_TEST_REUSE="$feature" G6MF_TEST_METADATA=1 "$HERE/swizzle-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
run_probe stress 90 "$HERE/stress-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
if [ -f "$HERE/descriptor-probe" ];then
 run_probe descriptor-control 90 "$HERE/descriptor-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 0
 run_probe descriptor 90 "$HERE/descriptor-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe descriptor-sampler 90 env G6MF_SAMPLER_CHURN=1 "$HERE/descriptor-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe descriptor-mask 90 env G6MF_MASK_CHURN=1 "$HERE/descriptor-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe descriptor-buffer 90 env G6MF_BUFFER_CHURN=1 "$HERE/descriptor-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render 90 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-sampler 90 env G6MF_SAMPLER_CHURN=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-mask 90 env G6MF_MASK_CHURN=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-fetch-zero 90 env G6MF_FETCH_INPUT=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-fetch-sampler 90 env G6MF_FETCH_INPUT=1 G6MF_SAMPLER_CHURN=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-fetch-mask 90 env G6MF_FETCH_INPUT=1 G6MF_MASK_CHURN=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 run_probe render-fetch-live 90 env G6MF_FETCH_INPUT=1 G6MF_FETCH_LIVE=1 "$HERE/render-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 1
 if [ -f "$HERE/cache-probe" ];then
  run_probe cache64 180 "$HERE/cache-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 64
  run_probe cache128 180 "$HERE/cache-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original" 128
 fi
 run_probe queue 90 "$HERE/queue-probe" "$CANDIDATE/Contents/MacOS/NVMTLDriver.g6mf-original"
fi
BACKUP=$(mktemp -d "$BASE/before-live-reuse-$(date +%Y%m%d-%H%M%S).XXXXXX")
ditto "$PLUGIN" "$BACKUP/NVMTLDriver.bundle"
[ ! -f "$CONFIG" ] || cp -p "$CONFIG" "$BACKUP/feature-config"
sw_vers -buildVersion > "$BACKUP/macos-build"
cp "$HERE/restore.sh" "$BACKUP/restore.sh"
touch "$BACKUP/READY"
printf '%s\n' "$BACKUP" > "$HERE/last-backup.txt"
[ ! -e "$STAGED" ] || exit 1
ditto "$CANDIDATE" "$STAGED"
chown -R root:wheel "$STAGED";chmod -R go-w,a+rX "$STAGED"
CHANGING=1
mv "$PLUGIN" "$BACKUP/live-original.bundle"
mv "$STAGED" "$PLUGIN"
printf '%s\n' "$feature" > "$WORK/feature-config"
chown root:wheel "$WORK/feature-config";chmod 644 "$WORK/feature-config"
mv "$WORK/feature-config" "$CONFIG"
run_probe lut-shader 240 "$HERE/lut-probe"
grep -q '^LUT CAP: 1024$' "$HERE/lut-shader.txt"
grep -q '^SHADER PASS:' "$HERE/lut-shader.txt"
run_probe serial 90 "$HERE/serial-probe"
grep -q '^SERIAL HOOK PASS:' "$HERE/serial.txt"
sysctl -n kern.boottime > "$HERE/installed-during-boot.txt"
chmod 644 "$HERE/installed-during-boot.txt"
CHANGING=0
sync
echo "GRAPHICS ${release:-live-reuse} READY. Reboot, verify Glass, then run profile-perf.sh."
