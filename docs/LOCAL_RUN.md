# D2L: Local QLoRA run on the M1 Pro (`train/runs/local-t4`)

The free-T4 config trained to completion on this Mac overnight, on `mps`, as insurance against
Colab staying unavailable. It finished at **03:43 IST on 2026-09-06**, exit 0, 500 optimizer steps
in 2 h 47 min. If a Colab run lands later, that one is the main run and this is the documented
fallback; until then this is the adapter D3 selects from.

## How it was launched

Detached, so it would survive the launching session:

```bash
# .scratch/d2l_run.sh, started with Popen(start_new_session=True) at 00:55:37 IST
uv run python train/train.py \
  --config configs/training/train-t4.yaml \
  --device mps \
  --data-dir data/processed \
  --run-name local-t4
```

The launcher is identified in the log's first line, so a later reader can tell this run from a
hand-started one:

```
RUN start 2026-09-06 00:55:37 IST launcher=fable
```

`--device mps` is an override, not an edit. `configs/training/train-t4.yaml` still says `device: cuda`,
because it targets a free T4; the Mac has no CUDA, and `train.py` stops with a message naming the
fix rather than falling back silently.

## What produced it

| Item | Value |
|---|---|
| Machine | Apple M1 Pro, 16 GiB unified memory, macOS 26.5 |
| Device | `mps` |
| Config | `configs/training/train-t4.yaml`, unchanged |
| Code | `ea66579` (recorded in `config.json` as `git_sha`) |
| Data text | `c19ee89` (B1b, number frame generalised) |
| Base model | `Qwen/Qwen2.5-1.5B-Instruct` at `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Python | 3.11.11, repo venv, `uv run` |
| torch / transformers / peft | 2.14.0 / 5.16.1 / 0.20.0 |
| bitsandbytes / accelerate / datasets | 0.50.2 / 1.14.0 / 5.0.1 |

The data text claim is checked, not assumed. `data/splits.json` last changed in `c19ee89`, and the
files on disk still hash to what it records:

```
uv run python data/prepare.py --audit-only --strict
  audit-only ok train=17701 val=2477 test=2270
  strict: hashes and intersections match          (exit 0)
```

Shape: NF4 4-bit with double quantisation and fp16 compute, LoRA r=16 alpha=32 dropout=0.05 on
`q_proj k_proj v_proj o_proj gate_proj up_proj down_proj`, 18,464,768 trainable parameters,
sequence length 512, micro-batch 1 with gradient accumulation 16, AdamW at lr 1e-4 on a cosine
schedule with 15 warmup steps, one epoch.

The 8,000-row cap is the group-aware routine from `data/prepare.py`, applied at load time to the
17,701-row train split, so whole similarity groups stay on one side and every intent keeps a share.
8,000 rows at grad-accum 16 is 500 optimizer steps.

## Result

| Item | Value |
|---|---|
| Started | 2026-09-06 00:55:54 IST |
| Finished | 2026-09-06 03:43:04 IST |
| Wall time | 10,028.9 s (2 h 47 min 09 s), about 20.1 s per optimizer step |
| Steps | 500 of 500, one full epoch |
| Peak memory | 8.24 GB (gate limit 12 GB) |
| Final train loss | 0.79433 |
| Final validation loss | 0.65170 |
| Exit | 0 |

Assistant-only loss, logged every 25 steps. Curves: `train/runs/local-t4/curves.png`.

| step | train | val | | step | train | val |
|---|---|---|---|---|---|---|
| 25 | 1.04698 | 1.09932 | | 275 | 0.64310 | 0.68744 |
| 50 | 1.03037 | 0.91151 | | 300 | 0.76525 | 0.67495 |
| 75 | 0.81327 | 0.86580 | | 325 | 0.66678 | 0.66702 |
| 100 | 0.84883 | 0.79704 | | 350 | 0.68445 | 0.66762 |
| 125 | 0.79240 | 0.75885 | | 375 | 0.65227 | 0.65964 |
| 150 | 0.81476 | 0.75845 | | 400 | 0.61863 | 0.65477 |
| 175 | 0.81444 | 0.72969 | | 425 | 0.69330 | 0.65485 |
| 200 | 0.83459 | 0.71575 | | 450 | 0.71277 | 0.65288 |
| 225 | 0.85512 | 0.70766 | | 475 | 0.70209 | 0.65187 |
| 250 | 0.81033 | 0.69997 | | 500 | 0.79433 | 0.65170 |

Validation fell at every logged step but two, 350 and 425, where it rose by less than 0.001, and it
was still easing at step 500, so this epoch shows no overfitting. Train loss is noisy
because each logged value is the mean over just the 16 micro-batches of that one optimizer step, a
16-example estimate, and nothing is averaged across steps; the step-500 value of 0.794 is one such
estimate, not a regression.

**Read the validation number for its trend, not its level.** `train.val_batches: 32` at micro-batch 1
means the validation loss is measured on the first 32 rows of `val.jsonl`, the same 32 rows at every
step, not on the full 2,477-row split (`config.json` records `val_rows_encoded: 32`). That makes the
curve comparable across steps, which is what a training curve is for, but it is a probe and not a
score. Checkpoint selection is D3's job and runs on dev pass rate, not on this number.

## Checkpoints

Six, 212 MB each: `adapter_model.safetensors` at 74 MB, plus a 148 MB `state.pt` holding the
optimizer, scheduler, torch RNG state and the data cursor, which is what makes a resume exact rather
than merely non-crashing.

```
train/runs/local-t4/checkpoint-100
train/runs/local-t4/checkpoint-200
train/runs/local-t4/checkpoint-250
train/runs/local-t4/checkpoint-300
train/runs/local-t4/checkpoint-400
train/runs/local-t4/checkpoint-500
```

Steps 100, 200, 300 and 400 come from `save_every: 100`; 250 and 500 from
`checkpoint_fractions: [0.5, 1.0]`. Nothing was pushed to the Hub: `HF_TOKEN` was not set, so the
adapters are local only, and `config.json` records that reason.

For D3, read a checkpoint with the C1b adapter option rather than merging it:

```bash
uv run python eval/run.py --backend transformers --model tuned \
  --adapter train/runs/local-t4/checkpoint-500 ...
