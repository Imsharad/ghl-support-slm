# Serving and benchmark

Both routes use the exact system prompt in `configs/prompts/prompt.txt`, the native Qwen2.5 ChatML template, greedy decoding, a 2,048-token context, and at most 256 new tokens. Ollama is the HTTP serving route used for evaluation. The Transformers route is a dependency-light local fallback that needs neither Ollama nor bitsandbytes.

## Ollama HTTP route

From the repository root, import and serve the base Q8 artifact:

```sh
ollama create ghl-base -f serve/Modelfile.base
ollama serve
```

If the Ollama desktop service is already running, the second command is unnecessary. Verify the OpenAI-compatible endpoint in another shell:

```sh
curl --fail-with-body http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ghl-base","messages":[{"role":"user","content":"I forgot my password and cannot sign in. What should I do?"}],"temperature":0,"max_tokens":256,"stream":false}'
```

Run one query through the repository wrapper, or run its fixed password-reset safety check:

```sh
uv run python serve/inference.py --backend ollama --model ghl-base \
  --query "How do I update the shipping address on an order?"
uv run python serve/inference.py --backend ollama --model ghl-base --self-test
```

`--self-test` always uses the password-reset demo query. It fails on an empty answer or language asking the customer to disclose a password, full payment-card detail, PIN, CVV, or security code.

The tuned Q8 artifact is available as `ghl-support`, created from `serve/Modelfile`; substitute that tag in the commands above to serve it.

## Plain Transformers route

The fallback loads `artifacts/merged/` when a merged checkpoint is present. Until then it loads the exact pinned base revision from the local Hugging Face cache. It applies the tokenizer's native chat template and greedy generation directly on CPU or MPS:

```sh
uv run python serve/inference.py --backend transformers --device cpu --self-test
uv run python serve/inference.py --backend transformers --device mps \
  --query "How can I reset my password?"
```

This is a command-line fallback, not the assignment's HTTP route. The Ollama endpoint remains the served artifact and the source of reported benchmark numbers.

## Benchmark method

The reproducible benchmark command is:

```sh
uv run python serve/bench.py --requests 30 --concurrency 1 --check --model ghl-base
```

The script unloads the model with `keep_alive: 0`, times the first cold request, performs five unreported warmups, then sends the first 30 fixed rows of `eval/dev.jsonl` serially. It records every request's prompt tokens, generated tokens, end-to-end latency, Ollama generation rate, and native timing fields. `--check` fails if a request fails, a field is missing, or the requested row count is not present. Results are written to `serve/bench_results.json` under the model tag so one model's run does not replace the other's result.

Generation tokens per second is `eval_count / eval_duration`. Total throughput is generated tokens divided by wall time across the 30 measured serial requests; it includes prompt evaluation and request overhead. Cold load is Ollama's reported `load_duration`; cold first-request latency is separately measured end to end.

## Measured Ollama results

Measured on an Apple M1 Pro with 16 GiB unified memory, macOS arm64, and Ollama 0.24.0. The base run was measured 2026-09-05 23:21:44 IST and the tuned run 2026-09-06 13:06:09 IST.

| Model | Requests | Failures | p50 latency | p95 latency | Mean generation | Total throughput | Cold load | Cold first request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ghl-base` Q8_0 | 30 | 0 | 1,348 ms | 3,337 ms | 66.79 tok/s | 60.69 tok/s | 894 ms | 2,892 ms |
| `ghl-support` Q8_0 | 30 | 0 | 1,428 ms | 2,942 ms | 65.86 tok/s | 60.89 tok/s | 2,296 ms | 4,262 ms |

The base measured window generated 2,687 tokens in 44.272 seconds; the tuned window generated 2,927 tokens in 48.071 seconds. These are local single-user numbers, not a concurrency or capacity claim.
