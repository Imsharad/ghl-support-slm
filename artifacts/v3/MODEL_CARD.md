---
language: en
license: apache-2.0
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
---

# GHL support SLM — v3 candidate03, step120

Experimental customer-support QLoRA adapter on Qwen2.5-1.5B-Instruct at revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. This is the final evaluated artifact,
not candidate04 (which failed development selection).

Training used 216 rewritten Bitext examples and 27 fictional supplied-context
examples, with 54 validation examples. Targets were assistant-authored and
self-reviewed. Rank 16, alpha 32, learning rate 5e-5, 120 updates; the repository
contains the full CUDA config, data lineage, logs and curves. Training used
approximately $0.45 in owner-authorized RunPod credit, a deviation from the
assignment's free-compute constraint.

The evaluated export is Q8_0 served through Ollama. On 106 graded pairs, recorded
passes were 59 base versus 81 tuned, critical failures 11 versus 9, and credential
violations 1 versus 2. The fixed safety gate failed. Judging was post-hoc mixed:
29 human and 77 human-calibrated automated grades; two cases were omitted and
human evidence notes are absent. These are not complete independent human results.
Reference-similarity gains reported for v1 do not belong to this adapter.

The model can invent business policies and request secrets. Use only for local
research and demonstration; it is not qualified for unsupervised customer support.
It has no business database, account access, retrieval or action tools.

Use the exact `configs/prompt-v3.txt` system text and Qwen native chat template.
Greedy decoding, 256 new tokens, 2048 context tokens, seed 42. Extract the adapter
archive at the repository root and run:

```sh
uv sync --frozen --extra serve
uv run --extra serve --with peft==0.20.0 python serve/adapter_v3.py \
  --adapter train/runs/v3-candidate03-runpod/checkpoint-120 \
  --device auto --allow-download --query 'I forgot my password. What should I do?'
```

The README contains the HTTP serving route and raw evaluation evidence. Direct
PEFT output may differ from the Q8 output used for scoring. Artifact hashes and
conversion lineage are in `candidate03-step120-q8_0.gguf.export.json`.
See `LICENSE-QWEN` and `MODEL-NOTICE.txt` for the upstream model license and changes;
Bitext dataset material carries the separate notices under `data/`.
