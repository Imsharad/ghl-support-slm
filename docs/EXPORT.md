# Exported model artifacts

Verified 2026-09-06 10:42 IST on an Apple M1 Pro with Ollama 0.24.0.

## Source identity

- Base: `Qwen/Qwen2.5-1.5B-Instruct`
- Base revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- Selected adapter: `train/runs/local-t4/checkpoint-400`
- Adapter SHA-256: `1a94ede7dfec05998d129dc6d2bcbd5c890c861ba755cc3322e67098dae966bb`
- llama.cpp converter commit: `6a1a922d269908a29cbd4b49c27e6a8e7fd10fae`
- Tokenizer SHA-256: `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`
- Prompt SHA-256: `d738ddb811ab3d1bb0d0804b2f1a9978b48435f9adb518159b5360ff7bd53443`

`tools/artifacts/merge.py` loads the pinned base in fp16, applies the selected PEFT
adapter, performs a safe merge, and writes `artifacts/merged/`. The export
copies the tokenizer files from the exact pinned base snapshot instead of
allowing the installed Transformers version to rewrite them. This is required
for compatibility with the pinned llama.cpp converter and keeps the tokenizer
identical to the base conversion.

`tools/artifacts/convert.sh` produced `artifacts/tuned-q8.gguf` with Q8_0 quantization.
`serve/Modelfile` is byte-identical to `serve/Modelfile.base` after the `FROM`
line and imports as Ollama model `ghl-support`.

## Parity and drift

All checks use the first ten rows of `eval/dev.jsonl`, greedy decoding, the same
system prompt, a 256-token limit, and the existing adapter answers from
`eval/results/dev-400-raw.jsonl`.

| Comparison | Exact answers | Rubric-level change |
|---|---:|---|
| Selected adapter vs merged fp16 | 3/10 | `dv-008` changes from critical fail to plain fail; the other nine keep their pass/critical class |
| Selected adapter fp16 vs tuned Q8 in Ollama | 2/10 | `dv-008` changes from critical fail to plain fail; the other nine keep their pass/critical class |
| Merged fp16 vs tuned Q8 in Ollama | 8/10 | None; only `dv-003` and `dv-004` differ in wording |

The fp16 merge therefore did not meet the hoped-for token-exact parity. The
gap is caused by the two dtype paths, not by evidence of an incorrect merge:
`eval/run.py` loads the pinned base with `dtype="auto"`, whose model config
selects bfloat16, and applies the LoRA without merging; `tools/artifacts/merge.py` loads
the base in float16 before merging and saving it. Those two rounding paths can
change greedy token choices. Q8 then reproduces eight of ten merged-fp16
answers exactly, so the quantization step contributes little additional drift.

## Served-model metrics

The served-model comparison uses the same 270 sampled test IDs and 270 distinct
groups on every side. Base Q8 and tuned Q8 both run through Ollama with greedy
decoding; the fp16 column is D3's unmerged bfloat16-base-plus-adapter result and
is included to show export drift. Metrics were generated at 2026-09-06 11:03
IST with 2,000 paired group-bootstrap resamples, seed 42.

| Metric | Base Q8, Ollama | Tuned adapter, bf16 path (D3) | Tuned Q8, Ollama | Tuned Q8 minus base Q8, 95% CI |
|---|---:|---:|---:|---|
| ROUGE-L F1 mean | 0.2153 | 0.3659 | 0.3667 | +0.1515 [+0.1380, +0.1662] |
| MiniLM cosine mean | 0.6741 | 0.8315 | 0.8288 | +0.1547 [+0.1335, +0.1766] |
| Placeholder rate | 0.0000 | 0.0000 | 0.0000 | |
| Truncated rate | 0.1037 | 0.0259 | 0.0222 | |
| Mean generated tokens | 107.8 | 91.8 | 91.8 | |

The tuned Q8 result retains the bf16 adapter's reference-overlap gain on the
same serving path as the base, so precision and runtime differences do not
explain the headline improvement. These automated metrics show that tuning
learned the Bitext response register; they do not establish correctness or
safety, which remain the job of the sealed blind evaluation.

Files: `eval/results/base-test-sample-raw.jsonl`,
`eval/results/tuned-q8-test-raw.jsonl`, and
`eval/results/tuned-q8-test-auto.json`. The base-side recomputation was written
to `.scratch/e1b-base-auto.json`; its headline values exactly match the existing
`eval/results/base-test-sample-auto.json`, which was not modified.

## Artifact hashes

- `artifacts/base-q8.gguf`: `eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5`
- `artifacts/tuned-q8.gguf`: `03ba912ba0e87269d58556769d17d922262aa2c84a3f91fdc1a40455fd8bf2a9`
- `artifacts/adapter/adapter_model.safetensors`: `1a94ede7dfec05998d129dc6d2bcbd5c890c861ba755cc3322e67098dae966bb`
- `artifacts/merged/model-00001-of-00002.safetensors`: `47eb843b311706ca2dca15c9215c084e2d909249ef1bfbac51704afe3ed408cc`
- `artifacts/merged/model-00002-of-00002.safetensors`: `5a8c1f85ddcf8555dfff83608964e0f31eecd44723a72bebb6889e96ac4dfa3d`

The complete per-file inventory, sizes, hashes, version pins, and expected Hub
URLs are in `artifacts/manifest.json`.

## Hub upload

The local export is complete, but `HF_TOKEN` was not present at export time, so
the URLs in the manifest remain expected destinations until the owner runs the commands below. The Hub namespace is `seekingtroooth`, the account that owns the write token; a `sharadja` namespace does not exist on the Hub. Never paste the token into this file or any tracked file; keep it in the environment or in `hf auth login`:

```sh
export HF_TOKEN='<write token>'
uv run hf upload seekingtroooth/ghl-support-qlora-t4 artifacts/adapter artifacts/adapter --no-private --token "$HF_TOKEN" --commit-message 'Upload selected adapter'
uv run hf upload seekingtroooth/ghl-support-qlora-t4 artifacts/merged artifacts/merged --token "$HF_TOKEN" --commit-message 'Upload merged fp16 model'
uv run hf upload seekingtroooth/ghl-support-qlora-t4 artifacts/base-q8.gguf artifacts/base-q8.gguf --token "$HF_TOKEN" --commit-message 'Upload base Q8 GGUF'
uv run hf upload seekingtroooth/ghl-support-qlora-t4 artifacts/tuned-q8.gguf artifacts/tuned-q8.gguf --token "$HF_TOKEN" --commit-message 'Upload tuned Q8 GGUF'
uv run hf upload seekingtroooth/ghl-support-qlora-t4 artifacts/manifest.json artifacts/manifest.json --token "$HF_TOKEN" --commit-message 'Upload artifact manifest'
uv run hf repos settings seekingtroooth/ghl-support-qlora-t4 --public --token "$HF_TOKEN"
```

After upload, verify from a clean target directory with
`uv run python tools/artifacts/fetch_artifacts.py --manifest artifacts/manifest.json --target serve`.
