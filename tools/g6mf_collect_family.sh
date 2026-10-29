#!/bin/bash
# Read-only collection of the installed Apple graphics family, Bash 3.2.
# Run in the recovered, working Tahoe session. No driver or EFI changes.
set -eu
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
[ "$(uname -s)" = Darwin ] || { echo 'Run in macOS Tahoe.' >&2; exit 1; }
[ "$(id -u)" = 0 ] || { echo 'Run with sudo bash.' >&2; exit 1; }
BASE=$(cd "$(dirname "$0")" && pwd -P)
OUT="$BASE/family-$(date +%Y%m%d-%H%M%S)-$$"
umask 077
mkdir -p "$OUT"
sw_vers > "$OUT/os-version.txt"
uname -a > "$OUT/kernel.txt"
df -Pk "$OUT" > "$OUT/free-space.txt"
free_kb=$(awk 'END {print $4}' "$OUT/free-space.txt")
case "$free_kb" in ''|*[!0-9]*) echo 'Cannot determine free space.' >&2; exit 1;; esac
[ "$free_kb" -ge 1200000 ] || { echo 'Need 1.2 GB free on the output volume.' >&2; exit 1; }
copy_file() {
 local source=$1 name=$2 bytes
 if [ ! -f "$source" ]; then
  printf 'ABSENT %s\n' "$source" >> "$OUT/files.txt"
  return 0
 fi
 bytes=$(stat -f %z "$source")
 case "$bytes" in ''|*[!0-9]*) echo "Cannot read size: $source" >&2; exit 1;; esac
 [ "$bytes" -le 1073741824 ] || { echo "File exceeds 1 GB: $source" >&2; exit 1; }
 printf 'Copying %s (%s bytes)\n' "$name" "$bytes"
 cp "$source" "$OUT/$name"
 printf '%s %s -> %s\n' "$bytes" "$source" "$name" >> "$OUT/files.txt"
}
for family in IOAcceleratorFamily2 IOGraphicsFamily; do
 bundle="/System/Library/Extensions/$family.kext/Contents"
 copy_file "$bundle/Info.plist" "$family.Info.plist"
 copy_file "$bundle/MacOS/$family" "$family"
done
# The kernel collection preserves the exact implementation if loose kext files
# are absent or only contain link stubs. Do not copy the entire dyld cache.
copy_file /System/Library/KernelCollections/BootKernelExtensions.kc BootKernelExtensions.kc
copy_file /System/Library/KernelCollections/SystemKernelExtensions.kc SystemKernelExtensions.kc
for framework in IOPresentment CoreDisplay; do
 copy_file "/System/Library/PrivateFrameworks/$framework.framework/Versions/A/$framework" "$framework"
done
if [ ! -f "$OUT/IOAcceleratorFamily2" ] && [ ! -f "$OUT/SystemKernelExtensions.kc" ]; then
 echo 'No accelerator executable or system collection found; keep this report.' >&2
 exit 1
fi
(cd "$OUT" && shasum -a 256 ./* > SHA256SUMS)
date > "$OUT/COLLECTION-COMPLETE.txt"
sync
printf 'FAMILY COLLECTION COMPLETE: %s\n' "$OUT"
