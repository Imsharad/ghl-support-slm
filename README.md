# Customer-support SLM: fine-tuned Qwen2.5-1.5B-Instruct, self-hosted

This repository answers the customer-support fine-tuning assignment in
[`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md). It keeps training, evaluation, conversion, and local
serving reproducible from pinned inputs.

## 1. What this is, and the headline result

[PENDING G1]

## 2. Model and method choices, and why

The base is
[`Qwen/Qwen2.5-1.5B-Instruct` at revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306).
The reviewed model license is Apache-2.0, which permits use, modification, self-hosting, and
commercial distribution subject to its notice and attribution conditions. The exact review and
redistribution notes are in [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md).

The training source is
[`bitext/Bitext-customer-support-llm-chatbot-training-dataset` at revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443`](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/tree/430d1a89bd93bd1fa23c16f29dd53e73f0087443),
whose dataset card declares CDLA-Sharing-1.0. Raw and processed rows are not published in this
repository: CDLA sharing conditions continue to apply to Data and Enhanced Data, so the repository
publishes fetch/prepare code and integrity hashes while keeping those rows gitignored. Trained
weights and aggregate metrics are treated as computational Results; see the license review for the
scope and legal caveat.

The measured local fallback uses QLoRA with NF4 4-bit double quantisation and fp16 compute; LoRA
rank 16, alpha 32, dropout 0.05, and no bias on `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`,
`up_proj`, and `down_proj`; sequence length 512; micro-batch 1; gradient checkpointing; and AdamW
at learning rate `1e-4`. The Apple M1 Pro probe measured 18,464,768 trainable parameters,
2.567 seconds per forward/backward pass, and 4.09 GB peak MPS memory. Its random-token losses are
timing ballast, not convergence evidence. Full measurements and caveats are in
[`docs/LOCAL_QLORA_PROBE.md`](docs/LOCAL_QLORA_PROBE.md).

Why these choices: [PENDING G1]

## 3. Data handling and split strategy

The data pipeline is deterministic and keeps source, cleaning, grouping, and split evidence
separate:

1. [`data/fetch.py`](data/fetch.py) downloads the pinned Bitext revision into gitignored
   `data/raw/`.
2. [`data/prepare.py`](data/prepare.py) applies the ordered rules in
   [`configs/cleaning.json`](configs/cleaning.json), renders the native Qwen chat format, and drops
   examples over the 512-token training limit instead of silently truncating answers.
3. Exact normalized instructions, response-template families, and MiniLM embeddings at cosine
   threshold 0.86 are grouped with average linkage. The grouping configuration and calibration
   evidence are in [`configs/grouping.json`](configs/grouping.json) and
   [`data/calibration/REPORT.md`](data/calibration/REPORT.md).
4. Whole groups, never individual paraphrases, are assigned to train, validation, and test with
   seed 42. [`data/splits.json`](data/splits.json) freezes group membership and
   [`data/audit.json`](data/audit.json) records hashes, intersections, and residual similarity risk.

The configured ordered cleaning rules are:

- `reject_completed_action`: remove answers that claim an account, order, refund, or request was
  already changed.
- `reject_invented_timeline`: remove unsupported numeric timelines unless the user supplied the
  same numbers.
- `reject_request_credentials`: remove answers asking for passwords, PINs, CVV/CVC, or full card
  details.
- `replace_placeholders`: replace only placeholders with the configured neutral wording.
- `reject_unresolved_placeholder`: remove any row that still contains a placeholder marker.

After those rules, the `drop_overlength_512` gate removes a fully rendered exchange when it exceeds
512 tokens.

Final post-B1b row counts, rejection counts, split sizes, group counts, audit hashes, and residual
risk numbers: [PENDING B1b]

## 4. Evaluation design and results

[PENDING G1]

## 5. Exact prompt template, and how to load and run

Training and direct Transformers inference use the tokenizer's native Qwen2.5 ChatML template.
Ollama uses the equivalent template in [`serve/Modelfile.base`](serve/Modelfile.base). The system
turn appears exactly once. Running `uv run python train/render.py` produces this rendered sample
text before printing token IDs:

```text
<|im_start|>system
You are a customer support assistant. Answer clearly and helpfully. Do not invent company policy, account details, or completed actions. Ask for missing context when needed. Never ask for passwords or full payment card details.<|im_end|>
<|im_start|>user
I forgot my password and cannot sign in. What should I do?<|im_end|>
<|im_start|>assistant
Use the password-reset option on the sign-in page. If the reset message does not arrive, check your spam folder and contact support without sharing your password.<|im_end|>
```

