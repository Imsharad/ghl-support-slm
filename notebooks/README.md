# `train_colab.ipynb`

Written 2026-09-07 (task V2-C0). This notebook has never been executed on Colab; v1 trained
on the Mac (`docs/LOCAL_RUN.md`). It is meant to run clean, top to bottom, on the first try.

## Colab secrets (key icon, left sidebar)

| Secret | Required | Used for |
|---|---|---|
| `GITHUB_TOKEN` | Yes, repo is private | Cloning `Imsharad/ghl-support-slm`. A fine-grained PAT with read-only access to that one repo is enough. |
| `HF_TOKEN` | No, but strongly recommended | Pushing adapter checkpoints to the private Hub repo as they train (`configs/train*.yaml` `hub.repo_id`), so the run survives a dropped session. Without it, training still completes; checkpoints stay local and must come back via the zip download in section 12. |

Both secrets need "Notebook access" toggled on for this notebook in the Colab secrets panel, not
just added to the account.

## Runtime

Runtime menu -> Change runtime type -> GPU. Two shapes matter here:

- **Free T4**: the default. `CONFIG = 'configs/train-t4.yaml'` (section 6) matches it: 8,000-row
  cap, the same config the v1 served checkpoint (`checkpoint-400`) was trained on. This is the v2
  headline substrate if it finishes clean.
- **Colab Pro, A100 or L4**: switch section 6 to `CONFIG = 'configs/train.yaml'` (full 17,701-row
  split). Do not run the full split on a free T4; it will not finish in one session.

## Expected wall time per section

Planning estimates from `docs/TRAINING.md`, not measurements — the real number is `wall_s` in
`train/runs/<run>/config.json` after the run.

| Section | Free T4 | A100 / L4 |
|---|---|---|
| 3. Install pinned versions | 1-2 min | 1-2 min |
| 5. Data (fetch + prepare) | a few min, dataset-fetch-bound | same |
| 7. Smoke run (20 steps, 64 rows) | 1-2 min | under 1 min |
| 8. Full run | roughly 1 to 1.5 h (8,000 rows) | 30 to 60 min (17,701 rows) |
| 9. Dev answers per checkpoint | a few min per checkpoint, 6 checkpoints | faster |
| 11. Ollama cell (optional) | several min, one-time llama.cpp build | same |

## The headline rule

Fixed in the GoHighLevel-prep thread before either run started, so it cannot be gamed after the
fact: **this Colab run is the v2 headline training substrate if it finishes clean by 04:00 IST
Tuesday.** Otherwise the parallel Mac `mps` run (`docs/LOCAL_RUN.md`) is, and `docs/RESULTS.md`
says which. CUDA and `mps` are not bit-identical, which is why the rule exists.

Either way, **scoring always runs on the sealed Mac Ollama path** (`docs/dag/CONTRACTS.md`
section 6: Q8 GGUF through Ollama, the pipeline that scored v1). The notebook's own Ollama cell
(section 11) is a visible cross-check of the serving path on Colab, not a second scoring run —
it is optional and safe to skip.

## `DATA_MODE`

Section 5 has a `DATA_MODE` switch:

- `'v1'`: `data/prepare.py` exactly as v1 ran it (reject-only placeholder cleaning). Regenerates
  `data/processed/*.jsonl` and checks the hashes against `data/splits.json`, the frozen v1 evidence.
- `'v2'`: substitute-placeholder cleaning, `data/prepare.py --placeholder-mode substitute --out
  data/v2`. V2-B1 (Opus) landed this flag before this notebook was finished; verified locally on
  the Mac (CPU/mps, not Colab/CUDA): `wrote train=20926 val=2753 test=3085 groups=4877`, `strict:
  hashes and intersections match`, and a smoke train run against `data/processed/v2` with
  `--device mps` completed with `resume match ok=True max_abs_diff=0.00052`.

## What could not be tested off Colab

- The GPU-only cells: `nvidia-smi`, `bitsandbytes` 4-bit loading, the smoke run, the full run, and
  everything downstream of them. No CUDA on the machine that wrote this notebook.
- The `google.colab.userdata` and `google.colab.files` calls (sections 2, 4, 12) — they only exist
  inside a real Colab kernel; a plain `import` fails outside Colab, which is why every cell that
  needs a secret already wraps the import in `try/except` and prints a fallback message instead of
  crashing.
- The Ollama cell's `apt-get`, the Ollama Linux installer, and `tools/convert.sh`'s cmake build —
  these need a real Linux Colab VM; not reproducible from the M1 Mac shell that authored this file.
- The full run and per-checkpoint dev-answer loop (sections 8-9) on CUDA specifically: run on `mps`
  only as a smoke proof (20 steps), not the full epoch, and never on an actual GPU.
- The clone cell's `google.colab.userdata` path and the final `google.colab.files.download` call —
  they only exist inside a real Colab kernel; a plain `import` fails outside Colab, which is why
  every cell that needs one already wraps the import in `try/except` with a fallback message.

What was checked: the notebook is valid JSON and nbformat 4; `jupyter nbconvert --to script`
transpiles it without error; every non-magic line parses as valid Python (`ast.parse`); every CLI
flag the notebook passes to `train/train.py`, `eval/run.py`, `tools/merge.py`,
`tools/check_run.py`, and `data/prepare.py` exists in that script's `argparse` block today, checked
by grep against each file. `DATA_MODE = 'v2'` and the smoke-run cell's `--data-dir` override were
additionally run for real on the Mac (CPU/mps) against the local raw CSV, not just grep-checked —
see the Data section above for the numbers.
