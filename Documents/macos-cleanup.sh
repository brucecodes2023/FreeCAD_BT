#!/bin/sh
# Reclaim disk after a successful Mac launch. Safe by default: does not delete
# the release binary the thin ~/Applications/FreeCAD_BT.app still needs.
#
# Usage:
#   ./Documents/macos-cleanup.sh           # ccache, debug build, pyc
#   ./Documents/macos-cleanup.sh --objects # also delete .o files (must rebuild to link again)
#   ./Documents/macos-cleanup.sh --build   # delete entire build/ (thin .app will break until rebuild)
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

MODE=safe
for arg in "$@"; do
    case "$arg" in
        --objects) MODE=objects ;;
        --build) MODE=build ;;
        -h|--help)
            echo "Usage: $0 [--objects|--build]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

echo "Repo: $ROOT"
du -sh .git build .pixi 2>/dev/null || true

if command -v pixi >/dev/null 2>&1; then
    pixi run ccache -C >/dev/null 2>&1 || true
fi
rm -rf build/debug
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true

if [ "$MODE" = "objects" ]; then
    echo "Removing compile objects under build/release (binaries kept)..."
    find build/release -name '*.o' -delete 2>/dev/null || true
    find build/release -name '*.d' -delete 2>/dev/null || true
fi

if [ "$MODE" = "build" ]; then
    echo "Removing entire build/ directory. The thin .app will not launch until you rebuild."
    rm -rf build
fi

echo "After cleanup:"
du -sh .git build .pixi 2>/dev/null || true
echo "A standalone (relocatable) .app is the only way to delete .pixi + the clone."
echo "That path is package/rattler-build/osx/create_bundle.sh after pixi run install-release."
