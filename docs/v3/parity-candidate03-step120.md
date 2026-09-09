# GGUF tokenizer and prompt-path parity

Verified: 2026-09-08 21:10:14 IST
Verdict: **PASS**

## Artifact

- Base model revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- Ollama model tag: `ghl-support-v3-c03-s120`
- Prompt file: `configs/prompt-v3.txt` (file SHA-256 `fb45ab8d4a58a83fb3d0541abb350bbe6ee20a666c1b5703ea0c771f029b82ce`)
- llama.cpp converter commit: `6a1a922d269908a29cbd4b49c27e6a8e7fd10fae`
- Quantization: `Q8_0`
- File: `artifacts/v3/candidate03-step120-q8_0.gguf`
- Size: 1,646,572,608 bytes
- SHA-256: `06d865f722bda7e6abd250cfab01e61c5806369cf42207b557e2c6f2e27f1240`

The GGUF was produced by `tools/artifacts/convert.sh`, which validates the pinned llama.cpp checkout and uses its isolated uv-created converter environment.

## 5-item parity check

`tokenizer_match` compares Hugging Face token IDs with the pinned llama.cpp `llama-tokenize` binary for the exact rendered prompt. `answer_match` compares generated token IDs from Ollama `/api/generate` with `raw: true` against Ollama `/api/chat`, both using greedy decoding and the same rendered item.

| Item | Prompt tokens | Tokenizer IDs | Answer tokens | Raw vs chat |
|---|---:|---|---:|---|
| dv-001 | 261 | match | 49 | match |
| dv-002 | 252 | match | 70 | match |
| dv-003 | 254 | match | 49 | match |
| dv-004 | 262 | match | 67 | match |
| dv-005 | 261 | match | 54 | match |

The exact specified prompt is supplied as the system turn. This compares tokenizer IDs and raw-vs-chat generation on the same GGUF; it does not claim numerical equivalence between the HF weights and their quantized export. Ollama remained running after verification.
