#!/usr/bin/env bash
# Development only. Never copy the sealed/fresh final queries to this training pod.
set -euo pipefail
cd /workspace/ghl-v3
export HF_HOME=/workspace/hf-cache
export UV_CACHE_DIR=/opt/ghl-v3-uv-cache
export UV_PROJECT_ENVIRONMENT=/opt/ghl-v3-venv
export UV_PYTHON_INSTALL_DIR=/workspace/python
export PYTHONUNBUFFERED=1
trap 'eval_status=$?; printf "DEVELOPMENT_EXIT=%s\n" "$eval_status"' EXIT
common=(--backend transformers --split dev --input data/processed/v3-candidate03/val.jsonl
        --device cuda --prompt-file configs/prompt-v3.txt --check-complete)
uv run --frozen --extra train --python 3.11.11 python -m eval.run --model base "${common[@]}" \
  --output eval/results/v3/development/base-cuda.jsonl
for checkpoint in 30 60 90 120; do
  uv run --frozen --extra train --python 3.11.11 python -m eval.run --model tuned "${common[@]}" \
    --adapter "train/runs/v3-candidate03-runpod/checkpoint-$checkpoint" \
    --output "eval/results/v3/development/tuned-cuda-$checkpoint.jsonl"
done
