#!/bin/bash
# Fetch pinned Khronos Vulkan C headers to an isolated user directory.
# No sudo, no Homebrew, no changes to installed macOS drivers.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
TAG="vulkan-sdk-1.4.328.1"
URL="https://github.com/KhronosGroup/Vulkan-Headers.git"
DEST="$HOME/Projects/Vulkan-Headers"
if [[ -f "$DEST/include/vulkan/vulkan.h" ]]; then
    printf 'HEADERS FOUND: %s\n' "$DEST/include"
    if [[ -d "$DEST/.git" ]]; then git -C "$DEST" describe --tags --always --exact-match 2>/dev/null || true; fi
    printf 'NEXT: bash tools/g6mf_descriptor_build_check.sh\n'
    exit 0
fi
if [[ -e "$DEST" ]]; then
    printf 'STOP: %s already exists but does not contain include/vulkan/vulkan.h.\n' "$DEST" >&2
    printf 'Inspect it manually; this tool never overwrites existing directories.\n' >&2
    exit 2
fi
command -v git >/dev/null || { echo "STOP: git is unavailable" >&2; exit 2; }
mkdir -p "$HOME/Projects"
TMP=$(mktemp -d "$HOME/Projects/.vulkan-headers-XXXXXXXX")
cleanup() { [[ -d "$TMP" ]] && rm -rf "$TMP"; }
trap cleanup EXIT
printf 'Cloning official Khronos Vulkan-Headers %s (headers only; no system install)...\n' "$TAG"
git clone -q --depth 1 --single-branch --branch "$TAG" "$URL" "$TMP"
[[ -f "$TMP/include/vulkan/vulkan.h" ]] || { echo "STOP: official tag lacks vulkan/vulkan.h" >&2; exit 3; }
[[ "$(git -C "$TMP" describe --tags --exact-match)" == "$TAG" ]] || { echo "STOP: wrong upstream tag" >&2; exit 3; }
mv "$TMP" "$DEST"
trap - EXIT
printf 'HEADERS READY: %s/include\n' "$DEST"
printf 'TAG: %s\nNEXT: bash tools/g6mf_descriptor_build_check.sh\n' "$TAG"
