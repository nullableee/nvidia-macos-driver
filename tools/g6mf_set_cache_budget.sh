#!/bin/bash
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin;export PATH
[ "$(id -u)" = 0 ] || exit 1
ROOT=/Library/NullMoth
CONFIG=$ROOT/g6mf-surface-cache-mb
[ -d "$ROOT" ] && [ ! -L "$ROOT" ] && [ "$(stat -f %u "$ROOT")" = 0 ] && [ ! -L "$CONFIG" ] || exit 1
case "${1:-}" in
64|128)
 temp=$(mktemp "$ROOT/.g6mf-cache.XXXXXX")
 trap 'rm -f "$temp"' EXIT
 printf '%s\n' "$1" > "$temp";chown root:wheel "$temp";chmod 644 "$temp";mv -f "$temp" "$CONFIG"
 ;;
absent) [ ! -e "$CONFIG" ] || { [ -f "$CONFIG" ] && rm "$CONFIG"; };;
*) exit 1;;
esac
