#!/bin/bash
# Read-only networking and Bluetooth report, Bash 3.2.
set -u
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
LC_ALL=C;export LC_ALL
[ "$(uname -s)" = Darwin ] && [ "$EUID" = 0 ] || { echo 'Run with sudo bash in Tahoe.';exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd -P)
OUT="$HERE/network-$(date +%Y%m%d-%H%M%S)-$$";umask 077;mkdir "$OUT" || exit 1
printf 'command\texit_status\ttimed_out\n' > "$OUT/command-status.tsv"
run() {
    local name="$1" limit="$2" pid start timed rc
    shift 2
    printf 'Collecting %s ...\n' "$name"
    {
        printf 'Command:'
        printf ' %q' "$@"
        printf '\n\n'
    } > "$OUT/$name.txt"
    "$@" >> "$OUT/$name.txt" 2>&1 &
    pid=$!
    start=$SECONDS
    timed=no
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$((SECONDS - start))" -ge "$limit" ]; then
            timed=yes
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -KILL "$pid" 2>/dev/null || true
            break
        fi
        sleep 1
    done
    rc=0
    wait "$pid" || rc=$?
    printf '%s\t%s\t%s\n' "$name" "$rc" "$timed" >> "$OUT/command-status.tsv"
    if [ "$rc" -ne 0 ] || [ "$timed" = yes ]; then
        printf '  %s: status %s, timeout %s; continuing.\n' "$name" "$rc" "$timed"
    fi
    return 0
}
run os-version 10 sw_vers
run boot-state 10 sysctl kern.safeboot kern.bootargs
run boot-nvram 10 nvram boot-args
run loaded-kexts 15 kmutil showloaded
run bluetooth 40 system_profiler SPBluetoothDataType
run usb 30 system_profiler SPUSBDataType
run hardware-ports 15 networksetup -listallhardwareports
run network-services 15 networksetup -listallnetworkservices
run interfaces 15 ifconfig -a
run network-state 15 scutil --nwi
run bluetooth-usb 20 ioreg -p IOUSB -l -w0
run bluetooth-host 15 ioreg -r -c IOBluetoothHCIController -l -w0
run realtek 15 ioreg -r -c RTL8111 -l -w0
run network-log 25 log show --last 5m --style compact --predicate 'process == "bluetoothd" OR process == "bluetool" OR eventMessage CONTAINS[c] "IntelFirmware" OR eventMessage CONTAINS[c] "RealtekRTL8111"'
sync
echo "NETWORK COLLECTION COMPLETE: $OUT"
