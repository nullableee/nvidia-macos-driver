#!/bin/bash
# Update the selected G6MF components, testing candidate and live Auxiliary KC.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run as root in Tahoe.'; exit 1; }
case "$(sw_vers -productVersion)" in 26.*) ;; *) exit 1;; esac
(cd "$HERE" && shasum -a 256 --strict --quiet -c SHA256SUMS)
. "$HERE/plan.env"
EXT=/Library/Extensions; KC=/Library/KernelCollections/AuxiliaryKernelExtensions.kc
OLD="$EXT/NMIntelFB.kext"
oldsha=$(shasum -a 256 "$OLD/Contents/MacOS/NMIntelFB" | awk '{print $1}')
case "$oldsha" in
 "$NEW_KEXT_SHA") echo 'Corrected NMIntelFB is present; revalidating and publishing its Auxiliary KC.';;
 "$OLD_KEXT_SHA") ;;
 *) echo 'STOP: installed NMIntelFB differs from the tested stack.'; exit 1;;
esac
PAIR=0
if [ -n "${NEW_ACCEL_SHA:-}" ]; then
 PAIR=1
 current_accel=$(shasum -a 256 "$EXT/NVAccel.kext/Contents/MacOS/NVAccel" | awk '{print $1}')
 case "$current_accel" in "$OLD_ACCEL_SHA"|"$NEW_ACCEL_SHA") ;; *) echo 'STOP: NVAccel differs from tested stack.';exit 1;; esac
fi
ADDAGDC=0
if [ -n "${NEW_AGDC_SHA:-}" ]; then
 ADDAGDC=1
 current_agdc=$(shasum -a 256 "$EXT/NVRMAGDC.kext/Contents/MacOS/NVRMAGDC" | awk '{print $1}')
 case "$current_agdc" in "$OLD_AGDC_SHA"|"$NEW_AGDC_SHA") ;; *) echo 'STOP: NVRMAGDC differs from tested stack.';exit 1;; esac
fi
[ -f "$KC" ] || { echo 'STOP: existing Auxiliary KC missing.'; exit 1; }
umask 077
WORK=$(mktemp -d /var/tmp/g6mf-bridge.XXXXXX)
CHANGING=0; BACKUP=''
finish() {
 local status=$?
 trap - EXIT
 if [ "$CHANGING" = 1 ]; then
  echo 'Update failed; restoring saved graphics components and Auxiliary KC.' >&2
  if ! /bin/bash "$HERE/rollback-bridge-macos.sh" "$BACKUP" /; then
   echo "RESTORATION FAILED; retain backup $BACKUP and do not reboot blindly." >&2
  fi
 fi
 rm -rf "$WORK"
 exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
mkdir "$WORK/repo"
for bundle in "$EXT"/*.kext; do
 [ -d "$bundle" ] || continue
 [ "${bundle##*/}" != NMIntelFB.kext ] || continue
 if [ "$PAIR" = 1 ] && [ "${bundle##*/}" = NVAccel.kext ]; then continue; fi
 if [ "$ADDAGDC" = 1 ] && [ "${bundle##*/}" = NVRMAGDC.kext ]; then continue; fi
 ditto "$bundle" "$WORK/repo/${bundle##*/}"
