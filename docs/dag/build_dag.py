#!/usr/bin/env python3
"""Build the task DAG for the GHL SLM assignment.

Writes DAG.json, tasks/<id>.md briefs and DAG.html from one source of truth
(the NODES list below). Re-run after editing; status lives in STATUS.json and
is never overwritten by this script.

Usage: python3 docs/dag/build_dag.py
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAG_DIR = ROOT / "docs" / "dag"
TASKS = DAG_DIR / "tasks"
CHANNEL = "04861c85-e907-4639-9075-7c474cbd8b51"
THREAD = "1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593"

# worker -> Buzz display name; share targets 50/25/25 of worker nodes
WORKERS = {"opus": "Opus", "sol": "Sol", "grok": "Grok"}

# (id, worker, title, phase, due IST, est hours, deps, owned paths, brief)
NODES = [
    # ---------------- Phase A: access and scaffold (Sat night) ----------------
    dict(
        id="A1", worker="opus", phase="A", title="Repo scaffold and dependency lock",
        due="Sat 2026-09-05 23:30", est=1.0, deps=[],
        paths=["pyproject.toml", "uv.lock", ".python-version", ".gitignore",
               "README.md", "configs/prompt.txt", "configs/eval.yaml", "tools/__init__.py",
               "data/.gitkeep", "eval/.gitkeep", "train/.gitkeep", "serve/.gitkeep",
               "artifacts/.gitkeep", "tests/.gitkeep", "Makefile"],
        brief="""
Create the Python project skeleton every later task builds on.

Do:
- `pyproject.toml` managed by `uv`, Python pinned to 3.11 in `.python-version` (system python is 3.14; do not use it).
  Base deps: `pandas`, `numpy`, `datasets`, `transformers`, `sentence-transformers`, `scikit-learn`, `rouge-score`,
  `pyyaml`, `requests`, `tqdm`, `pytest`, `matplotlib`. Optional extras: `train` (`peft`, `trl`, `bitsandbytes`, `accelerate`),
  `serve` (`fastapi`, `uvicorn`). Pin versions with `uv lock`; commit `uv.lock`.
  bitsandbytes will not install on this Mac; put it in the `train` extra only and confirm `uv sync` (no extras) works here.
- Directory layout exactly as in CONTRACTS.md section 2 (empty `.gitkeep` files are fine).
- `configs/prompt.txt` containing the exact system prompt from CONTRACTS.md section 4, no trailing whitespace, one trailing newline.
- `configs/eval.yaml` with the decoding settings from CONTRACTS.md section 5.
- `.gitignore`: `.venv/`, `data/raw/`, `artifacts/**/*.gguf`, `artifacts/merged/`, `artifacts/adapter/`, `**/__pycache__/`, `.pytest_cache/`, `*.log`, `.DS_Store`, `train/runs/**/checkpoint-*/`.
- `README.md` skeleton with the section headings in CONTRACTS.md section 7 and one line each saying "TODO (task Gx)". No results yet.
- `Makefile` targets: `sync`, `test`, `audit`, `eval-base`, `bench` that call the commands in CONTRACTS.md section 6 (they may fail until later tasks land; the targets just have to exist and be correct).

Verify: `uv sync` succeeds; `uv run python -c "import transformers, sentence_transformers, rouge_score"` prints nothing; `uv run pytest -q` reports "no tests ran" without error; `git status` shows only your paths.
""",
    ),
    dict(
        id="A2", worker="grok", phase="A", title="Dataset acquisition, pin and profile",
        due="Sat 2026-09-05 23:45", est=1.0, deps=[],
        paths=["data/fetch.py", "data/raw/", "data/PROFILE.md", "artifacts/sources.json"],
        brief="""
Get the Bitext customer-support dataset onto disk without Kaggle credentials, pin it, and profile it.

Do:
- There are no Kaggle credentials on this Mac. Use the Hugging Face mirror `bitext/Bitext-customer-support-llm-chatbot-training-dataset`
  (public, same 26,872 rows, same columns `flags, instruction, category, intent, response`). `data/fetch.py` downloads it with
  `huggingface_hub.snapshot_download` at a pinned commit revision, saves `data/raw/bitext.csv` plus the CSV sha256.
  Record `repo_id`, `revision`, `sha256`, `row_count`, `downloaded_at` (IST) and the dataset license text/URL in `artifacts/sources.json`.
  If the row count differs from 26,872, say so in PROFILE.md and sources.json, do not silently continue.
- `data/PROFILE.md`: row count; per-intent and per-category counts (27 intents, 10 categories expected); instruction and response
  length distributions in words and in Qwen2.5 tokens (p50/p90/p99/max; tokenizer `Qwen/Qwen2.5-1.5B-Instruct`, see CONTRACTS.md section 3);
  exact-duplicate instructions and responses; the `flags` column decoded (Bitext documents each letter; cite the source);
  every distinct `{{PLACEHOLDER}}` token in responses with counts; the 20 most common response templates (first 8 words) with counts;
  how many rows exceed 512 total tokens with the prompt template applied.
- The intent list with one example instruction each, saved as `data/intents.json` (list of `{intent, category, example}`).
  Add `data/intents.json` to your owned paths.

Verify: `uv run python data/fetch.py` is idempotent (second run says "already present, sha256 matches"); numbers in PROFILE.md
come from code you ran, quote the command next to each table.
""",
    ),
    dict(
        id="A3", worker="sol", phase="A", title="Model pin, license check, preflight tool",
        due="Sat 2026-09-05 23:45", est=1.0, deps=[],
        paths=["configs/versions.json", "tools/preflight.py", "docs/LICENSE_REVIEW.md"],
        brief="""
Pin the base model and prove we may self-host it commercially; write the preflight check.

Do:
- Resolve the current commit of `Qwen/Qwen2.5-1.5B-Instruct` on the Hub and download only `LICENSE`, `config.json`,
  `generation_config.json`, `tokenizer*` files at that revision into the default HF cache. Do not download the safetensors yet
  (other tasks will; keep tonight fast).
- `docs/LICENSE_REVIEW.md`: license name found in the pinned LICENSE file (expected Apache-2.0), what it requires of us
  (notice, attribution, change statement), and the same for the Bitext dataset (read `artifacts/sources.json` from task A2 if
  present, else look it up and mark it TO-CONFIRM). One paragraph on why a 1.5B instruct model is the pick (fits the M1 Pro 16 GB
  for Q8 serving, Apache-2.0, native chat template). No marketing claims.
- `configs/versions.json`: `{base_model: {repo_id, revision, license}, dataset: {...from A2 or TO-FILL}, python, torch, transformers,
  peft, trl, ollama, llama_cpp_converter: {repo, commit}}`. Fill what you can verify now; leave `TO-FILL` strings for the rest.
- `tools/preflight.py --training|--serve`: checks and prints a table: python version, uv present, disk free >= 30 GB, ollama binary and
  whether `ollama serve` is reachable, HF cache has the pinned tokenizer, `configs/prompt.txt` exists and hashes, `artifacts/sources.json`
  present, torch device (mps/cuda/cpu). `--training` additionally warns that QLoRA needs CUDA and this Mac has none. Exit nonzero on any
  hard failure. Save its report to `docs/preflight-<YYYY-MM-DD-HHMM>IST.md`.

Verify: run `uv run python tools/preflight.py --serve` and paste the table in your report. Note that Ollama is installed but no
server was running at 22:20 IST on Sep 5; do not start long-running services yourself.
""",
    ),
    # ---------------- Phase B: data and sealed cases (Sun morning) ----------------
    dict(
        id="B2", worker="grok", phase="B", title="Similarity threshold calibration (40 pairs)",
        due="Sun 2026-09-06 10:30", est=1.0, deps=["A2"],
        paths=["data/calibrate_threshold.py", "data/calibration/", "configs/grouping.json"],
        brief="""
