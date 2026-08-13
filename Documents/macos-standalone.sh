#!/bin/sh
# Build a relocatable FreeCAD_BT.app from the pixi env (after install-release).
# That app does not need this git checkout. After you confirm it launches,
# you may delete the clone, build/, and .pixi/ to reclaim ~15–20 GB.
#
# Usage (from repo root, after a working pixi run freecad-release):
#   pixi run install-release
#   ./Documents/macos-standalone.sh
#   open ~/Applications/FreeCAD_BT.app
set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
ENV="$ROOT/.pixi/envs/default"
APP="${HOME}/Applications/FreeCAD_BT.app"
RES="$APP/Contents/Resources"

if [ ! -d "$ENV" ]; then
    echo "No pixi env at $ENV" >&2
    echo "Run: pixi install && pixi run configure-release && pixi run build-release && pixi run install-release" >&2
    exit 1
fi

# install-release puts the app into CONDA_PREFIX (the pixi env).
FREECAD_BIN=""
for candidate in "$ENV/bin/freecad" "$ENV/bin/FreeCAD"; do
    if [ -x "$candidate" ]; then
        FREECAD_BIN=$candidate
        break
    fi
done
if [ -z "$FREECAD_BIN" ]; then
    echo "FreeCAD is not in the pixi env yet. Run: pixi run install-release" >&2
    echo "(pixi run freecad-release uses build/release/bin/FreeCAD; the standalone app needs the install.)" >&2
    exit 1
fi

echo "Using $FREECAD_BIN"
echo "Creating $APP (this copies Qt/OCCT/VTK — several GB, takes a few minutes)..."

mkdir -p "$HOME/Applications"
rm -rf "$APP"
mkdir -p "$RES/bin" "$APP/Contents/MacOS" "$APP/Contents/Resources"

rsync -a --delete \
    --exclude 'include/' \
    --exclude '*.a' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    "$ENV/" "$RES/"

# Keep a small runtime bin, matching the official macOS bundle.
mkdir -p "$RES/bin"
BIN_TMP="$RES/bin_keep"
mkdir -p "$BIN_TMP"
for name in freecad FreeCAD freecadcmd FreeCADCmd ccx python pip gmsh dot unflatten pyside6-rcc; do
    if [ -e "$RES/bin/$name" ] || [ -L "$RES/bin/$name" ]; then
        cp -a "$RES/bin/$name" "$BIN_TMP/" 2>/dev/null || true
    fi
done
# Restore full lib/share/etc from rsync; replace bin with the keepers.
# rsync already copied bin; we trim it.
if [ -d "$RES/bin" ]; then
    rm -rf "$RES/bin"
fi
mv "$BIN_TMP" "$RES/bin"

if [ ! -e "$RES/bin/freecad" ] && [ -e "$RES/bin/FreeCAD" ]; then
    ln -s FreeCAD "$RES/bin/freecad"
fi

FIX="$ROOT/package/rattler-build/scripts/fix_macos_lib_paths.py"
if [ -f "$FIX" ] && [ -d "$RES/lib" ]; then
    echo "Fixing dylib rpaths for a relocatable bundle..."
    python3 "$FIX" "$RES/lib" -r || true
fi

cat > "$APP/Contents/Info.plist" <<EOF
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

cat > "$APP/Contents/MacOS/FreeCAD" <<'EOF'
#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="$(cd "$HERE/../Resources" && pwd)"
export PREFIX
export CONDA_PREFIX="$PREFIX"
export PYTHONHOME="$PREFIX"
export PYTHONPATH="$PREFIX"
export SSL_CERT_FILE="$PREFIX/ssl/cacert.pem"
export GIT_SSL_CAINFO="$PREFIX/ssl/cacert.pem"
if [ -d "$PREFIX/lib" ]; then
    export DYLD_FALLBACK_LIBRARY_PATH="$PREFIX/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
fi
if [ -x "$PREFIX/bin/freecad" ]; then
    exec "$PREFIX/bin/freecad" "$@"
fi
exec "$PREFIX/bin/FreeCAD" "$@"
EOF
chmod +x "$APP/Contents/MacOS/FreeCAD"

if command -v codesign >/dev/null 2>&1; then
    codesign --force --sign - "$APP" >/dev/null 2>&1 || true
fi

echo
echo "Standalone app: $APP"
du -sh "$APP" 2>/dev/null || true
echo
echo "1. Launch it:  open \"$APP\""
echo "2. If that GUI is good, you may delete the checkout and build tree:"
echo "     rm -rf \"$ROOT\""
echo "   That removes git, build/, and .pixi/. Keep $APP."
echo "3. To rebuild later you will need to clone the repo again."
echo
echo "Prefs live outside the app (~/Library/Preferences/FreeCAD or FREECAD_USER_HOME)."
