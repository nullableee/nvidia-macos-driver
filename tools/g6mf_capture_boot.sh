#!/bin/bash
# One next-boot capture; never writes display registers or changes GPU sysctls.
set -u
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
HERE=$(cd "$(dirname "$0")" && pwd -P)
RUNTIME=/Library/NullMoth/g6mf-capture
LAUNCH=/Library/LaunchDaemons/com.nullmoth.g6mf-capture.plist
if [ "${1:-}" = --install ]; then
 [ "$(id -u)" = 0 ] || exit 1
 [ ! -L "$RUNTIME" ] || exit 1
 mkdir -p "$RUNTIME" || exit 1
 cp "$0" "$RUNTIME/capture-boot.sh" && cp "$HERE/map-probe" "$RUNTIME/map-probe" || exit 1
 basename "$HERE" > "$RUNTIME/kit-name.txt" || exit 1
 chown -R root:wheel "$RUNTIME" && chmod -R 755 "$RUNTIME" || exit 1
 cat > "$LAUNCH" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.nullmoth.g6mf-capture</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>/Library/NullMoth/g6mf-capture/capture-boot.sh</string></array>
<key>RunAtLoad</key><true/>
<key>ProcessType</key><string>Background</string>
</dict></plist>
PLIST
 chown root:wheel "$LAUNCH" && chmod 644 "$LAUNCH" || exit 1
 echo 'Next-boot diagnostic installed; it is not started in the current session.'
 exit 0
fi
umask 077
OUT=/Users/Shared/G6MF-BootReports/boot-$(date +%Y%m%d-%H%M%S)-$$
mkdir -p "$OUT" || exit 1
# Removing the plist makes this a one-boot job; retain helper and captured data.
rm -f "$LAUNCH"
nvram boot-args > "$OUT/boot-args.txt" 2>&1
sysctl kern.boottime > "$OUT/boot-time.txt" 2>&1
run() {
 local limit=$1 file=$2 pid start rc;shift 2
 "$@" > "$OUT/$file" 2>&1 & pid=$!;start=$SECONDS
 while kill -0 "$pid" 2>/dev/null; do
  if [ "$((SECONDS-start))" -ge "$limit" ]; then
   kill -TERM "$pid" 2>/dev/null;sleep 1;kill -KILL "$pid" 2>/dev/null;break
  fi
  sleep 1
 done
 rc=0;wait "$pid" || rc=$?
 printf '%s status=%s\n' "$file" "$rc" >> "$OUT/status.txt"
}
mirror() {
 local name kit
 name=$(cat "$RUNTIME/kit-name.txt" 2>/dev/null) || name=NullMoth-G6MF-Bridge-v4
 case "$name" in NullMoth-G6MF-Bridge-v[0-9]*) ;; *) return;; esac
 case "$name" in */*) return;; esac
 kit=/Volumes/1401/$name
 if [ -d "$kit" ]; then
  mkdir -p "$kit/boot-reports"
  cp -R "$OUT" "$kit/boot-reports/" 2>> "$OUT/copy-errors.txt" || true
 fi
}
mirror
for n in 1 2 3 4 5 6; do
 run 5 "state-$n.txt" sysctl debug.nvaccelfb debug.nvaccel_heads_published debug.nvaccel_heads_registered debug.nvaccel_heads_piped debug.nvaccel_iop_ok_h4 debug.nvaccel_iop_enter debug.nvaccel_iop_validate debug.nvaccel_iop_fail debug.nvrmfb_agdc debug.nvrmfb_agdc_fbmap debug.nvrmfb_agdc_maxfb debug.nvrmfb_agdc_k5_link debug.nvrmfb_agdc_k5_caps debug.nvrmfb_agdc_k5_why
 run 16 "map-$n.txt" "$RUNTIME/map-probe"
 run 5 "framebuffer-$n.txt" ioreg -l -w 0 -r -c NMIntelFB
 run 5 "agdc-$n.txt" ioreg -l -w 0 -r -c NVDADeviceControl
 mirror
 sleep 5
done
run 30 graphics-log.txt log show --last 15m --style syslog --info --predicate '(process == "kernel" AND (eventMessage CONTAINS[c] "NVRM" OR eventMessage CONTAINS[c] "NVAccel" OR eventMessage CONTAINS[c] "NMIntel")) OR process == "WindowServer" OR process == "ReportCrash"'
date > "$OUT/CAPTURE-COMPLETE.txt"
mirror
sync
