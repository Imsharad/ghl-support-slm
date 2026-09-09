# Base-model GGUF conversion and parity

Verified: 2026-09-05 23:54:42 IST
Verdict: **PASS**

## Artifact

- Base model revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- llama.cpp converter commit: `6a1a922d269908a29cbd4b49c27e6a8e7fd10fae`
- Quantization: `Q8_0`
- File: `artifacts/base-q8.gguf`
- Size: 1,646,572,704 bytes
- SHA-256: `eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5`

The GGUF was produced by `tools/artifacts/convert.sh`, which validates the pinned llama.cpp checkout and uses its isolated uv-created converter environment.

## Five-item parity check

`tokenizer_match` compares Hugging Face token IDs with the pinned llama.cpp `llama-tokenize` binary for the exact rendered prompt. `answer_match` compares generated token IDs from Ollama `/api/generate` with `raw: true` against Ollama `/api/chat`, both using greedy decoding and the same rendered item.

| Item | Prompt tokens | Tokenizer IDs | Answer tokens | Raw vs chat |
|---|---:|---|---:|---|
| dv-001 | 86 | match | 114 | match |
| dv-002 | 77 | match | 67 | match |
| dv-003 | 79 | match | 123 | match |
| dv-004 | 87 | match | 89 | match |
| dv-005 | 86 | match | 14 | match |

The Modelfile applies `configs/prompts/prompt.txt` once as the system turn and uses the native Qwen2.5 ChatML markers. Ollama remained running after verification for downstream evaluation tasks.