Decide the paraphrase-grouping threshold before any split exists. 30-minute labeling time box.

Do:
- Embed all instructions with the cached `sentence-transformers/all-MiniLM-L6-v2` (normalize text first: lowercase, strip punctuation,
  keep negations and numbers). Within each intent, sample candidate pairs across cosine bands 0.70-0.75, 0.75-0.80, 0.80-0.85, 0.85-0.90,
  0.90-0.95, 0.95-1.0 (about 7 per band, 40 total), seed 42. Save them to `data/calibration/pairs.jsonl` with both texts and the score.
- Label each pair `same_scenario` true/false with a one-line reason (same request, same specifics, only wording differs => true).
  Also flag pairs where the intent label itself looks wrong.
- Pick the threshold that gives zero false "different" above it while keeping the band below it mostly "different"; report the
  precision/recall of each candidate threshold on your 40 labels in `data/calibration/REPORT.md`. Write the chosen value plus the
  exact-match and template-family rules to `configs/grouping.json` (schema in CONTRACTS.md section 3).
- Also report how many groups and the largest group the chosen threshold produces per intent, so B1 knows if any intent collapses into one group.

Verify: `configs/grouping.json` validates against the schema; REPORT.md has the 40 labels and the threshold table.
""",
    ),
    dict(
        id="B1", worker="grok", phase="B", title="data/prepare.py: clean, group, split, audit, freeze",
        due="Sun 2026-09-06 12:30", est=2.5, deps=["A1", "A2", "B2"],
        paths=["data/prepare.py", "data/processed/", "data/splits.json", "data/audit.json",
               "configs/cleaning.json", "tests/test_prepare.py"],
        brief="""
Build the leakage-free split. This is the most scrutinised part of the assignment.

Do:
- Read `data/raw/bitext.csv` (A2), `configs/grouping.json` (B2), `configs/prompt.txt`.
- Cleaning rules in `configs/cleaning.json`, applied by code and logged per row in `data/audit.json`:
  reject responses that promise completed actions ("I have refunded", "your account is now unlocked"), invent policy or timelines
  ("within 24 hours" unless the instruction supplies it), or request credentials; replace `{{PLACEHOLDER}}` tokens with natural
  neutral wording only where the meaning survives (e.g. `{{Order Number}}` -> "your order number"), otherwise reject the row.
  Every rule has an id, a regex or function, and a count in the audit. Keep the row id, intent, category, flags as metadata that
  never enters the model input.
