#!/bin/sh
# Create a Finder/Dock .app that launches this pixi release build.
# Does NOT copy FreeCAD into /Applications by default (that needs a standalone
# bundle). Default destination is ~/Applications/FreeCAD_BT.app (user-writable).
#
# Usage:
#   ./Documents/macos-app.sh
#   ./Documents/macos-app.sh --system     # also copy to /Applications (sudo)
#   ./Documents/macos-app.sh --print
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
BIN="$ROOT/build/release/bin/FreeCAD"
DEST="${HOME}/Applications/FreeCAD_BT.app"
SYSTEM_COPY=0
PRINT_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --system) SYSTEM_COPY=1 ;;
        --print) PRINT_ONLY=1 ;;
        -h|--help)
            echo "Usage: $0 [--system] [--print]"
            echo "  Creates ~/Applications/FreeCAD_BT.app pointing at:"
            echo "    $BIN"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

if [ "$PRINT_ONLY" -eq 1 ]; then
    echo "binary: $BIN"
    echo "app:    $DEST"
    echo "exists: $([ -x "$BIN" ] && echo yes || echo no)"
    exit 0
fi

if [ ! -x "$BIN" ]; then
    echo "No release binary at $BIN" >&2
    echo "Build first: pixi run configure-release && pixi run build-release" >&2
    exit 1
fi

mkdir -p "$HOME/Applications"
rm -rf "$DEST"
mkdir -p "$DEST/Contents/MacOS" "$DEST/Contents/Resources"

cat > "$DEST/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleExecutable</key>
	<string>FreeCAD</string>
	<key>CFBundleIdentifier</key>
	<string>org.freecad.FreeCAD</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>FreeCAD_BT</string>
	<key>CFBundleDisplayName</key>
	<string>FreeCAD_BT</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>26.3.0</string>
	<key>CFBundleVersion</key>
	<string>26.3.0</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSRequiresAquaSystemAppearance</key>
	<false/>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>
</dict>
</plist>
EOF

cat > "$DEST/Contents/MacOS/FreeCAD" <<EOF
#!/bin/bash
ROOT="$ROOT"
export PREFIX="\$ROOT/.pixi/envs/default"
if [ -d "\$PREFIX" ]; then
    export CONDA_PREFIX="\$PREFIX"
    export PATH="\$PREFIX/bin:\$PATH"
fi
exec "\$ROOT/build/release/bin/FreeCAD" "\$@"
EOF
chmod +x "$DEST/Contents/MacOS/FreeCAD"

# Ad-hoc sign so Gatekeeper on recent macOS will launch a local .app
if command -v codesign >/dev/null 2>&1; then
    codesign --force --sign - "$DEST" >/dev/null 2>&1 || true
fi

echo "Created $DEST"
echo "This is a launcher. It still needs this git checkout and build/release."
echo "Open it with: open \"$DEST\""

if [ "$SYSTEM_COPY" -eq 1 ]; then
    echo "Copying to /Applications/FreeCAD_BT.app (may ask for your password)..."
    sudo rsync -a --delete "$DEST/" /Applications/FreeCAD_BT.app/
    echo "Installed /Applications/FreeCAD_BT.app"
fi
