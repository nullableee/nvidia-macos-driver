#!/bin/bash
# macOS Tahoe / Recovery collector. Bash 3.2 compatible; no Python or Xcode needed.
# Reads system state and writes a new report directory. Does not install/unload
# drivers, rebuild caches, edit EFI/NVRAM, change sysctls or send data anywhere.
set -u
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
umask 077
if [ "$(uname -s)" != Darwin ]; then
    echo 'Run this script in macOS Tahoe (or Recovery).' >&2
    exit 1
fi
if [ "$EUID" -ne 0 ]; then
    echo 'Run: sudo bash /Volumes/1401/G6MF-Hardware-2026-10-29/collect-macos.sh' >&2
    exit 1
fi
BASE="$(cd "$(dirname "$0")" && pwd -P)" || exit 1
PARENT=${1:-"$BASE"}
case "$PARENT" in /*) ;; *) echo 'Output parent must be an absolute path.' >&2; exit 1;; esac
OUT="$PARENT/macOS-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$OUT" || exit 1
printf 'command\texit_status\ttimed_out\n' > "$OUT/command-status.tsv"
printf 'Report: %s\nKeep Terminal open until COLLECTION COMPLETE.\n' "$OUT"
# Each command has a deadline. Partial output and all failures are retained.
# No background watchdog is left sleeping when the command finishes.
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
run os-version 10 /usr/bin/sw_vers
run kernel 10 /usr/bin/uname -a
run uptime 10 /usr/bin/uptime
run boot-time 10 /usr/sbin/sysctl kern.boottime
run cpu-memory 10 /usr/sbin/sysctl machdep.cpu.brand_string machdep.cpu.family machdep.cpu.model machdep.cpu.stepping hw.memsize hw.ncpu hw.physicalcpu hw.logicalcpu
run system-profiler 90 /usr/sbin/system_profiler -detailLevel full -timeout 60 SPHardwareDataType SPDisplaysDataType SPPCIDataType SPMemoryDataType SPSoftwareDataType
run displays-json 60 /usr/sbin/system_profiler -json -detailLevel full -timeout 45 SPDisplaysDataType
run ioreg-full 60 /usr/sbin/ioreg -l -w 0 -p IOService
# XML is separate: no command prefix, so the result remains parseable as plist.
printf 'Collecting ioreg XML ...\n'
run ioreg-xml-command 60 /bin/bash -c 'exec /usr/sbin/ioreg -a -l -p IOService > "$1"' collector "$OUT/ioreg-full.plist"
run ioreg-device-tree 45 /usr/sbin/ioreg -l -w 0 -p IODeviceTree
run ioreg-accelerators 20 /usr/sbin/ioreg -l -w 0 -r -c IOAccelerator
run ioreg-framebuffers 20 /usr/sbin/ioreg -l -w 0 -r -c IOFramebuffer
run ioreg-pci 30 /usr/sbin/ioreg -l -w 0 -r -c IOPCIDevice
run ioreg-intel-probe 15 /usr/sbin/ioreg -l -w 0 -r -c NMIntelProbe
run ioreg-render-backend 15 /usr/sbin/ioreg -l -w 0 -r -c NVRMRenderBridge
run ioreg-nvrm 15 /usr/sbin/ioreg -l -w 0 -r -c NVRM
run ioreg-intel-panel 15 /usr/sbin/ioreg -l -w 0 -r -c NMIntelFB
run ioreg-agdc 15 /usr/sbin/ioreg -l -w 0 -r -c NVDADeviceControl
run loaded-kexts 45 /usr/bin/kmutil showloaded --list-only
run loaded-kexts-legacy 20 /usr/sbin/kextstat -l
run system-integrity 10 /usr/bin/csrutil status
run authenticated-root 10 /usr/bin/csrutil authenticated-root status
run boot-args 10 /usr/sbin/nvram boot-args
run sip-nvram 10 /usr/sbin/nvram csr-active-config
run gpu-debug-sysctls 15 /usr/sbin/sysctl debug.nvaccel_headless debug.nvaccel_igpu debug.nvaccelfb debug.nvaccel_iop_ok_h4 debug.nvaccel_iop_flip debug.nmintelfb_sample debug.nvaccel_heads_published debug.nvaccel_heads_registered debug.nvaccel_heads_piped debug.nvaccel_surface_gpu_timeouts debug.nvaccel_iop_copy_skip
run agdc-debug-sysctls 15 /usr/sbin/sysctl debug.nvrmfb_agdc debug.nvrmfb_agdc_fbmap debug.nvrmfb_agdc_maxfb debug.nvrmfb_agdc_cmds debug.nvrmfb_agdc_refused debug.nvrmfb_agdc_k5_link debug.nvrmfb_agdc_k5_caps debug.nvrmfb_agdc_k5_why
run disk-layout 20 /usr/sbin/diskutil list
run apfs-layout 20 /usr/sbin/diskutil apfs list
run mounts 10 /sbin/mount
run power-settings 15 /usr/bin/pmset -g custom
run power-assertions 15 /usr/bin/pmset -g assertions
run kernel-messages 20 /sbin/dmesg
run installed-kexts 15 /bin/ls -la /Library/Extensions
run installed-gpu-bundles 15 /bin/ls -la /Library/GPUBundles
run kernel-collections 15 /bin/ls -la /Library/KernelCollections /System/Library/KernelCollections
run installation-receipts 15 /usr/sbin/pkgutil --pkgs
PREDICATE='(process == "kernel" AND (eventMessage CONTAINS[c] "NVRM" OR eventMessage CONTAINS[c] "NVAccel" OR eventMessage CONTAINS[c] "NMIntel" OR eventMessage CONTAINS[c] "WhateverXe" OR eventMessage CONTAINS[c] "TGL" OR eventMessage CONTAINS[c] "IOGraphics" OR eventMessage CONTAINS[c] "GPU" OR eventMessage CONTAINS[c] "framebuffer")) OR process == "WindowServer" OR process == "displaypolicyd" OR process == "kernelmanagerd"'
run graphics-log 90 /usr/bin/log show --last 30m --style syslog --info --predicate "$PREDICATE"
# Inventory actual installed bundle IDs and versions, without executing drivers.
{
    for bundle in /Library/Extensions/*.kext /Library/GPUBundles/*.bundle; do
        [ -f "$bundle/Contents/Info.plist" ] || continue
        printf '\n%s\n' "$bundle"
        /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$bundle/Contents/Info.plist" 2>&1
        /usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$bundle/Contents/Info.plist" 2>&1
    done
} > "$OUT/installed-bundle-versions.txt"
# Copy at most 40 recent graphics/kernel reports, preserving original files.
mkdir -p "$OUT/crashes"
count=0
for dir in /Library/Logs/DiagnosticReports /Library/Logs/DiagnosticReports/Retired; do
    [ -d "$dir" ] || continue
    while IFS= read -r -d '' file; do
        count=$((count + 1))
        [ "$count" -le 40 ] || break
        /bin/cp -p "$file" "$OUT/crashes/$count-${file##*/}" 2>> "$OUT/crash-copy-errors.txt" || true
    done < <(/usr/bin/find "$dir" -maxdepth 1 -type f -mtime -7 \( -iname '*WindowServer*' -o -iname '*.panic' -o -iname '*kernel*' -o -iname '*GPU*' -o -iname '*displaypolicyd*' \) -print0 2>/dev/null)
