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

`tools/merge.py` loads the pinned base in fp16, applies the selected PEFT
adapter, performs a safe merge, and writes `artifacts/merged/`. The export
copies the tokenizer files from the exact pinned base snapshot instead of
allowing the installed Transformers version to rewrite them. This is required
for compatibility with the pinned llama.cpp converter and keeps the tokenizer
identical to the base conversion.

`tools/convert.sh` produced `artifacts/tuned-q8.gguf` with Q8_0 quantization.
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
divergence begins at fp16 merge/save rather than Q8 conversion: Q8 reproduces
eight of ten merged-fp16 answers exactly. This drift is disclosed rather than
treated as adapter-only evidence.

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
the URLs in the manifest remain expected destinations until the owner runs:

```sh
export HF_TOKEN='<write token>'
uv run hf upload sharadja/ghl-support-qlora-t4 artifacts/adapter artifacts/adapter --no-private --token "$HF_TOKEN" --commit-message 'Upload selected adapter'
uv run hf upload sharadja/ghl-support-qlora-t4 artifacts/merged artifacts/merged --token "$HF_TOKEN" --commit-message 'Upload merged fp16 model'
uv run hf upload sharadja/ghl-support-qlora-t4 artifacts/base-q8.gguf artifacts/base-q8.gguf --token "$HF_TOKEN" --commit-message 'Upload base Q8 GGUF'
uv run hf upload sharadja/ghl-support-qlora-t4 artifacts/tuned-q8.gguf artifacts/tuned-q8.gguf --token "$HF_TOKEN" --commit-message 'Upload tuned Q8 GGUF'
uv run hf upload sharadja/ghl-support-qlora-t4 artifacts/manifest.json artifacts/manifest.json --token "$HF_TOKEN" --commit-message 'Upload artifact manifest'
uv run hf repos settings sharadja/ghl-support-qlora-t4 --public --token "$HF_TOKEN"
```

After upload, verify from a clean target directory with
`uv run python tools/fetch_artifacts.py --manifest artifacts/manifest.json --target serve`.