done
ditto "$HERE/NMIntelFB.kext" "$WORK/repo/NMIntelFB.kext"
if [ "$PAIR" = 1 ]; then ditto "$HERE/NVAccel.kext" "$WORK/repo/NVAccel.kext";fi
if [ "$ADDAGDC" = 1 ]; then ditto "$HERE/NVRMAGDC.kext" "$WORK/repo/NVRMAGDC.kext";fi
chown -R root:wheel "$WORK/repo";chmod -R go-w "$WORK/repo"
KARG=(--allow-missing-kdk)
[ ! -f /System/Library/Kernels/kernel ] || KARG+=(--kernel /System/Library/Kernels/kernel)
build_collection() {
 local repository=$1 candidate=$2 log=$3
 kmutil create -n aux --volume-root / "${KARG[@]}" \
  -B /System/Library/KernelCollections/BootKernelExtensions.kc \
  -S /System/Library/KernelCollections/SystemKernelExtensions.kc \
  --repository "$repository" -A "$candidate" -z > "$log" 2>&1 || { tail -30 "$log";return 1; }
 [ -s "$candidate" ] || return 1
 kmutil inspect -a x86_64 --show-kext-uuids -A "$candidate" > "$log.inspect" 2>&1 || return 1
 if [ -n "${NEW_ACCEL_UUID:-}" ];then
  grep -Fiq "$NEW_ACCEL_UUID" "$log.inspect" || { echo 'Candidate NVAccel UUID missing';return 1; }
 fi
 local name
 for name in NVRM NVAccel NVRMFB NVRMAGDC NMIntelFB; do
  grep -Eq "com\.nullmoth\.$name([^A-Za-z0-9]|$)" "$log.inspect" || { echo "Missing $name from candidate KC";return 1; }
 done
}
echo 'Checking corrected framebuffer against the current Tahoe kernel...'
build_collection "$WORK/repo" "$WORK/test.kc" "$HERE/bridge-kmutil-test.log"
BASE=/Users/Shared/G6MF-Backups
[ -d "$BASE" ] && [ ! -L "$BASE" ] && [ "$(stat -f '%u:%Lp' "$BASE")" = 0:700 ] || { echo 'Expected root-owned mode-700 G6MF backup directory from the full install.';exit 1; }
BACKUP=$(mktemp -d "$BASE/before-bridge-$(date +%Y%m%d-%H%M%S).XXXXXX")
ditto "$OLD" "$BACKUP/NMIntelFB.kext"
if [ "$PAIR" = 1 ]; then
 ditto "$EXT/NVAccel.kext" "$BACKUP/NVAccel.kext"
 if [ -d /Library/NullMoth/kexts/26 ]; then ditto /Library/NullMoth/kexts/26 "$BACKUP/accel-cache-26";fi
 touch "$BACKUP/pair-update"
fi
if [ "$ADDAGDC" = 1 ]; then
 ditto "$EXT/NVRMAGDC.kext" "$BACKUP/NVRMAGDC.kext"
 touch "$BACKUP/agdc-update"
fi
cp -p "$KC" "$BACKUP/AuxiliaryKernelExtensions.kc"
cp "$HERE/rollback-bridge-macos.sh" "$BACKUP/rollback-bridge-macos.sh"
sw_vers -buildVersion > "$BACKUP/macos-build"
touch "$BACKUP/READY"
printf '%s\n' "$BACKUP" > "$HERE/last-bridge-backup.txt"
CHANGING=1
rm -rf "$OLD";ditto "$WORK/repo/NMIntelFB.kext" "$OLD"
chown -R root:wheel "$OLD";chmod -R 755 "$OLD"
[ "$(shasum -a 256 "$OLD/Contents/MacOS/NMIntelFB" | awk '{print $1}')" = "$NEW_KEXT_SHA" ]
if [ "$PAIR" = 1 ]; then
 rm -rf "$EXT/NVAccel.kext";ditto "$WORK/repo/NVAccel.kext" "$EXT/NVAccel.kext"
 chown -R root:wheel "$EXT/NVAccel.kext";chmod -R 755 "$EXT/NVAccel.kext"
 [ "$(shasum -a 256 "$EXT/NVAccel.kext/Contents/MacOS/NVAccel" | awk '{print $1}')" = "$NEW_ACCEL_SHA" ]
 if [ -d /Library/NullMoth/kexts/26 ]; then
  rm -rf /Library/NullMoth/kexts/26/NVAccel.kext
  ditto "$EXT/NVAccel.kext" /Library/NullMoth/kexts/26/NVAccel.kext
  (cd /Library/NullMoth/kexts/26 && find NVAccel.kext -type f -exec shasum -a 256 '{}' \;) > /Library/NullMoth/kexts/26/SHA256SUMS
 fi
fi
if [ "$ADDAGDC" = 1 ]; then
 rm -rf "$EXT/NVRMAGDC.kext";ditto "$WORK/repo/NVRMAGDC.kext" "$EXT/NVRMAGDC.kext"
 chown -R root:wheel "$EXT/NVRMAGDC.kext";chmod -R 755 "$EXT/NVRMAGDC.kext"
 [ "$(shasum -a 256 "$EXT/NVRMAGDC.kext/Contents/MacOS/NVRMAGDC" | awk '{print $1}')" = "$NEW_AGDC_SHA" ]
fi
build_collection "$EXT" "$WORK/live.kc" "$HERE/bridge-kmutil-live.log"
cp -p "$WORK/live.kc" "$KC.g6mf-new"
mv -f "$KC.g6mf-new" "$KC"
CHANGING=0
echo "BRIDGE UPDATE INSTALLED. Backup: $BACKUP"
echo 'The new framebuffer will load after reboot; no kext unload attempted.'
