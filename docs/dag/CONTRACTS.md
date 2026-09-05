# Contracts for parallel work on the GHL SLM assignment

Every worker (Opus, Sol, Grok) reads this before its task brief. It fixes the things that must agree across tasks built in parallel. Fable owns this file; ask in the thread if something here blocks you, do not edit it.

## 1. Facts about this machine and the accounts

- Mac: Apple M1 Pro, 16 GB unified memory, 230 GiB free. No CUDA. Correction 2026-09-05 22:35 IST (A1): `bitsandbytes 0.50.2` does install here and an NF4 forward runs on cpu and mps; whether local QLoRA is a usable fallback is node D0's question. Real training still runs on Colab Pro.
- System `python3` is 3.14; use the repo venv (`uv`, Python 3.11) via `uv run` for everything.
- Installed: `uv 0.8.8`, `ollama` (binary present, no server running at 22:20 IST Sep 5, zero models pulled), `git`.
  `llama-server` and `llama-quantize` are absent; task C3 clones llama.cpp under `.scratch/`.
- HF cache already has `sentence-transformers/all-MiniLM-L6-v2`. Hugging Face CLI is not logged in; `HF_TOKEN` comes from shark (node H0).
- No Kaggle credentials on disk. The dataset comes from the HF mirror (section 3).
- The assignment brief is `docs/ASSIGNMENT.md` (moved from `readme.md` by A1: this volume is case-insensitive, so `README.md` and `readme.md` were one file).
- Locked versions (uv.lock at A1): python 3.11.11, torch 2.14.0, transformers 5.16.1, peft 0.20.0, trl 1.12.0, bitsandbytes 0.50.2, datasets 5.0.1, pandas 3.0.5. Consequences: write pandas with copy-on-write semantics (no chained assignment); QLoRA/SFTTrainer recipes for transformers 4.x and trl 0.x do not apply verbatim, read the trl 1.x API; the Colab notebook must `pip install` these exact versions, not Colab's preinstalled ones.
- Deadlines (IST): Sun 2026-09-06 20:00 soft, Mon 2026-09-07 20:00 soft, Tue 2026-09-08 20:00 final.

