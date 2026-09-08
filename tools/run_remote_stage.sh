#!/usr/bin/env bash
# Launch with setsid; caller captures stdout/stderr on the network volume.
set -euo pipefail
case "${1:-}" in smoke|train) stage="$1" ;; *) exit 2 ;; esac
cd /workspace/ghl-v3
export HF_HOME=/workspace/hf-cache
export UV_CACHE_DIR=/workspace/uv-cache
export UV_PYTHON_INSTALL_DIR=/workspace/python
export PYTHONUNBUFFERED=1
trap 'stage_status=$?; printf "STAGE_EXIT=%s\n" "$stage_status"' EXIT
uv run --frozen --extra train --python 3.11.11 python tools/run_training_bundle.py "--$stage"
