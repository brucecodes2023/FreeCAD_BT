#!/usr/bin/env bash
# Cloud Agent install script for FreeCAD.
#
# Prepares a fully buildable FreeCAD checkout:
#   1. Installs the pixi package manager (single static binary) onto PATH.
#   2. Fetches git submodules and the conda-forge toolchain + dependencies.
#   3. Configures, builds, and installs FreeCAD (release preset).
#
# Must stay idempotent: pixi resolves the locked environment, and ccache keeps
# rebuilds incremental, so re-running only refreshes what actually changed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 1. Ensure pixi is available on PATH (installed once, reused afterwards).
if ! command -v pixi >/dev/null 2>&1; then
  export PIXI_NO_PATH_UPDATE=1
  export PIXI_HOME="${PIXI_HOME:-$HOME/.pixi}"
  curl -fsSL https://pixi.sh/install.sh | bash
  sudo install -m 0755 "$PIXI_HOME/bin/pixi" /usr/local/bin/pixi
fi

pixi --version

# 2. Fetch submodules and materialize the locked conda-forge environment.
pixi run initialize

# 3. Configure, build, and install FreeCAD (release matches CI: sub_buildPixi.yml).
pixi run configure-release
pixi run build-release
pixi run install-release

echo "FreeCAD install complete."