```

`--adapter` requires `--backend transformers` and `--model tuned`; `eval/run.py` rejects any other
combination. It loads the pinned base itself, so no merge into `artifacts/merged` is needed.

## Verification

Run at 04:39 IST on 2026-09-06, after the run finished.

```
uv run python tools/training/check_run.py train/runs/local-t4 --max-memory-gb 12 --device mps
  loss.csv: 20 logged steps, 20 with a validation loss
  peak memory: 8.24 GB (limit 12.0 GB)
  git sha: ea665794329394bc36be8b31934011f661b2922f
  reloading checkpoint-500 on mps
  sample answer:
  I'm sorry to hear that you're having trouble signing in due to forgetting your password.
  Don't worry, I'll guide you through the process step by step:
  1. Visit our website's login page.
  2. Look for the "Forgot Password" option on the top right corner of the page.
  3. Click
  PASS: run directory is complete and the adapter reloads          (exit 0)
```

The answer stops mid-sentence because the gate generates 64 tokens; that is the check's budget, not
the adapter's behaviour. The gate loads the base model, so it needs the GPU free.

```
uv run python train/plot_curves.py train/runs/local-t4
  wrote train/runs/local-t4/curves.png from 20 logged steps
```

## What is tracked

Only this document and `train/runs/local-t4/curves.png`. The run directory stays untracked: the
checkpoint directories are 1.2 GB in total and `.gitignore` excludes `train/runs/**/checkpoint-*/`,
and `train.log` is covered by `*.log`. `loss.csv` and `config.json` are untracked by the same
convention, and everything either of them says is reproduced above.

## Notes for a rerun

- Nothing else may hold a model while this runs. Three processes died silently overnight because the
  Mac exhausted swap; macOS kills them with no traceback. Check `sysctl vm.swapusage` first and run
  one model-loading job at a time.
- Throughput improved to roughly 20 s per step once the machine was otherwise idle, against the 30 s
  planned for, which is why the run finished at 03:43 rather than the projected 06:45 IST.
- A crash costs at most 100 steps. `train.py` resumes from the newest checkpoint and restores the
  optimizer, scheduler, RNG state and the micro-batch cursor, so the data order is replayed rather
  than reshuffled; D1 proved this on the smoke fixture to within 0.003 on `mps`.
