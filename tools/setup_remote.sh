#!/usr/bin/env bash
# Rebuildable dependencies use local disk; training artifacts stay on /workspace.
set -euo pipefail
cd /workspace/ghl-v3
export UV_CACHE_DIR=/opt/ghl-v3-uv-cache
export UV_PROJECT_ENVIRONMENT=/opt/ghl-v3-venv
export UV_PYTHON_INSTALL_DIR=/workspace/python
trap 'setup_status=$?; printf "SETUP_EXIT=%s\n" "$setup_status"' EXIT
uv sync --frozen --extra train --python 3.11.11
"$UV_PROJECT_ENVIRONMENT/bin/python" --version
