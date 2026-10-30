#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || exit 1
value=${1:?Use 0 (control), 1024, 2048, 4096 or 16384}
case "$value" in 0|1024|2048|4096|16384) ;; *) exit 1;;esac
[ -f /Library/GPUBundles/NVMTLDriver.bundle/Contents/MacOS/NVMTLDriver.g6mf-original ] || { echo 'LUT experiment is not installed.';exit 1; }
CONFIG=/Library/NullMoth/g6mf-lut-limit
[ ! -L "$CONFIG" ] && [ ! -L "$CONFIG.new" ] || exit 1
printf '%s\n' "$value" > "$CONFIG.new"
chown root:wheel "$CONFIG.new";chmod 644 "$CONFIG.new";mv -f "$CONFIG.new" "$CONFIG"
sync
echo "LUT limit $value saved. Reboot to apply; 0 is the original-limit control."