- Grouping: exact normalized match and response-template family are unioned as before, but the cosine step uses the `linkage` named in
  `configs/grouping.json` (B2's addendum: single-linkage union-find at 0.86 chained six intents into one giant component each, about 90%
  of the intent's rows; average-linkage agglomerative clustering at cosine distance 1 - threshold within intent is the expected value).
  Report per intent: group count, largest group share. If a largest group still exceeds 50% of an intent, say so in the audit and the
  README; never break it. Split 80/10/10 by whole groups, stratified by intent, seed 42. If an intent cannot give every split at
  least one group, report it in the audit and keep the grouping (never break a group).
- Output `data/processed/{train,val,test}.jsonl` with the row schema in CONTRACTS.md section 3 (gitignored: Bitext is CDLA-Sharing-1.0,
  so we publish code plus hashes, never rows; prepare.py must be deterministic from `data/raw/bitext.csv`); `data/splits.json` with group ids
  per split and sha256 of each jsonl; `data/audit.json` with counts per rule, per split, per intent, cross-split intersection checks
  (group ids and normalized instructions both empty), nearest cross-split neighbour cosine distribution, and residual-risk note.
- Drop rows over 512 total tokens with the chat template applied (count them). Provide `--cap-train N` (used by the free-T4 config,
  default no cap) that keeps the most intent-balanced N rows.
- `--audit-only --strict` recomputes hashes and intersections and exits nonzero on any mismatch.
- `tests/test_prepare.py`: group never straddles splits; placeholder tokens absent from outputs; rejected rows carry a rule id.

Verify: `uv run python data/prepare.py` then `uv run python data/prepare.py --audit-only --strict` passes; `uv run pytest -q tests/test_prepare.py`
passes; report split sizes, group counts, and any collapsed intents.
""",
    ),
    dict(
        id="B3", worker="grok", phase="B", title="Draft 54 challenge queries, 54 dev scenarios, rubric",
        due="Sun 2026-09-06 11:15", est=1.5, deps=["A2"],
        paths=["eval/challenge_draft.jsonl", "eval/dev.jsonl", "eval/RUBRIC.md"],
        brief="""
Author the held-out proof set that shark will edit and approve at 11:30 IST Sunday. Nothing tuned may exist before it is sealed.

Do:
- `eval/challenge_draft.jsonl`: 54 items, two per intent from `data/intents.json`: one ordinary request and one hard variant
  (typos, anger, two requests in one, missing context, asks for an unsupported policy, off-topic drift). Item schema in CONTRACTS.md
  section 3: `id, intent, kind (ordinary|hard), query, facts (what the assistant may assume), acceptable_actions, critical_fail_if`.
  Queries must be freshly written, not paraphrases of Bitext rows: check the max cosine to any Bitext instruction with MiniLM and
  keep it under 0.85; store that score in the item as `max_bitext_cosine`.
- `eval/dev.jsonl`: 54 different scenarios in the same schema for debugging and checkpoint choice. Include the two Loom demo queries
  and the policy probe from the Astra plan section 7 as dev items flagged `demo: true`. No dev scenario may share a situation with a challenge item.
- `eval/RUBRIC.md`: pass = addresses every request, sound next steps, admits missing facts, helpful tone; critical failure = invented
  policy/status/completed action or credential request; "contact support" alone is not a pass; correctness over style. Include a
  10-line scoring guide a human can apply in under a minute per answer, and the blind sheet column layout (from CONTRACTS.md section 3).

Verify: 27 intents x 2 kinds present; ids unique; every item has non-empty facts and critical_fail_if; the cosine check output is
pasted into your report.
""",
    ),
    dict(
        id="B4", worker="grok", phase="B", title="Bitext test automated metrics module",
        due="Sun 2026-09-06 15:00", est=1.0, deps=["A1"],
        paths=["eval/auto_metrics.py", "tests/test_auto_metrics.py"],
        brief="""
Secondary metrics for the Bitext held-out test split (the human blind pass rate on the challenge set stays the headline).

Do:
- `eval/auto_metrics.py --raw eval/results/<name>-raw.jsonl --refs data/processed/test.jsonl --out eval/results/<name>-auto.json`:
  ROUGE-L F1 against the reference response, MiniLM embedding cosine to the reference, placeholder-token rate (`{{`), mean/median
  answer length in tokens, empty or truncated (hit 256 cap) rate, per-intent breakdown, paired bootstrap 95% interval for the
  base-vs-tuned difference when two raw files are given (`--compare`), 2,000 resamples by group id, seed 42.
- Deterministic; no network beyond the cached MiniLM; runs in under 2 minutes on 300 rows on this Mac.
- `tests/test_auto_metrics.py` with tiny fixtures: identical answer scores 1.0 ROUGE-L, placeholder detection, bootstrap interval
  contains the point estimate, missing ids raise.

Verify: `uv run pytest -q tests/test_auto_metrics.py` passes.
""",
    ),
    # ---------------- Phase C: harness and base first (Sun afternoon) ----------------
    dict(
        id="C2", worker="sol", phase="C", title="Prompt template rendering and loss-mask collator with fixtures",
        due="Sun 2026-09-06 14:00", est=1.5, deps=["A1", "A3"],
        paths=["train/collate.py", "train/render.py", "tests/test_prompt.py", "tests/fixtures/"],
        brief="""
Prove the training answer boundary before any GPU minute is spent.

Do:
- `train/render.py`: render one example with the Qwen2.5 native chat template (`tokenizer.apply_chat_template`) using the system
  prompt from `configs/prompt.txt` applied exactly once, user = instruction, assistant = response. Expose `render_prompt(instruction)`
  (generation prompt, ends at the assistant header) and `render_full(instruction, response)` (with end marker `<|im_end|>`).
  Print the rendered text and token ids for a sample row as a CLI.
- `train/collate.py`: tokenizes `render_full`, sets labels to -100 for every token up to and including the assistant header, keeps
  labels for assistant text plus the end marker, truncates at 512 total tokens (drop, never truncate the answer silently: return None
  and count). Padding side and pad token documented.
- `tests/fixtures/`: three examples with their expected token ids and label masks committed as JSON; regenerate script included.
- `tests/test_prompt.py`: fixtures match; system prompt appears once; user tokens have -100 labels; assistant labels nonempty and end
  with the end-marker id; `render_prompt` is a strict prefix of `render_full` token ids; a >512 example returns None.

Verify: `uv run pytest -q tests/test_prompt.py` passes; paste the rendered sample (text) in your report so C3 can check parity against Ollama.
""",
    ),
    dict(
        id="C1", worker="sol", phase="C", title="Eval harness: eval/run.py and eval/score.py with bootstrap",
        due="Sun 2026-09-06 16:30", est=2.5, deps=["A1", "B3", "C2"],
        paths=["eval/run.py", "eval/score.py", "eval/blind.py", "tests/test_eval.py"],
        brief="""
The measurement must work on the base model before training finishes.

Do:
- `eval/run.py --model {base,tuned} --backend {ollama,transformers} --split {dev,challenge,test} [--limit N] [--check-complete]`:
  reads the split file, renders with `train/render.py` for the transformers backend, or sends `system` + `user` messages to
  `POST http://localhost:11434/api/chat` with `options: {temperature: 0, num_predict: 256, repeat_penalty: 1.0, seed: 42}` for Ollama
  (model tags from CONTRACTS.md section 5). Writes `eval/results/<model>-<split>-raw.jsonl` (schema in CONTRACTS.md section 3),
  resumable by id, records timeouts and empty answers as failures. `--check-complete` exits nonzero unless every split id has a row.
- `eval/blind.py --split challenge`: pairs base and tuned raw answers, randomizes A/B order per item with seed from the sealed hash,
  writes `eval/results/blind-sheet.csv` (columns in CONTRACTS.md section 3) plus a hidden `eval/results/blind-key.json` (gitignored),
  and an HTML sheet `eval/results/blind-sheet.html` a human can score in the browser and export as CSV.
- `eval/score.py --final --require-complete`: reads the scored CSV and the key, computes pass rate per model, point difference,
  paired bootstrap 95% interval (2,000 resamples over items, seed 42), critical-error counts, win/tie/loss, per-intent and per-kind
  tables; classifies `positive` (gain >= 5 points, interval excludes zero, critical errors not higher), `negative` (tuned lower or more
  critical errors) else `inconclusive`. Writes `eval/results/{scores,summary,failures}.jsonl`. Failures = items the tuned model failed
  or scored below base.
- `tests/test_eval.py`: good/bad fixture pairs score as expected, swapped labels are detected, missing outputs fail `--check-complete`,
  bootstrap interval contains the point estimate.

Verify: `uv run pytest -q tests/test_eval.py`; a dry run `eval/run.py --model base --backend ollama --split dev --limit 3` once C3 has
the base tag in Ollama (if C3 is not done, use `--backend transformers --limit 1` on CPU and say so).
""",
    ),
    dict(
        id="C3", worker="sol", phase="C", title="Base Q8 GGUF, Ollama import, prompt parity check",
        due="Sun 2026-09-06 15:30", est=2.0, deps=["A3", "C2"],
        paths=["tools/convert.sh", "tools/parity_check.py", "serve/Modelfile.base", "artifacts/base-q8.gguf", "docs/CONVERSION.md"],
        brief="""
The served base model must be the same prompt and weights as the trained-on base, or the comparison is meaningless.

Do:
- Download the full pinned `Qwen/Qwen2.5-1.5B-Instruct` revision from `configs/versions.json` (about 3 GB).
- Pin a llama.cpp commit in `configs/versions.json` (`llama_cpp_converter`), clone it under `.scratch/llama.cpp` (gitignored),
  install its converter requirements in a separate uv venv, run `convert_hf_to_gguf.py --outtype q8_0` to produce `artifacts/base-q8.gguf`.
  `tools/convert.sh <hf_dir> <out.gguf>` wraps this so E1 reuses the exact same converter for the tuned model.
- `serve/Modelfile.base`: `FROM ./artifacts/base-q8.gguf`, `SYSTEM` = contents of `configs/prompt.txt`, `PARAMETER temperature 0`,
  `num_predict 256`, `repeat_penalty 1.0`, `num_ctx 2048`, and a TEMPLATE that reproduces the Qwen2.5 ChatML format exactly.
  `ollama create ghl-base -f serve/Modelfile.base`. Start `ollama serve` in the background only for your checks and leave it running
  (say so in the report).
- `tools/parity_check.py`: for 5 dev items, compare the prompt text Ollama renders (`/api/chat` with `"raw": false` is opaque, so use
  `/api/generate` with `raw: true` on the string from `train/render.py:render_prompt` and compare its answer to `/api/chat` output on the
  same item; both must match token-for-token at temperature 0). Also assert the GGUF tokenizer produces the same ids as the HF tokenizer
  for the rendered prompt (llama.cpp `tokenize` binary or `gguf` python package). Write the result to `docs/CONVERSION.md` with the
  converter commit, file sha256, size, and the parity table.

Verify: `curl` from CONTRACTS.md section 6 against `ghl-base` returns a nonempty answer; parity table all `match`; artifacts/base-q8.gguf
sha256 recorded.
""",
    ),
    dict(
        id="C4", worker="grok", phase="C", title="Base dev answers and 20-answer inspection",
        due="Sun 2026-09-06 18:00", est=1.5, deps=["C1", "C3"],
        paths=["eval/results/base-dev-raw.jsonl", "eval/results/BASE_DEV_INSPECTION.md"],
        brief="""
Look at what the base model actually says before we claim to beat it.

Do:
- `uv run python eval/run.py --model base --backend ollama --split dev --check-complete` (54 items, serial).
- Read 20 answers (every intent category represented) and write `eval/results/BASE_DEV_INSPECTION.md`: for each, the query, the
  answer, pass/critical/notes using `eval/RUBRIC.md`, and a tally. Call out harness defects (truncation, template leakage such as
  `<|im_start|>` in output, empty answers, system prompt ignored) as separate bullets with the item ids, because C1/C3 must fix
  those before training output is scored.
- Record wall time and tokens/sec observed for the run (from the raw file fields) as a first serving-speed data point.

Verify: 54 rows in the raw file; inspection file has 20 entries and the defect list (possibly empty, say "none found").
""",
    ),
    dict(
        id="C5", worker="sol", phase="C", title="Base answers on the frozen test split plus automated metrics",
        due="Sun 2026-09-06 04:00", est=1.5, deps=["B1", "B1b", "C1", "C3"],
        paths=["eval/results/base-test-raw.jsonl", "eval/results/base-test-auto.json"],
        brief="""
Pre-generate the base half of D3's automated comparison so the tuned run on Sunday is not waiting an hour on the base.

Do:
- `uv run python eval/run.py --model base --backend ollama --split test --check-complete` (2,270 rows, serial, temperature 0).
  Resume by id if interrupted; do not regenerate rows that already exist.
- `uv run python eval/auto_metrics.py --raw eval/results/base-test-raw.jsonl --refs data/processed/test.jsonl --out eval/results/base-test-auto.json`.
- Commit both files. Report row count, failures, wall time, tokens/sec, and the headline numbers from the auto file
  (ROUGE-L, cosine, placeholder rate, truncated rate, mean gen_tokens).

Verify: `--check-complete` PASS on 2,270 rows; auto json has the per-intent breakdown.
""",
    ),
    dict(
        id="B1b", worker="grok", phase="B", title="Frame-aware and voice-aware placeholder wording",
        due="Sun 2026-09-06 02:00", est=1.0, deps=["B1", "C4"],
        paths=["data/prepare.py", "data/processed/", "data/splits.json", "data/audit.json", "configs/cleaning.json", "tests/test_prepare.py"],
        brief="""
C4 found that the blanket neutral wording for id-style placeholders is ungrammatical in the common frames and uses the
assistant's voice inside the user turn: 782 train instructions read "purchase your order number", 767 "order your order
number", 1,475 rows "number your order number", 760 "the your ...". Fix the wording, not the grouping.

Do:
- In `replace_placeholders`, make the wording depend on the field and the preceding words. Possessive P is "my" in the
  instruction and "your" in the response. For every id-style placeholder in `placeholder_replace` whose wording is
  "your <noun phrase>" (order number, invoice number, tracking number, account number, account id, account type, account
  category, refund amount): `(order|purchase|invoice|tracking|account)\s+number\s+{{X}}` -> "P <noun> number";
  `\b(order|purchase|invoice|account)\s+{{X}}` -> "P <that word>"; `\bthe\s+{{X}}` -> "P <noun phrase>";
  standalone -> "P <noun phrase>". Keep Bitext typo rows as they are (a typo before the slot falls to the standalone form).
- Add a `frame` count per rule to `data/audit.json` so the README can say how many rows took each form.
- Regenerate. Splits must not move: group ids, split membership and `data/splits.json` group lists are expected to be
  byte-identical to 24ab0d9 because `normalize` runs on the raw text; if anything moves, stop and report before committing.
- `tests/test_prepare.py`: add cases for the four frames in both voices, and assert no processed instruction contains
  "your order number" preceded by order/purchase/number, and no "the my"/"the your".

Verify: `uv run python data/prepare.py` then `--audit-only --strict`; `uv run pytest -q`; report the count of rows whose text
changed per split and confirm splits.json group lists are unchanged (diff against HEAD).
""",
    ),
    dict(
        id="G0", worker="sol", phase="C", title="README sections that are already final",
        due="Sun 2026-09-06 03:30", est=1.0, deps=["C2", "C3", "F1"],
        paths=["README.md"],
        brief="""
Draft the README sections whose inputs are already frozen so G1 only has to add results. Order and headings from
CONTRACTS.md section 7; keep the existing section numbers and the A1 developer quickstart.

Do:
- Section 5: the exact rendered prompt from `uv run python train/render.py` (text, not ids), and load-and-run commands for the
  Ollama route against `ghl-base` today (the `ghl-support` tag and the adapter/merged routes get one line each marked
  `[PENDING D3]` so G1 can fill them).
- Section 6: the ghl-base block from `serve/bench_results.json` as a table with the file cited, hardware and Ollama version,
  the cold-load numbers, and the 256-token cap note with the two truncated dev ids from `eval/results/base-dev-raw.jsonl`.
- Section 8: reproduce steps in dependency order using the real commands from the briefs that have landed (uv sync, data/fetch.py,
  data/prepare.py, --audit-only --strict, tools/convert.sh, ollama create with serve/Modelfile.base, eval/run.py, serve/bench.py,
  tools/check_artifacts.py). Every command must be one you ran or one that exists on main.
- Section 2, method half only: base model, pinned revision, licence line from `docs/LICENSE_REVIEW.md` (A3), Bitext licence and
  why rows are not published, QLoRA settings from `docs/LOCAL_QLORA_PROBE.md` as the measured local fallback. Leave the
  "why these choices" prose to G1.
- Section 3: the structure and the cleaning-rule list from `configs/cleaning.json`, with numbers left as `[PENDING B1b]`.
- Use exactly the marker form `[PENDING <node>]` for anything not yet final; G1 removes them. No other TODO text.

Verify: every local path linked in the README exists; no `{{`; `uv run pytest -q` passes; commit as `G0: README sections 2, 3, 5, 6, 8`.
""",
    ),
    dict(
        id="C1b", worker="grok", phase="C", title="eval/run.py --adapter: score a PEFT adapter without merging",
        due="Sun 2026-09-06 02:30", est=1.0, deps=["C1", "D1"],
        paths=["eval/run.py", "tests/test_eval.py"],
        brief="""
D3 scores several checkpoints on dev. Today `--model tuned --backend transformers` only reads `artifacts/merged/`, so the
Colab notebook merges each adapter into that directory and deletes it between checkpoints. Remove the dance.

Do:
- Add `--adapter <dir>` to `eval/run.py`. With it, the transformers backend loads the pinned fp16 base from
  `configs/versions.json` (same revision as `tools/merge.py`) and wraps it with `PeftModel.from_pretrained(base, adapter_dir)`;
  the tokenizer and prompt come from the adapter dir when present, else from the base. `--model tuned` without `--adapter`
  keeps the current merged-directory behaviour; `--adapter` with `--backend ollama` is an error.
- Record `adapter_dir` and its sha256 of `adapter_model.safetensors` in the raw file header/rows so D3 can prove which
  checkpoint produced which answers.
- Test with a disposable zero-effect rank-1 adapter as Sol did for E1 (build it in the test, delete after): answers with
  `--adapter` on 2 dev items equal the base answers greedy on cpu. Add the argument-validation case.
- Do not touch `serve/inference.py` (F1, Sol). Sol's C5 process is running `eval/run.py` right now; editing the file on disk
  does not affect the loaded process, but do not delete or rename anything under `eval/results/`.

Verify: `uv run pytest -q tests/test_eval.py` and the full suite; paste the raw-file header line showing adapter_dir and sha.
""",
    ),
    # ---------------- Phase D: train and choose ----------------
    dict(
        id="D0", worker="opus", phase="D", title="Local QLoRA timing probe on the M1 Pro (30-minute box)",
        due="Sat 2026-09-05 23:59", est=0.5, deps=["A1"],
        paths=["docs/LOCAL_QLORA_PROBE.md", ".scratch/"],
        brief="""
A1 found that bitsandbytes 0.50.2 installs and runs NF4 on this Mac, which contradicts the plan's "no local QLoRA" premise.
Settle in 30 minutes whether local QLoRA is a real fallback for the cloud-GPU gate or too slow to matter.

Do:
- Download `Qwen/Qwen2.5-1.5B-Instruct` safetensors (latest revision is fine for a timing probe; note the revision) into the HF cache.
  Sol's C3 will reuse the cache, so this is not wasted.
- In `.scratch/qlora_probe.py`: load NF4 double-quant, fp16 compute, LoRA r16 alpha32 on q,k,v,o,gate,up,down via peft, on the best
  available device (try mps, fall back to cpu), 8 synthetic 512-token sequences, micro-batch 1, gradient checkpointing on. Time 5
  optimizer steps after 1 warmup step. Record peak memory (`torch.mps.driver_allocated_memory` or `resource`), seconds per step, and
  whether loss is finite. If MPS refuses a kernel, record the exact error and try cpu once.
- `docs/LOCAL_QLORA_PROBE.md`: device, versions, seconds per step, projected wall time for 2,000 rows x 1 epoch at accumulation 16
  (= 2,000 forward/backward passes), memory, and a one-line verdict: "viable fallback under N hours" or "not viable, keep mlx-lm".
  Stop at 30 minutes wall and write whatever you have.

Verify: the probe file exists with a projected wall time or an exact failure message; nothing outside `.scratch/` and the doc touched.
""",
    ),
    dict(
        id="D1", worker="opus", phase="D", title="train/train.py, configs, Colab notebook, check_run",
        due="Sun 2026-09-06 15:30", est=2.5, deps=["A1", "C2", "B1"],
        paths=["train/train.py", "configs/train.yaml", "configs/train-t4.yaml", "notebooks/train_colab.ipynb",
               "tools/check_run.py", "train/plot_curves.py", "docs/TRAINING.md"],
        brief="""
QLoRA training that shark can run on Colab Pro with one click, resumable, with the exact loss mask from C2.

Do:
- `train/train.py --config configs/train.yaml [--smoke] [--resume]`: Qwen2.5-1.5B-Instruct at the pinned revision, 4-bit NF4 with
  double quant, fp16 compute, LoRA r16 alpha32 dropout 0.05 on q,k,v,o,gate,up,down; lr 1e-4 cosine, 3% warmup, seed 42, micro-batch 1,
  grad accumulation 16, max length 512, gradient checkpointing, assistant-only labels via `train/collate.py`. Log train and val loss
  every 25 steps to `train/runs/<run>/loss.csv`; save resumable state every 100 steps; push adapter checkpoints to the Hub repo named in
  the config (token from env `HF_TOKEN`; skip push with a warning if unset). Save `config.json` (resolved config + git sha + versions)
  and `peak_memory_gb`. `--smoke` = 20 steps on 64 rows, then a resume from step 10 to prove resume works.
- `configs/train.yaml` = full grouped train set, 1 epoch, mid-epoch checkpoint at 50% (for A100/L4). `configs/train-t4.yaml` = `--cap-train 8000`,
  same hyperparameters (the free-compute config the README promises).
- `notebooks/train_colab.ipynb`: cells for `nvidia-smi`, clone the repo at a tag or branch, `pip install` pinned, `HF_TOKEN` from Colab
  secrets, mount nothing, run smoke, run full, then a post-training cell that runs `eval/run.py --backend transformers --split dev` for
  each saved checkpoint and writes `train/runs/<run>/dev-<ckpt>-raw.jsonl`, then zips `train/runs/<run>` for download.
- `tools/check_run.py train/runs/<run>`: finite losses, val loss recorded, peak memory below 12 GB, adapter reloads and generates one
  answer, exits nonzero otherwise. `train/plot_curves.py` writes `curves.png`.
- `docs/TRAINING.md`: how to run on Colab Pro and on a free T4, expected wall time (planning estimate, labeled), what to paste back.

Verify: `uv run python -c "import train.train"` on this Mac (no CUDA) fails only at device selection with a clear message; the notebook
JSON is valid; `--smoke` cannot run here, say so. shark runs the smoke on Colab (node H0/D2).
""",
    ),
    dict(
        id="D3", worker="opus", phase="D", title="Checkpoint selection and Bitext test generation",
        due="Mon 2026-09-07 10:30", est=3.0, deps=["D2L", "B4", "C1b", "C5"],
        paths=["artifacts/selection.json", "train/runs/local-t4/", "eval/sample_test.py", "eval/run_sample.py",
               "eval/results/test-sample.json", "eval/results/test-sample-refs.jsonl", "eval/results/base-test-sample-raw.jsonl",
               "eval/results/tuned-test-raw.jsonl", "eval/results/dev-*-raw.jsonl", "eval/results/dev-*-judgments.jsonl",
               "eval/results/base-test-sample-auto.json", "eval/results/tuned-test-auto.json", "docs/SELECTION.md"],
        brief="""
Pick the checkpoint on dev only, then generate tuned Bitext test answers once. Rewritten 04:58 IST 2026-09-06 after D2L
replaced the Colab run and C5 produced the full base test file.

Facts that shape the job:
- The run is local: `train/runs/local-t4/` (D2L, finished 03:43 IST, checkpoints 100/200/250/300/400/500). check_run and
  plot_curves are done (0c3ee1b, 58353a7). `tools/check_run.py` reloads a checkpoint, so it needs one-model clearance like any eval.
- `eval/dev.jsonl` is a rubric set (query, facts, acceptable_actions, critical_fail_if) with no reference responses, so
  `eval/auto_metrics.py` cannot score it. Dev pass rate comes from rubric judgment against `eval/RUBRIC.md`, as in
  `BASE_DEV_INSPECTION.md`.
- Base test answers are Sol's C5 file `eval/results/base-test-raw.jsonl` (2,270 rows, Ollama Q8). Never regenerate or modify it.
- One model load at a time on this Mac. `uv run pytest -q` loads the base model too (test_eval zero-effect adapter).

Do:
- Dev generations for checkpoints 250, 300, 400, 500 only (100 and 200 are strictly undertrained on the val curve). All 54 dev
  rows each, via `eval/run_sample.py` or `eval/run.py --backend transformers --model tuned --adapter <dir>`, into
  `eval/results/dev-<step>-raw.jsonl`. Judge all 54 per checkpoint by rubric and record one line per item in
  `eval/results/dev-<step>-judgments.jsonl` (`id, pass, critical, note`) so the verdicts can be spot-checked.
  Select by dev pass rate, then critical errors, then earlier checkpoint. Write `artifacts/selection.json`
  (`checkpoint, step, dev_pass_rate, critical_errors, reason, selected_at IST`) and `docs/SELECTION.md`.
- Test sample: `eval/sample_test.py` seed 42, one row per distinct group, up to 10 per intent, deficit backfilled round-robin
  (270 rows, 270 groups, 27 intents). `eval/results/test-sample.json` records rule, seed, counts; `--check` reproduces the ids.
  Subsets: `base-test-sample-raw.jsonl` copied from C5, `test-sample-refs.jsonl` copied from `data/processed/test.jsonl`
  (`auto_metrics.align` is strict on identical id sets).
- Generate tuned answers for the 270 sampled ids with the selected adapter (fp16, transformers, mps) into
  `eval/results/tuned-test-raw.jsonl`. Measure 10 rows first; if the 270 project past 90 minutes, report the rate and stop.
- `eval/auto_metrics.py --raw base-test-sample-raw.jsonl --refs test-sample-refs.jsonl --compare tuned-test-raw.jsonl`,
  base output named `base-test-sample-auto.json`. Note in SELECTION.md that base is Ollama Q8 and tuned is fp16 transformers.
- Run `uv run pytest -q` once, after generation, before reporting.

Verify: selection.json cites dev numbers only; four dev raw and judgment files with 54 rows each; sample raw files and refs
subset have 270 rows with identical ids; the auto-metrics comparison has an interval.
""",
    ),
    dict(
        id="D2L", worker="opus", phase="D", title="Local insurance training run on mps (train-t4 config, detached)",
        due="Sun 2026-09-06 08:00", est=6.0, deps=["D1", "B1b"],
        paths=["train/runs/local-t4/", "docs/LOCAL_RUN.md"],
        brief="""
Block 0 (Colab GPU) is still unanswered at 00:40 IST Sunday. D0 measured 2.57 s per 512-token pass on this Mac, so the
free-T4 config (cap_train 8000, one epoch) is about 5.7 h here. Run it overnight as insurance so D3 has a real adapter by
morning whatever happens with Colab. If Colab lands, the Colab run is the main run and this is the documented fallback.

Do:
- Launch detached (Popen with start_new_session, log to `train/runs/local-t4/train.log`), `--device mps`, `--data-dir data/processed`,
  `configs/train-t4.yaml` unchanged except output dir `train/runs/local-t4/`. Confirm with pgrep from a later call, then post
  the PID, the first logged step time, and the projected finish in IST. Do not wait in-turn.
- Keep the checkpoint cadence from the config so a crash loses at most 100 optimizer steps; resume with the D1 path if it dies.
- When it finishes, run `tools/check_run.py train/runs/local-t4 --max-memory-gb 12 --device mps`, plot curves, and write
  `docs/LOCAL_RUN.md`: config, wall time, peak memory, final train/val loss, checkpoint list. Commit the doc and curves.png only;
  the run directory stays untracked.
- Ollama will be serving Sol's C5 run at the same time; that is expected, do not stop it.

Verify: check_run PASS; LOCAL_RUN.md committed; the adapter path reported so D3 can pick it up.
""",
    ),
    # ---------------- Phase E: export and final proof ----------------
    dict(
        id="E1", worker="sol", phase="E", title="Merge, tuned Q8 GGUF, manifest, fetch/check tools, Hub push",
        due="Mon 2026-09-07 12:30", est=2.0, deps=["D3", "C3"],
        paths=["tools/merge.py", "artifacts/manifest.json", "artifacts/tuned-q8.gguf", "artifacts/merged/", "artifacts/adapter/",
               "serve/Modelfile", "tools/fetch_artifacts.py", "tools/check_artifacts.py", "docs/EXPORT.md"],
        brief="""
Produce the artifacts graders will download, and prove they are the model we evaluated.

Do:
- `tools/merge.py`: load the original fp16 base at the pinned revision, apply the selected adapter, merge, save `artifacts/merged/` with
  tokenizer and the prompt template file. Adapter-vs-merged parity on 10 dev items (greedy, identical answers expected; report any diff).
- Convert `artifacts/merged/` with `tools/convert.sh` (same converter commit as C3) to `artifacts/tuned-q8.gguf`. `serve/Modelfile`
  identical to `Modelfile.base` except the FROM line; `ollama create ghl-support -f serve/Modelfile`. Q8 drift check: 10 dev answers
  fp16 (from D3's dev raw) vs Q8 through Ollama; report exact-match count and any rubric-relevant difference.
- `artifacts/manifest.json`: every artifact with path, sha256, bytes, Hub URL, plus base revision, converter commit, tokenizer sha,
  prompt sha, ollama version, created_at IST.
- `tools/fetch_artifacts.py --manifest --target serve` downloads the GGUFs from the Hub URLs and verifies sha256; `tools/check_artifacts.py`
  verifies local files against the manifest. Both exit nonzero on mismatch.
- Push adapter, merged weights and both GGUFs to shark's Hub account (`HF_TOKEN` in env; if absent, stop and report the exact commands
  for shark to run). Fill Hub URLs into the manifest and write `docs/EXPORT.md`.

Verify: `uv run python tools/check_artifacts.py --manifest artifacts/manifest.json`; the CONTRACTS.md section 6 curl against
`ghl-support` returns a nonempty answer.
""",
    ),
    dict(
        id="E1b", worker="sol", phase="E", title="Tuned answers on the 270 test sample through Ollama Q8 (served-model metrics)",
        due="Sun 2026-09-06 13:30", est=0.75, deps=["E1"],
        paths=["eval/results/tuned-q8-test-raw.jsonl", "eval/results/tuned-q8-test-auto.json", "docs/EXPORT.md"],
        brief="""
D3 compared base Q8 (Ollama) against the tuned adapter in bf16 transformers, so the reported gap is adapter plus precision plus
serving stack. E1 showed the served `ghl-support` Q8 model matches the bf16 adapter answers on only 2 of 10 dev items. Score the
model graders will actually run, through the same path as the base, so the README can report one apples-to-apples number.

Do:
- `uv run python eval/run_sample.py --model tuned --backend ollama --check-complete --output eval/results/tuned-q8-test-raw.jsonl`
  (270 sampled test ids, `ghl-support`, serial, temperature 0). Nothing else loaded; do not load transformers. Detached launcher
  with the finish-line post (rule below).
- `uv run python eval/auto_metrics.py --raw eval/results/base-test-sample-raw.jsonl --refs eval/results/test-sample-refs.jsonl
  --compare eval/results/tuned-q8-test-raw.jsonl --out .scratch/e1b-base-auto.json --out-compare eval/results/tuned-q8-test-auto.json`.
  Do not overwrite `eval/results/base-test-sample-auto.json`; confirm the scratch base file carries the same headline numbers.
- `docs/EXPORT.md`: add a "Served-model metrics" section with the base Q8 vs tuned Q8 table (ROUGE-L, cosine, truncated, mean tokens,
  deltas with CI) next to D3's bf16 numbers, and one paragraph naming the cause of the E1 parity gap: `eval/run.py` loads the base
  with `dtype="auto"` (the pinned config says bfloat16) and applies the LoRA unmerged, while `tools/merge.py` merges in float16.

Verify: `--check-complete` PASS on 270 rows, zero errors; `uv run pytest -q`; report the served-model table and the deltas.
""",
    ),
    dict(
        id="E2", worker="grok", phase="E", title="Generate 54 challenge answers x 2 models and the blind sheet",
        due="Mon 2026-09-07 13:30", est=1.0, deps=["E1", "C1", "H1"],
        paths=["eval/results/base-challenge-raw.jsonl", "eval/results/tuned-challenge-raw.jsonl",
               "eval/results/blind-sheet.csv", "eval/results/blind-sheet.html"],
        brief="""
Produce the answers shark scores blind at 18:00 IST Monday. Do not read the answers against model names yourself.

Do:
- Confirm `eval/challenge.jsonl` sha256 matches `eval/SEAL.json` (Fable seals it after H1). Stop if it does not.
- `uv run python eval/run.py --model base --backend ollama --split challenge --check-complete` and the same with `--model tuned`
  (`ghl-support`). Serial, temperature 0.
- `uv run python eval/blind.py --split challenge` to produce the CSV and HTML sheet. Open the HTML once to confirm it renders and
  every item shows two answers; do not score anything.
- Post the sheet path and the count (54 items, 108 answers) in your report.

Verify: both raw files pass `--check-complete`; blind-key.json is not in git.
""",
    ),
    dict(
        id="E3", worker="opus", phase="E", title="Unblind, final statistics, failure write-ups",
        due="Mon 2026-09-07 20:00", est=1.0, deps=["H2"],
        paths=["eval/results/scores.jsonl", "eval/results/summary.jsonl", "eval/results/failures.jsonl",
               "docs/RESULTS.md", "docs/FAILURES.md"],
        brief="""
Turn shark's blind scores into the honest verdict.

Do:
- `uv run python eval/score.py --final --require-complete` on the scored sheet. Copy the headline table (pass rates, difference,
  95% interval, critical errors, win/tie/loss, verdict) into `docs/RESULTS.md` together with the Bitext auto-metrics comparison from D3
  and the base/tuned bench numbers from F1 if present.
- `docs/FAILURES.md`: three real failures of the tuned model (or of both) with query, both answers verbatim, the rubric reason, and a
  one-paragraph cause hypothesis grounded in the training data (cite intent counts or cleaning rules). Pick one for the Loom.
- Do not retune, rescore, or reselect anything based on challenge results. If the verdict is inconclusive or negative, write it that way.

Verify: summary.jsonl has exactly one verdict row; RESULTS.md numbers match summary.jsonl (quote both).
""",
    ),
    # ---------------- Phase F: serve and measure ----------------
    dict(
        id="F1", worker="sol", phase="F", title="serve/inference.py, serve/bench.py, bench results",
        due="Mon 2026-09-07 15:00", est=2.0, deps=["C3"],
        paths=["serve/inference.py", "serve/bench.py", "serve/bench_results.json", "docs/SERVING.md"],
        brief="""
The HTTP serving story and the measured numbers. Build against `ghl-base` now; rerun the bench on `ghl-support` once E1 lands.

Do:
- `serve/inference.py --backend {ollama,transformers} [--self-test] [--query "..."]`: Ollama backend calls `/v1/chat/completions` with the
  fixed decoding settings; transformers backend loads `artifacts/merged/` (or the base) on cpu/mps with the same prompt template and
  greedy decoding, needing neither Ollama nor bitsandbytes. `--self-test` sends the password-reset demo query and asserts a nonempty
  answer with no credential request.
- `serve/bench.py --requests 30 --concurrency 1 --check [--model ghl-base|ghl-support]`: 5 warmups then 30 fixed dev prompts serial;
  record per request prompt tokens, generated tokens, end-to-end ms, generation tokens/s (from Ollama's `eval_count`/`eval_duration`);
  report p50/p95 latency, mean tokens/s, total tokens over wall seconds, failures, cold-load time (stop and restart the model with
  `keep_alive: 0` then time the first request), hardware and Ollama version. Write `serve/bench_results.json` keyed by model tag.
  `--check` exits nonzero if any request failed or fields are missing.
- `docs/SERVING.md`: how to serve (Ollama route and the plain transformers route), the curl, how the bench measured, the numbers table.

Verify: `serve/bench_results.json` has the `ghl-base` block with 30 requests; self-test passes on both backends (transformers on cpu is
slow; one query is enough).
""",
    ),
    # ---------------- Phase G: explain and submit ----------------
    dict(
        id="G1", worker="opus", phase="G", title="README complete with results, prompt template, real-vs-cut",
        due="Tue 2026-09-08 11:30", est=2.0, deps=["E3", "F1", "E1"],
        paths=["README.md", "docs/curves.png"],
        brief="""
The README is what the grader reads first. Order and content from CONTRACTS.md section 7.

Do:
- Fill every section: model and method with reasons (from LICENSE_REVIEW, TRAINING, SELECTION); data handling and split strategy
  with the audit numbers and residual-risk statement (from data/audit.json and calibration REPORT); evaluation design and results
  (RESULTS.md tables, interval, verdict, Bitext secondary, three failures linked to FAILURES.md); exact prompt template rendered
  (from train/render.py output) and load-and-run commands for adapter, merged and Ollama routes; serving numbers from bench_results.json;
  real versus cut for time (every cut from the compressed plan section 2, plus disclosure that shark drafted-and-approved the challenge
  set and was the single blind reviewer, and the Colab Pro subscription note); production trade-offs.
- Embed `train/runs/main/curves.png` copied to `docs/curves.png`.
- Every number in the README must be traceable to a file in the repo; cite the file next to each table.

Verify: every link in README resolves (run a link checker over local paths and Hub URLs); no TODO strings remain; `uv run pytest -q` passes.
""",
    ),
    dict(
        id="G2", worker="sol", phase="G", title="Fresh-clone smoke in a temp dir",
        due="Tue 2026-09-08 12:30", est=1.0, deps=["G1", "E1"],
        paths=["docs/FRESH_CLONE_TRANSCRIPT.md"],
        brief="""
Prove the README's install-and-run steps work from nothing on this Mac.

Do:
- In `$(mktemp -d)`: `git clone` the repo (local path is fine, but use the published remote if it exists by then), checkout the
  submission tag or main, `uv sync --frozen --extra serve`, `uv run python tools/fetch_artifacts.py --manifest artifacts/manifest.json --target serve`,
  `uv run python tools/check_artifacts.py ...`, `ollama create ghl-support -f serve/Modelfile`, `uv run python serve/inference.py --backend ollama --self-test`,
  the curl from CONTRACTS.md section 6. Follow the README literally; do not fix things in the temp clone.
- Save the full transcript with timings to `docs/FRESH_CLONE_TRANSCRIPT.md`. Any step that needed a deviation is a README bug:
  list them at the top and post them to Fable, do not edit the README yourself.

Verify: transcript ends with the curl JSON showing a nonempty answer; deviation list present (possibly "none").
""",
    ),
    dict(
        id="G3", worker="opus", phase="G", title="Loom shot list, demo driver, submission.json, check_submission",
        due="Tue 2026-09-08 13:30", est=1.0, deps=["G1"],
        paths=["docs/LOOM_SHOTLIST.md", "serve/demo.py", "submission.json", "tools/check_submission.py"],
        brief="""
Make the 3-minute recording mechanical for shark at 14:00 IST Tuesday.

Do:
- `serve/demo.py`: runs the two demo queries and the policy probe side by side (base tag, tuned tag) printing query, both answers, and
  latency, then prints the headline table from summary.jsonl and the chosen failure from FAILURES.md. One command, no arguments.
- `docs/LOOM_SHOTLIST.md`: 5 shots, 3 minutes total, exact commands to type and what to say in one sentence each (Astra plan section 7
  timings compressed). Include the pre-flight: Ollama running, both tags present, terminal font size, windows to close.
- `submission.json`: repo URL, tag, Hub links (adapter, merged, GGUFs), Loom link placeholder, README path, contact, `submitted_at` null.
- `tools/check_submission.py submission.json`: every URL returns 200 without auth, Loom link non-null, tag exists, manifest hashes match,
  README has no TODO. Exit nonzero otherwise.

Verify: `uv run python serve/demo.py` runs end to end; `check_submission.py` fails only on the Loom placeholder.
""",
    ),
]

HUMAN = [
    dict(id="H0", title="Colab Pro GPU attached, nvidia-smi pasted; Kaggle T4 backup confirmed; HF token available; recruiter asked (endpoint vs artifacts)",
         due="Sat 2026-09-05 23:30", deps=[]),
    dict(id="D2", title="Run notebooks/train_colab.ipynb on Colab Pro: smoke, then full epoch 1 (Opus on standby for errors); download the run zip",
         due="Sun 2026-09-06 16:30", deps=["D1", "B1", "H0"]),
    dict(id="H1", title="Edit and approve the 54 challenge queries and rubric (45 min); Fable seals the hash right after",
         due="Sun 2026-09-06 12:15", deps=["B3"]),
    dict(id="H2", title="Blind-score 108 answers on the sheet (90 min)",
         due="Mon 2026-09-07 19:30", deps=["E2"]),
    dict(id="H3", title="Record the 3-minute Loom (45 min)",
         due="Tue 2026-09-08 15:00", deps=["G3", "G2"]),
    dict(id="H4", title="Submit; post the receipt in the thread",
         due="Tue 2026-09-08 18:00", deps=["H3", "G3"]),
]

FABLE = [
    dict(id="R-A", title="Review A1-A3, commit, dispatch wave B", deps=["A1", "A2", "A3"], due="Sun 2026-09-06 09:00"),
    dict(id="R-B", title="Freeze split hashes, seal challenge (eval/SEAL.json) after H1, dispatch C/D", deps=["B1", "H1"], due="Sun 2026-09-06 12:30"),
    dict(id="CP1", title="Checkpoint 1 review in thread", deps=["B1", "C1", "C3", "C4", "D2"], due="Sun 2026-09-06 20:00"),
    dict(id="CP2", title="Checkpoint 2 review in thread with the honest verdict", deps=["E3", "F1", "E1"], due="Mon 2026-09-07 20:00"),
    dict(id="R-G", title="Final read of README, links in private window, watch Loom", deps=["G1", "G2", "G3", "H3"], due="Tue 2026-09-08 17:00"),
]


def task_md(n: dict) -> str:
    deps = ", ".join(n["deps"]) or "none"
    paths = "\n".join(f"- `{p}`" for p in n["paths"])
    return f"""# Task {n['id']}: {n['title']}

- Worker: {WORKERS[n['worker']]}
- Phase: {n['phase']}
- Due (IST): {n['due']}
- Estimate: {n['est']} h
- Depends on: {deps}
- Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`
- Read first: `docs/dag/CONTRACTS.md`, then the briefs of your dependencies under `docs/dag/tasks/`, then `docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md` section 2 and the Astra plan sections 5 and 6 for the traps and evaluation rules.

## Owned paths (write only here)

{paths}

If you need a change outside these paths, describe it in your report; do not make it.

## Brief
{n['brief'].rstrip()}

## Rules for every task

- Work in the repo above on `main`. Commit with `git add <your paths only>` and message `{n['id']}: <what>`; never `git add -A`; never amend or rebase; pull before commit if the index is locked, retry once.
- Run only under `uv run` in the repo venv (Python 3.11). System python is 3.14 and is off limits.
- No emojis anywhere. IST timestamps, labeled. No secrets in files (HF tokens stay in env).
- Do not start training, do not touch `eval/challenge.jsonl` after it is sealed, do not read blind keys.
- Report back in the GoHighLevel-prep thread (root `{THREAD}`) with `@Fable 5.1`: what landed (paths), the verification command output, anything you could not do and why. One message when done or blocked; no acknowledgement messages.
- Detached jobs (anything you launch with `Popen(start_new_session=True)` or a launcher script that outlives your turn): the launcher script itself must post the finish line to this thread with `buzz messages send --channel 04861c85-e907-4639-9075-7c474cbd8b51 --reply-to {THREAD} --mention c8ab0f4dfbc279dd4d4437a153d595c3a03bf710f1641e36691c888f53ba4c9d`, carrying the exit code and the result line, on both success and failure. Write that line into the script at the same time as the run command. A log file is not a callback, your session will not be awake when the job ends, and a post that mentions only yourself wakes nobody (D2L stalled 58 minutes, D3 stalled four hours on 2026-09-06).
"""


def build():
    TASKS.mkdir(parents=True, exist_ok=True)
    for n in NODES:
        (TASKS / f"{n['id']}.md").write_text(task_md(n))
    counts = {w: sum(1 for n in NODES if n["worker"] == w) for w in WORKERS}
    total = len(NODES)
    dag = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "channel": CHANNEL, "thread": THREAD,
        "share_target": {"opus": 0.5, "sol": 0.25, "grok": 0.25},
        "share_actual": {w: round(c / total, 2) for w, c in counts.items()},
        "counts": counts,
        "nodes": [
            {k: n[k] for k in ("id", "worker", "phase", "title", "due", "est", "deps", "paths")} for n in NODES
        ] + [dict(id=h["id"], worker="shark", phase="H", title=h["title"], due=h["due"], est=None, deps=h["deps"], paths=[]) for h in HUMAN]
          + [dict(id=f["id"], worker="fable", phase="R", title=f["title"], due=f["due"], est=None, deps=f["deps"], paths=[]) for f in FABLE],
    }
    (DAG_DIR / "DAG.json").write_text(json.dumps(dag, indent=2) + "\n")
    status_path = DAG_DIR / "STATUS.json"
    if not status_path.exists():
        status_path.write_text(json.dumps({n["id"]: {"state": "pending", "note": ""} for n in dag["nodes"]}, indent=2) + "\n")
    render_html(dag, json.loads(status_path.read_text()))
    return dag


COLORS = {"opus": "#b8860b", "sol": "#2e6f9e", "grok": "#6b4c9a", "shark": "#b23b3b", "fable": "#3d7a4a"}


def render_html(dag: dict, status: dict):
    nodes = dag["nodes"]
    by_phase: dict[str, list] = {}
    for n in nodes:
        by_phase.setdefault(n["phase"], []).append(n)
    phase_names = {"A": "A. Access and scaffold (Sat night)", "B": "B. Data and sealed cases (Sun morning)",
                   "C": "C. Harness and base first (Sun afternoon)", "D": "D. Train and choose (Sun-Mon)",
                   "E": "E. Export and final proof (Mon)", "F": "F. Serve and measure (Mon)",
                   "G": "G. Explain and submit (Tue)", "H": "Shark (human) nodes", "R": "Fable review gates"}
    rows = []
    for ph in "ABCDEFGHR":
        if ph not in by_phase:
            continue
        rows.append(f"<h2>{html.escape(phase_names[ph])}</h2><table><tr><th>id</th><th>worker</th><th>task</th><th>due IST</th><th>est h</th><th>depends on</th><th>state</th></tr>")
        for n in by_phase[ph]:
            st = status.get(n["id"], {}).get("state", "pending")
            note = status.get(n["id"], {}).get("note", "")
            rows.append(
                f"<tr><td><b>{n['id']}</b></td><td><span class=w style='background:{COLORS[n['worker']]}'>{n['worker']}</span></td>"
                f"<td>{html.escape(n['title'])}</td><td>{html.escape(n['due'])}</td><td>{n['est'] if n['est'] is not None else ''}</td>"
                f"<td>{', '.join(n['deps']) or '-'}</td><td class='st-{st}'>{st}{(' - ' + html.escape(note)) if note else ''}</td></tr>")
        rows.append("</table>")
    counts = dag["counts"]
    total = sum(counts.values())
    edges = []
    for n in nodes:
        for d in n["deps"]:
            edges.append(f"{d} --> {n['id']}")
    mermaid = "graph LR\n" + "\n".join(f"  {n['id']}[\"{n['id']}<br/>{html.escape(n['title'][:38])}\"]:::{n['worker']}" for n in nodes) + "\n" + "\n".join("  " + e for e in edges)
    mermaid += "\n" + "\n".join(f"  classDef {w} fill:{c},color:#fff,stroke:#333;" for w, c in COLORS.items())
    doc = f"""<!doctype html><html><head><meta charset=utf-8><title>GHL SLM task DAG</title>
<style>body{{font:15px/1.45 -apple-system,Helvetica,Arial;margin:32px;max-width:1200px;color:#222}}
table{{border-collapse:collapse;width:100%;margin:8px 0 24px}}th,td{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f3f3f3}}.w{{color:#fff;padding:2px 8px;border-radius:4px;font-size:13px}}
.st-done{{color:#2e7d32;font-weight:600}}.st-running{{color:#b26a00;font-weight:600}}.st-blocked{{color:#b23b3b;font-weight:600}}.st-pending{{color:#777}}
.legend span{{margin-right:12px}}.mermaid{{background:#fafafa;border:1px solid #eee;padding:12px;overflow:auto}}
h2{{margin-top:28px;font-size:18px}}code{{background:#f3f3f3;padding:1px 4px}}</style>
<script type=module>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,securityLevel:'loose',flowchart:{{useMaxWidth:false}}}});</script>
</head><body>
<h1>GHL SLM assignment: task DAG</h1>
<p>Generated {dag['generated_at']}. Source: <code>docs/dag/DAG.json</code>, briefs under <code>docs/dag/tasks/</code>, contracts in <code>docs/dag/CONTRACTS.md</code>, live state in <code>docs/dag/STATUS.json</code>.</p>
<p class=legend>Worker share of the {total} worker nodes:
<span class=w style="background:{COLORS['opus']}">Opus {counts['opus']} ({dag['share_actual']['opus']:.0%})</span>
<span class=w style="background:{COLORS['sol']}">Sol {counts['sol']} ({dag['share_actual']['sol']:.0%})</span>
<span class=w style="background:{COLORS['grok']}">Grok {counts['grok']} ({dag['share_actual']['grok']:.0%})</span>
<span class=w style="background:{COLORS['shark']}">shark</span> <span class=w style="background:{COLORS['fable']}">Fable gates</span></p>
<p>Fable orchestrates, reviews every deliverable before dispatching dependents, and takes over any node that fails review twice. Astra is the escalation for B1, C1 and E3 only if Opus is late.</p>
<div class=mermaid>{mermaid}</div>
{''.join(rows)}
</body></html>"""
    (DAG_DIR / "DAG.html").write_text(doc)


if __name__ == "__main__":
    d = build()
    print(json.dumps({"nodes": len(d["nodes"]), "counts": d["counts"], "share": d["share_actual"]}))
