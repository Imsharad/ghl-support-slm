# V3 reviewer runbook

This page contains the operational detail intentionally omitted from the root
README. Candidate03 step120 is the evaluated and served v3 artifact. Candidate04
is a completed but rejected experiment.

## Choose a verification level

| Goal | Time and downloads | Command or entry point |
|---|---|---|
| Inspect the recorded result | About 2 minutes; no GPU | `uv run python -m eval.replay_published_v3` |
| Run repository tests | A few minutes | `uv run pytest -q` |
| Exercise both served models | Several minutes; about 4.5 GB first run | `./start.sh --check` |
| Keep the comparison API running | Same setup as above | `./start.sh` |
| Inspect in a browser | No local setup | [v3 evidence Colab](../../notebooks/v3_evidence_walkthrough.ipynb) |

Do not retrain for ordinary review. Retraining creates a new experiment and is
not verification of the published result.

## 1. Verify source, tests, and recorded arithmetic

Requirements: Git and a Python environment supported by the lockfile. From the
repository root:

```sh
uv sync --frozen --extra serve
uv run python data/fetch.py
uv run python data/restore_v1.py
uv run pytest -q
uv run python -m eval.replay_published_v3
```

`data/fetch.py` downloads the pinned Bitext CSV into the gitignored `data/raw/`
directory and verifies its digest. `data/restore_v1.py` reconstructs gitignored
historical fixtures and verifies their sealed hashes. Neither command retrains a
model or changes sealed v3 results.

The arithmetic replay checks the published counts, task-success rates, gain,
critical-failure counts, intent-macro gain, and paired interval against the
recorded evidence under `eval/results/v3/final01/`.

## 2. Run real base and tuned inference

The launcher supports Apple Silicon macOS and Linux x86_64 with glibc, including
WSL2. It needs Bash, curl, tar, and `shasum` or `sha256sum`. Allow 20 GB free disk
and preferably 16 GB RAM. A GPU is optional.

```sh
git clone https://github.com/Imsharad/ghl-support-slm.git
cd ghl-support-slm
./start.sh --check
```

The first run downloads about 3.3 GB of model weights; the Linux Ollama archive
adds about 1.2 GB. The launcher installs pinned tools in `.runtime/`, verifies
artifact hashes, starts localhost services, makes one real request to each model,
and stops. It does not need sudo, an API key, or a preinstalled Python or Ollama.

To keep the API running:

```sh
./start.sh
```

Wait for `READY`, then open <http://127.0.0.1:8013/docs>. Ctrl+C stops services
owned by the launcher. Alternate ports are supported:

```sh
./start.sh --check --port 8023 --ollama-port 11436
```

The public API binds to `127.0.0.1:8013`; its private Ollama binds to
`127.0.0.1:11435`. Logs are `.runtime/logs/api.log` and
`.runtime/logs/ollama.log`; the last successful smoke check is
`.runtime/last-check.json`. Native Windows and Intel Macs are not supported by
the launcher. Linux support is implemented but was not verified on a live Linux
host for this submission.

Do not expose this API publicly. It has no authentication, TLS, retrieval, or
account tools.

## 3. Manual serving path

Use Python 3.11.11 and Ollama 0.24.0. Start `ollama serve` separately, then run:

```sh
uv sync --frozen --extra serve
uv run python tools/fetch_artifacts.py \
  --manifest artifacts/v3/manifest.json \
  --target serve
uv run python -c 'from train.render import get_tokenizer; get_tokenizer(local_files_only=False)'
ollama create ghl-base -f serve/Modelfile.base
ollama create ghl-support-v3-c03-s120 -f serve/Modelfile.v3-candidate03-step120
SUPPORT_TUNED_TAG=ghl-support-v3-c03-s120 \
  SUPPORT_PROMPT_FILE=configs/prompt-v3.txt \
  uv run --extra serve uvicorn serve.api:create_app --factory \
  --host 127.0.0.1 --port 8013 --no-access-log
```

The exact prompt is [`configs/prompt-v3.txt`](../../configs/prompt-v3.txt), SHA-256
`6df9d82ec3d693df9934ab8a2c40d07c618574cf9188bd842d89986487cc9a79`.
The exact adapter is pinned in [`artifacts/v3/manifest.json`](../../artifacts/v3/manifest.json).
The base is Qwen2.5-1.5B-Instruct revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

## 4. Reproduce the demo or inspect performance

The released 2:47 walkthrough is
[demo.mp4](https://github.com/Imsharad/ghl-support-slm/releases/download/v3-submission.1/demo.mp4).
Its deterministic request plan, responses, captions, and recording provenance are
under [`eval/results/v3/demo-recording-001/`](../../eval/results/v3/demo-recording-001/).

Recorded warm HTTP measurements are under
[`eval/results/v3/paired-api-warm02/`](../../eval/results/v3/paired-api-warm02/).
They describe the tested local machine and should not be treated as portable
hardware claims.

## 5. Evidence map and boundaries

| Question | Canonical record |
|---|---|
| What was promised before the final evaluation? | [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md) |
| What ran and in what order? | [`PLAN.md`](PLAN.md) |
| Why was candidate03 retained? | [`SELECTION.md`](SELECTION.md) |
| What must a submission reviewer inspect? | [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) |
| What counts as a pass or critical failure? | [`eval/RUBRIC.md`](../../eval/RUBRIC.md) |
| What model, prompt, and files were served? | [`artifacts/v3/manifest.json`](../../artifacts/v3/manifest.json) |
| What was measured? | [`analysis.json`](../../eval/results/v3/final01/partial-mixed-analysis-001/analysis.json) |
| Why did the safety gate fail? | [`credential-review.json`](../../eval/results/v3/final01/partial-mixed-analysis-001/credential-review.json) |
| Why was candidate04 rejected? | [`review.json`](../../eval/results/v3/development/candidate04-mps/review.json) |

Treat `eval/results/v3/final01/` as immutable recorded evidence. Do not fabricate
the two omitted grades or the private blind key, pool interrupted CUDA results
with the complete MPS review, use validation loss as a safety claim, or compare
absolute pass rates across v1, v2, and v3.