## 2. Repository layout and ownership

Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1` (git, branch `main`; it was briefly `master` until 22:50 IST Sep 5). One working tree shared by all workers; parallel safety comes from disjoint paths. Each task brief lists the paths it owns. Commit only those paths (`git add <paths>`), message `<TASK-ID>: <what>`.

Commit identity: repo-local `user.name`/`user.email` are set to Sharad Jain / im.sharad.jain@gmail.com (this is shark's submission, so commits carry his identity). Workers commit with it; do not ask. Put your agent name in the commit body if you want attribution, e.g. `Authored-by: Sol`.

Data licensing: Bitext is CDLA-Sharing-1.0 (see `docs/LICENSE_REVIEW.md`). Raw and processed rows are gitignored (`data/raw/`, `data/processed/`); the repo publishes fetch/prepare code and sha256 hashes, and `data/prepare.py` must regenerate the same files deterministically. Trained weights and metrics are Results and may be published.

```
configs/        prompt.txt, eval.yaml, train.yaml, train-t4.yaml, cleaning.json, grouping.json, versions.json
data/           fetch.py, prepare.py, calibrate_threshold.py, intents.json, PROFILE.md, raw/ (gitignored), processed/, calibration/, splits.json, audit.json
eval/           run.py, score.py, blind.py, auto_metrics.py, dev.jsonl, challenge_draft.jsonl, challenge.jsonl (sealed), SEAL.json, RUBRIC.md, results/
train/          render.py, collate.py, train.py, plot_curves.py, runs/
serve/          Modelfile.base, Modelfile, inference.py, bench.py, demo.py, bench_results.json
tools/          preflight.py, convert.sh, parity_check.py, merge.py, check_run.py, fetch_artifacts.py, check_artifacts.py, check_submission.py
artifacts/      sources.json, manifest.json, selection.json, base-q8.gguf, tuned-q8.gguf, adapter/, merged/
notebooks/      train_colab.ipynb
tests/          test_prepare.py, test_prompt.py, test_eval.py, test_auto_metrics.py, fixtures/
docs/           plans/, dag/, LICENSE_REVIEW.md, CONVERSION.md, TRAINING.md, SELECTION.md, EXPORT.md, SERVING.md, RESULTS.md, FAILURES.md, LOOM_SHOTLIST.md
.scratch/       gitignored scratch (llama.cpp clone, temp venvs)
```

## 3. Data sources and schemas

Dataset: HF `bitext/Bitext-customer-support-llm-chatbot-training-dataset`, pinned by commit revision in `artifacts/sources.json` (task A2). Columns `flags, instruction, category, intent, response`. 26,872 rows confirmed by A2 (revision 430d1a89, sha256 6f81102b...). Note from A2: the CSV has 11 categories, not the 10 the card lists (extra `CONTACT`), and names `CANCEL`/`SHIPPING`/`SUBSCRIPTION` differ from the card; treat the CSV as truth and say so in the README. 385 distinct placeholders, 306 of them rare; flags `S` and `V` are undocumented.

Base model: `Qwen/Qwen2.5-1.5B-Instruct`, pinned by commit revision in `configs/versions.json` (task A3). Apache-2.0 expected, verified offline by A3.

Processed row (`data/processed/*.jsonl`), one JSON object per line:

```json
{"id": "bitext-000123", "group_id": "g-0042", "intent": "cancel_order", "category": "ORDER", "flags": "BQ",
 "instruction": "...", "response": "...", "cleaning": ["placeholder_order_number"], "n_tokens": 214}
```

Only `instruction` and `response` ever enter the model. `data/splits.json`: `{"seed": 42, "threshold": 0.87, "train": {"groups": [...], "rows": N, "sha256": "..."}, "val": {...}, "test": {...}}`.

`configs/grouping.json` (task B2; calibrated 0.86 on 2026-09-05 22:46 IST; `linkage` is how the cosine step clusters within intent, decided in B2's addendum because single-linkage chaining collapsed six intents):

```json
{"embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "normalize": "lower_strip_punct_keep_neg_num",
 "exact_match": true, "template_family": true, "cosine_threshold": 0.86, "linkage": "average", "labelled_pairs": 40, "report": "data/calibration/REPORT.md"}
```

Scenario item (`eval/dev.jsonl`, `eval/challenge*.jsonl`):

```json
{"id": "ch-013", "intent": "get_refund", "kind": "hard", "query": "...", "facts": "customer paid by card 9 days ago; refund policy unknown to assistant",
 "acceptable_actions": ["ask for order id", "explain how to request a refund", "say timeline depends on policy"],
 "critical_fail_if": ["promises refund is done", "states a refund timeline as fact"], "max_bitext_cosine": 0.71, "demo": false}
```

Raw answer (`eval/results/<model>-<split>-raw.jsonl`):

```json
{"id": "ch-013", "model": "base", "backend": "ollama", "tag": "ghl-base", "answer": "...", "prompt_tokens": 143, "gen_tokens": 188,
 "latency_ms": 2210, "tokens_per_s": 41.2, "truncated": false, "error": null, "ts": "2026-09-07 12:41 IST"}
```

Blind sheet CSV columns: `item_id, query, facts, answer_A, answer_B, pass_A, pass_B, critical_A, critical_B, preferred (A|B|tie), notes`. Model identity for A/B lives only in `eval/results/blind-key.json` (gitignored).

Scored row (`eval/results/scores.jsonl`): `{"id", "model", "pass": true, "critical": false, "preferred": "tuned", "notes"}`.
Summary (`eval/results/summary.jsonl`): one row `{"n", "base_pass_rate", "tuned_pass_rate", "diff_points", "ci95": [lo, hi], "base_critical", "tuned_critical", "win", "tie", "loss", "verdict": "positive|inconclusive|negative"}`.

## 4. The system prompt (exact text of `configs/prompt.txt`)

```
You are a customer support assistant. Answer clearly and helpfully. Do not invent company policy, account details, or completed actions. Ask for missing context when needed. Never ask for passwords or full payment card details.
```

Applied once, as the `system` turn of the native Qwen2.5 ChatML template, for training and for both serving routes.

## 5. Decoding and model tags (`configs/eval.yaml`)

- Greedy: temperature 0, top_p 1, repeat_penalty 1.0, max new tokens 256, context 2048, seed 42, same end token `<|im_end|>`.
- Ollama tags: `ghl-base` (Modelfile.base, from `artifacts/base-q8.gguf`), `ghl-support` (Modelfile, from `artifacts/tuned-q8.gguf`). Ollama at `http://localhost:11434`.
- Training: QLoRA NF4 double-quant, fp16 compute, LoRA r16 alpha32 dropout 0.05 on q,k,v,o,gate,up,down; lr 1e-4 cosine, 3% warmup; micro-batch 1, accumulation 16; max length 512; seed 42; assistant-only loss.
- Evaluation headline: blind human pass rate on the 54 sealed challenge queries, base-Q8 vs tuned-Q8 through Ollama. Positive only if gain >= 5 points, 95% bootstrap interval excludes zero, critical errors not higher. Else inconclusive or negative. Never retune on challenge results.

## 6. Commands that must exist and pass by Tuesday

```sh
uv sync --frozen --extra serve
uv run pytest -q
uv run python data/prepare.py --audit-only --strict
uv run python eval/run.py --model base --backend ollama --split dev --check-complete
uv run python eval/score.py --final --require-complete
uv run python serve/bench.py --requests 30 --concurrency 1 --check
uv run python tools/check_artifacts.py --manifest artifacts/manifest.json
uv run python tools/check_submission.py submission.json
curl --fail-with-body http://localhost:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"ghl-support","messages":[{"role":"user","content":"I forgot my password and cannot sign in. What should I do?"}],"temperature":0,"max_tokens":256,"stream":false}'
```

## 7. README section order

1. What this is (two lines) and the headline result with interval and verdict.
2. Model and method choices, and why.
3. Data handling and split strategy (grouping, threshold calibration, audit numbers, residual risk).
4. Evaluation design and results (challenge set, blind protocol, Bitext secondary, three failures).
5. Exact prompt template and how to load and run (adapter, merged, Ollama).
6. Serving and measured latency/throughput.
7. Real vs cut for time, and production trade-offs.
8. Reproduce: install, data, train (Colab Pro and free T4), evaluate, bench.

## 8. Reporting

Report in the GoHighLevel-prep thread with `@Fable 5.1` once, when done or blocked: paths landed, verification output, what you could not do. Fable reviews, commits if needed, updates `docs/dag/STATUS.json`, and dispatches the next node. Do not dispatch other workers yourself.
