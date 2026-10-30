#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
[ "$(uname -s)" = Darwin ] && [ "$(id -u)" = 0 ] || { echo 'Run with sudo bash in Tahoe.';exit 1; }
case "${1:-}" in 0|1) ;; *) echo 'Pass 0 (original scheduling) or 1 (serial LUT).';exit 1;; esac
CONFIG=/Library/NullMoth/g6mf-lut-serial
[ ! -L /Library/NullMoth ] && [ -f "$CONFIG" ] && [ ! -L "$CONFIG" ] && [ ! -L "$CONFIG.new" ] || exit 1
printf '%s\n' "$1" > "$CONFIG.new";chown root:wheel "$CONFIG.new";chmod 644 "$CONFIG.new";mv -f "$CONFIG.new" "$CONFIG"
sync
echo 'Setting saved. Reboot to apply; then run profile-perf.sh.'
