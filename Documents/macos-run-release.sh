#!/bin/bash
# Launch the pixi release build with a Qt plugin tree macOS 27 will actually load.
#
# .pixi plugin dylibs are marked hidden (com.apple.provenance), so Qt skips them.
# Copying them is fine; running install_name_tool on them is not — that invalidates
# the code signature and macOS SIGKILLs FreeCAD (Code Signature Invalid).
set -e
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/.pixi/envs/default"
RUNTIME="$ROOT/build/release/qt-runtime"
PLUGINS="$RUNTIME/lib/qt6/plugins"
BIN="$ROOT/build/release/bin/FreeCAD"
SRC_PLUGINS="$PREFIX/lib/qt6/plugins"

if [ ! -x "$BIN" ]; then
    echo "No release binary at $BIN" >&2
    echo "Build first: pixi run configure-release && pixi run build-release" >&2
    exit 1
fi
if [ ! -f "$SRC_PLUGINS/platforms/libqcocoa.dylib" ]; then
    echo "Qt cocoa plugin missing in $SRC_PLUGINS" >&2
    exit 1
fi

mkdir -p "$RUNTIME/lib/qt6"

# Point @loader_path/../../../ (from .../lib/qt6/plugins/platforms) at a lib/
# that contains the real Qt dylibs, without rewriting plugin Mach-O headers.
for item in "$PREFIX/lib/"*; do
    name=$(basename "$item")
    [ "$name" = "qt6" ] && continue
    ln -sfn "$item" "$RUNTIME/lib/$name"
done
for item in "$PREFIX/lib/qt6/"*; do
    name=$(basename "$item")
    [ "$name" = "plugins" ] && continue
    ln -sfn "$item" "$RUNTIME/lib/qt6/$name"
done

mkdir -p "$PLUGINS"
rsync -a --delete "$SRC_PLUGINS/" "$PLUGINS/"
chflags -R nohidden "$PLUGINS" 2>/dev/null || true

# Conda Qt6 reads qt6.conf next to the executable.
cat > "$ROOT/build/release/bin/qt6.conf" <<EOF
[Paths]
Prefix = $PREFIX
Plugins = $PLUGINS
Libraries = $PREFIX/lib
LibraryExecutables = $PREFIX/lib/qt6
Binaries = $PREFIX/lib/qt6/bin
ArchData = $PREFIX/lib/qt6
Data = $PREFIX/share/qt6
Translations = $PREFIX/share/qt6/translations
EOF
cp "$ROOT/build/release/bin/qt6.conf" "$ROOT/build/release/bin/qt.conf"

export CONDA_PREFIX="$PREFIX"
export PATH="$PREFIX/bin:$PATH"
export QT_PLUGIN_PATH="$PLUGINS"
unset QT_QPA_PLATFORM_PLUGIN_PATH

if [ -z "$FREECAD_USER_HOME" ]; then
    export FREECAD_USER_HOME="$HOME/freecad-modern-cad-fresh"
    mkdir -p "$FREECAD_USER_HOME"
fi

exec "$BIN" "$@"
