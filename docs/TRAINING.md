# Training

QLoRA fine-tune of `Qwen2.5-1.5B-Instruct` on the grouped Bitext train split, one epoch,
assistant-only loss. Everything below runs from the repository root.

Hyperparameters are fixed by `docs/dag/CONTRACTS.md` section 5. The two configs differ in
one line only, the number of train rows.

| Config | Train rows | Target machine |
|---|---|---|
| `configs/train.yaml` | full grouped split (17,701 rows at `24ab0d9`) | Colab Pro, A100 or L4 |
| `configs/train-t4.yaml` | 8,000 rows, group-aware cap | free Colab T4 |

The cap is the same routine `data/prepare.py --cap-train` uses, so whole similarity groups stay
on one side of the split and every intent keeps a share.

## Colab Pro, one click

Open `notebooks/train_colab.ipynb` in Colab, choose an A100 or L4 runtime, and run the cells in
order. They do: `nvidia-smi`, clone at a branch or tag, install the pinned versions from
`configs/versions.json`, read `HF_TOKEN` from Colab secrets, regenerate the data, run the smoke,
run the full epoch, generate dev answers for every checkpoint, plot the curves, zip the run.

Nothing is mounted. Every artifact lands in `train/runs/<run_name>/` and the last cell downloads
that directory as a zip.

## Free T4

Same notebook, one edit: in the full-run cell set

```python
CONFIG = 'configs/train-t4.yaml'
```

The T4 has 16 GB and this shape peaks near 4 GB, so the cap is about wall time, not memory.

## Local fallback on the M1 Pro Mac

There is no CUDA on the Mac, so the default config stops with a message that names the fix:

```sh
uv run python train/train.py --config configs/train.yaml
# device 'cuda' was requested but no CUDA GPU is visible. ... run with --device mps
```

MPS works. Node D0 measured 2.567 s/step for exactly this shape at 512 tokens
(`docs/LOCAL_QLORA_PROBE.md`). Add `--device mps` to any command here. This is a fallback for a
dead cloud path, not the default: a full epoch is hours rather than minutes.

## Commands

```sh
# smoke: 20 steps, then a resume from step 10 that must reproduce steps 11 to 20
uv run python train/train.py --config configs/train.yaml --smoke --data-dir data/processed

# full run
uv run python train/train.py --config configs/train.yaml

# continue after a dropped session, from the newest checkpoint
uv run python train/train.py --config configs/train.yaml --resume

# gate the run directory before trusting the adapter
uv run python tools/check_run.py train/runs/ghl-support-qlora --max-memory-gb 12

# loss curves
uv run python train/plot_curves.py train/runs/ghl-support-qlora
```

Useful overrides: `--device`, `--data-dir`, `--cap-train`, `--max-steps`, `--run-name`, `--no-push`.

## What the smoke proves

`--smoke` trains 20 steps on up to 64 rows, deletes every checkpoint after step 10, resumes from
step 10, and compares the logged train losses at the steps both phases reached. The comparison
lands in `train/runs/<run>/smoke.json` with `ok`, the two loss series and `max_abs_diff`. The
resume replays the same data order (the micro-batch cursor is stored) and restores the optimizer,
the scheduler and the RNG state, so a match means resume is real rather than merely not crashing.
`tools/check_run.py` fails if `smoke.json` says `ok: false`.

Without `--data-dir`, the smoke reads `tests/fixtures/train_smoke/`, a 16-row synthetic fixture
with no Bitext text in it, so the path can be exercised on a machine with no processed data.
On Colab point it at `data/processed` for the 64-row shape.

## Run directory

```
train/runs/<run_name>/
  config.json                 resolved config, git sha, installed versions, wall_s, peak_memory_gb
  loss.csv                    step, epoch, lr, train_loss, val_loss, elapsed_s, peak_memory_gb
  curves.png                  written by train/plot_curves.py
  smoke.json                  smoke runs only: the resume comparison
  checkpoint-<step>/          adapter weights, state.pt (optimizer, scheduler, cursor, RNG), trainer_state.json
  dev-checkpoint-<step>-raw.jsonl   written by the notebook, one row per dev item
```

Checkpoints land every 100 optimizer steps, at 50 percent and 100 percent of the run, and at the
final step. `checkpoint-*/` is gitignored; `loss.csv`, `config.json`, `smoke.json` and `curves.png`
are small enough to commit.

## Hugging Face pushes

`hub.repo_id` in the config names the adapter repo. The token comes from the environment variable
`HF_TOKEN`, never from a file. With no token the run prints one warning and keeps every checkpoint
local. A failed push warns and the run continues; training is never lost to a network error.

## Expected wall time

Planning estimates, not measurements. Replace them with the real `wall_s` from `config.json` once
a run finishes.

| Machine | Rows | Estimate |
|---|---|---|
| A100 or L4 | 17,701 | 30 to 60 min for one epoch |
| Free T4 | 8,000 | 1 to 1.5 h for one epoch |
| M1 Pro, MPS | 17,701 | measured 2.567 s/step, so about 1.5 h per 2,000 optimizer steps |

Memory: the D0 probe peaked at 4.09 GB for this shape, which is why `check_run.py` gates at 12 GB.

## What to paste back into the thread

- From `config.json`: `wall_s`, `peak_memory_gb`, `final_step`, `git_sha`, `versions`.
- From `smoke.json`: `ok` and `max_abs_diff`.
- The last few rows of `loss.csv`.
- The checkpoint list and the row count of each `dev-checkpoint-*-raw.jsonl`.
- The run zip, or the Hub repo URL when the push worked.
