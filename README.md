# Customer-support SLM: v3 submission closeout

Fine-tuned Qwen2.5-1.5B-Instruct for customer support, with reproducible training,
evaluation, artifact packaging, and localhost serving. The default branch is the
v3 submission state described by [`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md).

## Index

- [Understand the project in 60 seconds](#understand-the-project-in-60-seconds)
- [Open the demo, deck, or notebooks](#open-the-demo-deck-or-notebooks)
- [Run or verify v3](#run-or-verify-v3)
- [Read the closeout result](#read-the-closeout-result)
- [Choose a deeper path](#choose-a-deeper-path)
- [Navigate the repository](#navigate-the-repository)
- [Understand evidence boundaries](#understand-evidence-boundaries)
- [Find historical versions](#find-historical-versions)

## Understand the project in 60 seconds

| Version | What changed | Recorded result | Decision |
|---|---|---|---|
| v1 | QLoRA on cleaned Bitext responses | On 54 sealed cases, task success fell from 29.6% to 13.0%; critical failures rose from 2 to 8 | Rejected |
| v2 | Repaired placeholders and added 206 examples that admit missing facts | On a new 54-case set, task success rose from 14.8% to 22.2%, but the interval crossed zero and critical failures rose from 6 to 12 | Rejected |
| v3 candidate03 | Curated targets, supplied-context examples, stronger leakage screening, stricter prompt, and new evaluation | On 106 graded pairs, task success rose from 55.7% to 76.4%; credential violations rose from 1 to 2 | Final demonstrated artifact; safety gate failed |
| v3 candidate04 | Added 18 boundary examples and trained on a free Colab T4 | Every checkpoint failed development selection | Rejected; did not replace candidate03 |

Evaluation sets and judging changed between versions. Compare base with tuned
within a row; do not compare absolute rates across rows.

The shortest defensible conclusion: candidate03 learned useful support-response
patterns and improved recorded v3 task success, but credential handling remained
unsafe. V3 is an evidence-backed closeout, not a claim of production readiness.

## Open the demo, deck, or notebooks

- [Watch the 2:47 captioned demo](https://github.com/Imsharad/ghl-support-slm/releases/download/v3-submission.1/demo.mp4)
- [Download the editable six-slide reviewer deck](docs/v3/GHL-Support-SLM-v3-reviewer-deck.pptx)
- [![Open the v3 evidence walkthrough in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Imsharad/ghl-support-slm/blob/main/notebooks/v3_evidence_walkthrough.ipynb)
- [![Open candidate04 training in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Imsharad/ghl-support-slm/blob/main/notebooks/v3_candidate04_colab.ipynb)

The evidence notebook is a no-GPU tour of the published result. The training
notebook reproduces candidate04, whose checkpoints were all rejected; there is no
published candidate03 training notebook.

## Run or verify v3

Real base-and-tuned startup, inference, and shutdown:

```sh
./start.sh --check
```

Keep the localhost comparison API running:

```sh
./start.sh
```

First run needs network access and about 4.5 GB of downloads. Supported launcher
hosts are Apple Silicon macOS and Linux x86_64 with glibc. A GPU is optional.

Read-only verification of the published arithmetic:

```sh
uv sync --frozen --extra serve
uv run python -m eval.replay_published_v3
```

For source reconstruction, all tests, manual serving, ports, logs, and
troubleshooting, use the [`v3 reviewer runbook`](docs/v3/REVIEWER_RUNBOOK.md).

## Read the closeout result

Candidate03 step120 is the final evaluated and served artifact. Candidate04
trained successfully but failed selection. Experimentation is closed for this
submission, and no successful safety qualification is claimed.

| Evidence | Base | Tuned | Interpretation |
|---|---:|---:|---|
| Recorded task success, 106 pairs | 59 (55.7%) | 81 (76.4%) | +20.75 points; post-hoc mixed judging |
| Critical failures | 11 | 9 | Lower observed count |
| Credential/verification violations | 1 | 2 | Fixed zero-violation safety gate failed |
| Historical v1 served ROUGE-L, 270 rows | 0.2153 | 0.3667 | Reference conformity, not verified accuracy |

V3 intent-macro gain was +21.60 points, with a 95% paired intent-cluster interval
of [8.95, 34.26]. The 106 recorded judgments comprise 29 human and 77
human-calibrated Terra judgments; two pairs were omitted. The preregistered
all-human primary evaluation was not completed.

### What “critical failure” means

An answer is a critical failure if it invents company policy, account or order
status, a completed action, or a factual timeline, or asks for a password or full
payment-card number. One such failure fails the entire evaluation item even when
the rest of the answer is useful.

A credential/verification violation is the security-sensitive subset used by
v3's fixed zero-violation gate. The exact definitions and examples are in
[`eval/RUBRIC.md`](eval/RUBRIC.md).

### Material disclosures

- Candidate03 used about $0.45 of owner-authorized RunPod credit, a disclosed
  deviation from the brief's free-compute requirement.
- Candidate04 used a free Colab T4, completed 120 updates in 519.8 seconds with
  3.32 GB peak GPU memory, and was rejected after a separate 330-response MPS
  development review.
- Partial CUDA and complete MPS development results were not pooled.
- The API has no authentication, TLS, retrieval, or account tools. Keep it on
  localhost.

## Choose a deeper path

| If you need to… | Start here | Then inspect |
|---|---|---|
| Run the system or tests | [`Reviewer runbook`](docs/v3/REVIEWER_RUNBOOK.md) | [`start.sh`](start.sh), [`serve/`](serve/) |
| Audit the submission package | [`Submission checklist`](docs/v3/SUBMISSION_CHECKLIST.md) | [`submission.json`](submission.json), [`artifacts/v3/`](artifacts/v3/) |
| Reconstruct what happened | [`Execution plan and log`](docs/v3/PLAN.md) | [`Pre-registration`](docs/v3/PRE_REGISTRATION.md) |
| Understand model selection | [`Selection record`](docs/v3/SELECTION.md) | [`candidate03 parity`](docs/v3/parity-candidate03-step120.md) |
| Audit scoring and failures | [`Scoring rubric`](eval/RUBRIC.md) | [`final v3 results`](eval/results/v3/final01/) |
| Inspect training data construction | [`candidate03 manifest`](data/v3/candidate03_manifest.json) | [`data/assemble_v3.py`](data/assemble_v3.py) |
| Inspect exact served artifacts | [`v3 manifest`](artifacts/v3/manifest.json) | [`prompt-v3.txt`](configs/prompt-v3.txt) |
| Review measured HTTP performance | [`paired warm summary`](eval/results/v3/paired-api-warm02/summary.json) | [`benchmark tool`](serve/bench_api.py) |
| Review v1/v2 | [`Historical results`](docs/RESULTS.md) | [`v2 evidence map`](docs/v2/EVIDENCE.md) |

AI reviewers should also read [`AGENTS.md`](AGENTS.md). It states the current
truth, minimum verification order, and evidence boundaries without requiring a
conversation with the repository owner.

## Navigate the repository

The top-level directories are deliberate. They separate executable code from
recorded evidence and retained history; deleting or flattening them would break
reproduction paths.

| Path | Purpose |
|---|---|
| [`configs/`](configs/) | Exact prompts and experiment configuration |
| [`data/`](data/) | Pinned source reconstruction, derived datasets, and manifests |
| [`train/`](train/) | Training and rendering code |
| [`eval/`](eval/) | Evaluation code, rubric, sealed sets, and recorded results |
| [`serve/`](serve/) | Local comparison API and model definitions |
| [`tools/`](tools/) | Artifact, release, demo, and integrity utilities |
| [`tests/`](tests/) | Automated regression and evidence-integrity tests |
| [`artifacts/`](artifacts/) | Source and served-weight manifests; large weights stay external |
| [`notebooks/`](notebooks/) | Colab entry points and historical notebooks |
| [`docs/v3/`](docs/v3/) | Current reviewer records and operational detail |
| [`docs/v2/`](docs/v2/) | Preserved v2 records |
| [`docs/dag/`](docs/dag/) | Historical task-graph evidence |
| [`docs/plans/`](docs/plans/) | Historical implementation plans |
| [`docs/prompts/`](docs/prompts/) | Preserved experiment prompts |
| [`docs/research/`](docs/research/) | Supporting research notes |
| [`docs/sessions/`](docs/sessions/) | Historical execution-session records |

Local `.runtime/`, `.venv/`, `.pytest_cache/`, and `.scratch/` directories are
gitignored runtime state, not part of the GitHub submission.

## Understand evidence boundaries

- Treat `eval/results/v3/final01/` as immutable recorded evidence.
- Do not invent the two omitted grades or the private blind key.
- Do not infer safety from falling loss, reference similarity, or task-success
  gain alone.
- Do not use validation loss as proof of response quality or safety.
- Do not compare absolute pass rates across v1, v2, and v3.
- Do not retrain unless a new experiment is explicitly intended.

Published artifacts:

- [GitHub v3 release](https://github.com/Imsharad/ghl-support-slm/releases/tag/v3-submission.1)
- [Exact candidate03 adapter](https://huggingface.co/seekingtroooth/ghl-support-qlora-t4/tree/cc4a1e2affcf5c8db315e35d9b41cb7d4f6e1684/v3/adapter)
- [Served artifact manifest](artifacts/v3/manifest.json)

## Find historical versions

- `main`: current v3 submission state
- `v3-submission.1`: immutable v3 release tag
- `v2`: preserved branch and tag for the v2 closeout
- `v1`: annotated tag preserving the former default-branch tip

Historical details remain available under [`docs/`](docs/) and in the versioned
branches/tags. They are intentionally not repeated in this README.

Base model: Qwen2.5-1.5B-Instruct, Apache-2.0. Dataset: Bitext customer-support
dataset, CDLA-Sharing-1.0; see [`artifacts/sources.json`](artifacts/sources.json).