Verify the local base artifact, import it, and start the Ollama HTTP route from the repository root:

```sh
uv run python tools/check_artifacts.py --manifest artifacts/manifest.json --target serve
ollama create ghl-base -f serve/Modelfile.base
ollama serve
```

If the Ollama desktop service is already running, omit `ollama serve`. Query the imported base Q8
through the OpenAI-compatible endpoint:

```sh
curl --fail-with-body http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ghl-base","messages":[{"role":"user","content":"I forgot my password and cannot sign in. What should I do?"}],"temperature":0,"max_tokens":256,"stream":false}'
```

The repository wrapper exposes the same route and a fixed safety check:

```sh
uv run python serve/inference.py --backend ollama --model ghl-base --self-test
```

- Adapter load route: [PENDING D3]
- Merged Transformers load route: [PENDING D3]
- Tuned Ollama tag `ghl-support`: [PENDING D3]

## 6. Serving and measured latency/throughput

The checked-in base benchmark is
[`serve/bench_results.json`](serve/bench_results.json), measured at 2026-09-05 23:21:44 IST on an
Apple M1 Pro with 16 GiB unified memory, macOS 26.5 arm64, and Ollama 0.24.0. It ran five warmups,
then 30 serial development requests with greedy decoding and a 256-new-token cap.

| Model | Requests | Failures | p50 end-to-end | p95 end-to-end | Mean generation | Total throughput | Cold load | Cold first request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ghl-base` Q8_0 | 30 | 0 | 1,348 ms | 3,337 ms | 66.79 tok/s | 60.69 tok/s | 894 ms | 2,892 ms |

The measured window generated 2,687 tokens in 44.272 seconds. These are single-user local numbers,
not a concurrency or capacity claim. In the separate 54-item base development run,
[`eval/results/base-dev-raw.jsonl`](eval/results/base-dev-raw.jsonl) records two answers that reached
the 256-token cap: `dv-033` and `dv-041`. The cap is therefore an observed truncation risk, not only
a configured limit.

Tuned `ghl-support` benchmark: [PENDING F1]

## 7. Real vs cut for time, and production trade-offs

[PENDING G1]

## 8. Reproduce

Run these steps from the repository root in dependency order.

1. Install the locked Python 3.11 serving environment and run the suite:

   ```sh
   uv sync --frozen --extra serve
   uv run pytest -q
   ```

2. Fetch the pinned dataset, build the processed splits, then verify their frozen hashes and
   intersections:

   ```sh
   uv run python data/fetch.py
   uv run python data/prepare.py
   uv run python data/prepare.py --audit-only --strict
   ```

3. Training commands for Colab Pro, a free T4, and the measured MPS fallback: [PENDING D1]

4. With the full pinned Hugging Face snapshot available locally, convert it using the pinned
   llama.cpp checkout. `HF_MODEL_DIR` must point to revision
   `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`:

   ```sh
   HF_MODEL_DIR=~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306
   tools/convert.sh "$HF_MODEL_DIR" artifacts/base-q8.gguf
   uv run python tools/check_artifacts.py --manifest artifacts/manifest.json --target serve
   ollama create ghl-base -f serve/Modelfile.base
   ```

5. Run the base evaluation harness. Each raw JSONL is appended by ID and can resume safely:

   ```sh
   uv run python eval/run.py --model base --backend ollama --split dev --check-complete
   ```

   Tuned and final challenge evaluation commands: [PENDING D3]

6. Reproduce the 30-request serial benchmark and validate all currently manifested artifacts:

   ```sh
   uv run python serve/bench.py --requests 30 --concurrency 1 --check --model ghl-base
   uv run python tools/check_artifacts.py --manifest artifacts/manifest.json
   ```

---

## Developer quickstart (task A1)

Python is pinned to 3.11 by `.python-version`; the system interpreter is 3.14 and is not used.
Everything runs through `uv run` against the locked environment.

```sh
make sync     # uv sync --frozen --extra serve
make test     # uv run pytest -q
make audit    # uv run python data/prepare.py --audit-only --strict
make eval-base
make bench
```

`bitsandbytes` lives in the `train` extra only. The pinned environment now loads and steps an NF4
QLoRA model on this Apple M1 Pro through MPS; the measured scope and caveats are in
[`docs/LOCAL_QLORA_PROBE.md`](docs/LOCAL_QLORA_PROBE.md). The default `uv sync` and `--extra serve`
also work here.