done
# Preserve accessible logs on the same USB without mounting or modifying EFI.
mkdir -p "$OUT/usb-logs"
for file in "$BASE"/../opencore-*.txt "$BASE"/../G6MF-Remove-Graphics/removed-*/removal.log "$BASE"/../G6MF-Remove-Graphics/removed-*/SUCCESS.txt; do
    [ -f "$file" ] || continue
    parent=${file%/*};parent=${parent##*/}
    /bin/cp -p "$file" "$OUT/usb-logs/$parent-${file##*/}" 2>> "$OUT/usb-copy-errors.txt" || true
done
cat > "$OUT/README-RU.txt" <<'NOTE'
Диагностика G6 MF из macOS/Recovery. Никаких установок, изменений EFI,
NVRAM, sysctl, драйверов или kernel collections скрипт не выполнял.
command-status.tsv содержит exit status и признак таймаута каждой команды.
Отсутствующие команды, sysctl или kext — диагностические данные, не повод
считать весь сбор неудачным. Частичный вывод сохраняется при таймауте.
В Recovery драйверы и IORegistry отличаются от обычной загрузки Tahoe.
SPDisplaysDataType сообщает заявленные возможности Metal, но не проверяет
отрисовку на GPU. Этот сборщик не является тестом ускорения.
В отчёте могут быть серийные номера, UUID, имена пользователей и пути.
Ничего не отправляется в сеть. Для разбора после возврата в Linux нужна
вся папка вместе с command-status.tsv, даже если отдельные команды упали.
NOTE
# Include our own next-boot captures when USB was not mounted during the failed GUI start.
if [ -d /Users/Shared/G6MF-BootReports ]; then
    mkdir -p "$OUT/boot-reports"
    for capture in /Users/Shared/G6MF-BootReports/boot-*; do
        [ -d "$capture" ] || continue
        /bin/cp -R "$capture" "$OUT/boot-reports/" 2>> "$OUT/boot-copy-errors.txt" || true
    done
fi
printf 'Collection finished at %s\n' "$(date)" > "$OUT/COLLECTION-COMPLETE.txt"
/bin/sync
printf '\nCOLLECTION COMPLETE\nSaved: %s\nReturn to Linux and keep this folder on USB 1401.\n' "$OUT"
