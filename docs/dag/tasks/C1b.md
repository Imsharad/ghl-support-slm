# Task C1b: eval/run.py --adapter: score a PEFT adapter without merging

- Worker: Grok
- Phase: C
- Due (IST): Sun 2026-09-06 02:30
- Estimate: 1.0 h
- Depends on: C1, D1
- Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`
- Read first: `docs/dag/CONTRACTS.md`, then the briefs of your dependencies under `docs/dag/tasks/`, then `docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md` section 2 and the Astra plan sections 5 and 6 for the traps and evaluation rules.

## Owned paths (write only here)

- `eval/run.py`
- `tests/test_eval.py`

If you need a change outside these paths, describe it in your report; do not make it.

## Brief

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

## Rules for every task

- Work in the repo above on `main`. Commit with `git add <your paths only>` and message `C1b: <what>`; never `git add -A`; never amend or rebase; pull before commit if the index is locked, retry once.
- Run only under `uv run` in the repo venv (Python 3.11). System python is 3.14 and is off limits.
- No emojis anywhere. IST timestamps, labeled. No secrets in files (HF tokens stay in env).
- Do not start training, do not touch `eval/challenge.jsonl` after it is sealed, do not read blind keys.
- Report back in the GoHighLevel-prep thread (root `1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593`) with `@Fable 5.1`: what landed (paths), the verification command output, anything you could not do and why. One message when done or blocked; no acknowledgement messages.
