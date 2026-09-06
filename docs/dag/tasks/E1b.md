# Task E1b: Tuned answers on the 270 test sample through Ollama Q8 (served-model metrics)

- Worker: Sol
- Phase: E
- Due (IST): Sun 2026-09-06 13:30
- Estimate: 0.75 h
- Depends on: E1
- Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`
- Read first: `docs/dag/CONTRACTS.md`, then the briefs of your dependencies under `docs/dag/tasks/`, then `docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md` section 2 and the Astra plan sections 5 and 6 for the traps and evaluation rules.

## Owned paths (write only here)

- `eval/results/tuned-q8-test-raw.jsonl`
- `eval/results/tuned-q8-test-auto.json`
- `docs/EXPORT.md`

If you need a change outside these paths, describe it in your report; do not make it.

## Brief

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

## Rules for every task

- Work in the repo above on `main`. Commit with `git add <your paths only>` and message `E1b: <what>`; never `git add -A`; never amend or rebase; pull before commit if the index is locked, retry once.
- Run only under `uv run` in the repo venv (Python 3.11). System python is 3.14 and is off limits.
- No emojis anywhere. IST timestamps, labeled. No secrets in files (HF tokens stay in env).
- Do not start training, do not touch `eval/challenge.jsonl` after it is sealed, do not read blind keys.
- Report back in the GoHighLevel-prep thread (root `1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593`) with `@Fable 5.1`: what landed (paths), the verification command output, anything you could not do and why. One message when done or blocked; no acknowledgement messages.
- Detached jobs (anything you launch with `Popen(start_new_session=True)` or a launcher script that outlives your turn): the launcher script itself must post the finish line to this thread with `buzz messages send --channel 04861c85-e907-4639-9075-7c474cbd8b51 --reply-to 1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593 --mention c8ab0f4dfbc279dd4d4437a153d595c3a03bf710f1641e36691c888f53ba4c9d`, carrying the exit code and the result line, on both success and failure. Write that line into the script at the same time as the run command. A log file is not a callback, your session will not be awake when the job ends, and a post that mentions only yourself wakes nobody (D2L stalled 58 minutes, D3 stalled four hours on 2026-09-06).
