# Notebooks

Four notebooks cover the current v3 review path and the historical v2 run.

| file | what it is |
|---|---|
| [`v3_evidence_walkthrough.ipynb`](v3_evidence_walkthrough.ipynb) | The fastest v3 review path. CPU-only and read-only: loads the recorded comparison, defines critical failures, visualizes the result, inspects the exact contract, and replays published arithmetic. [Open in Colab](https://colab.research.google.com/github/Imsharad/ghl-support-slm/blob/main/notebooks/v3_evidence_walkthrough.ipynb). |
| [`v3_candidate04_colab.ipynb`](v3_candidate04_colab.ipynb) | Runnable free-T4 reconstruction, smoke, and 120-update training for candidate04. Candidate04 was rejected at every checkpoint and did not replace the submitted candidate03 model. [Open in Colab](https://colab.research.google.com/github/Imsharad/ghl-support-slm/blob/main/notebooks/v3_candidate04_colab.ipynb). |
| [`train_colab.ipynb`](train_colab.ipynb) | The runnable notebook. Eleven code cells, top to bottom on a free Colab T4, about 1.5 hours. Open it with the badge in its first cell; it forks into your own Drive, so running it cannot change what is committed here. |
| [`v2_colab_run.ipynb`](v2_colab_run.ipynb) | The executed record of the run that produced the scored v2 model, committed with every cell output as it ran. Read this one to audit; run the other one to reproduce. |

## v3 notebook status

The submitted and served v3 artifact is **candidate03 step120**, originally trained
on RunPod. The evidence notebook audits its published records without retraining.
The runnable GPU notebook covers the later free-Colab candidate04 experiment because
that is the v3 training run actually completed on Colab. Its failure is part of the
record: successful training and falling validation loss did not make any checkpoint
safe or eligible.

The remainder of this file documents the two historical v2 notebooks.

## What the notebook does

GPU check and pinned versions, clone at a pinned commit, the pinned base model into the local cache, the v2 data (substitution cleaning plus the 206 admission rows) with the strict audit, the frozen config printed, a smoke run with a resume proof and its gate, one epoch, the loss curve and the completeness gate, dev answers for every checkpoint, then a zip of the whole run directory.

Nothing needs a secret. The repository is public, so the clone is unauthenticated, and the run trains with `--no-push`, so no Hugging Face token is required; artifacts leave the VM as the zip in the last cell.

## The run that is committed here

| | value |
|---|---|
| substrate | free Colab T4, `configs/train-t4.yaml` unchanged |
| data | `data/processed/v2` (8,000-row cap: 7,794 corpus rows plus 206 admission rows, exempt from the cap) |
| steps / wall | 500 (one epoch) / 4832 s |
| peak memory | 2.94 GB (the gate allows 12) |
| git sha | `33bdbbd` |
| selected checkpoint | 250, on dev only ([`docs/SELECTION.md`](../docs/SELECTION.md)) |

## Two cells errored in the committed run, and both are fixed in the source

The executed copy is kept exactly as it ran, with a note at the top. Neither error touched the training or the gate.

1. **Smoke cell.** A 64-row smoke cap cannot exempt 206 admission rows. `cap_train_rows` now falls back to a uniform group cap when the cap is at or below the admission count; the real 8,000-row cap never takes that branch.
2. **Dev-answers cell.** The evaluation runner is launched as a subprocess and needed the repository root on `PYTHONPATH`. The dev answers were regenerated on the same VM with the fixed command; that log is the last cell of the executed copy.

## Free-tier facts worth planning around

- A free T4 can be reclaimed mid-run. One was, at step 190 of an identical earlier run. The second run pulled every checkpoint off the VM as it was written, so a reclaim would have cost minutes rather than the epoch.
- The CLI's runtime-proxy token expires hourly. The session then looks lost while the VM keeps running; reattaching restores it without losing anything.
- CUDA training is not bit-reproducible across GPUs and driver versions. A re-run reproduces the split hashes and the gates exactly, and the loss curve and pass rates approximately.

## Colab Pro

Switch the config in the configuration cell to `configs/train.yaml` for the full 17,701-row split on an A100 or L4. Do not run the full split on a free T4; it will not finish in one session. The committed run and every number in [`docs/RESULTS.md`](../docs/RESULTS.md) use the T4 config.
