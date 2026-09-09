# AI reviewer guide

## Current truth

- The default branch represents the v3 submission state.
- `v3-candidate03-step120` is the final evaluated and served artifact.
- Recorded task success improved from 59/106 to 81/106 in a post-hoc mixed-judge comparison.
- The tuned model had two credential/verification violations; the fixed safety gate required zero.
- The preregistered all-human evaluation was not completed. Do not claim overall qualification.
- Candidate04 trained successfully on a free Colab T4, but every checkpoint failed development selection. It never replaced candidate03.

## Read first

1. `README.md`: 60-second history, verdict, and map of the repository.
2. `docs/v3/REVIEWER_RUNBOOK.md`: commands, startup, troubleshooting, and evidence map.
3. `docs/v3/SUBMISSION_CHECKLIST.md`: submission evidence and reviewer checklist.
4. `docs/v3/SELECTION.md`: candidate and checkpoint decisions.
5. `docs/v3/PLAN.md`: chronological execution record and reconstruction details.
6. `eval/RUBRIC.md`: pass and critical-failure definitions.

## Verify source and evidence

From the repository root:

```sh
uv sync --frozen --extra serve
uv run python data/fetch.py
uv run python data/restore_v1.py
uv run pytest -q
uv run python -m eval.replay_published_v3
```

The data commands reconstruct gitignored historical fixtures from pinned public
inputs. They do not retrain a model, rewrite the matching committed source
manifest, or modify sealed v3 evidence.

For a real local base/tuned inference check:

```sh
./start.sh --check
```

First run needs network access and about 4.5 GB of downloads. Supported launcher
hosts are Apple Silicon macOS and Linux x86_64 with glibc. It installs pinned tools
inside `.runtime/`, verifies artifact hashes, makes one real request to each model,
and stops.

## Evidence boundaries

- Treat `eval/results/v3/final01/` as immutable recorded evidence.
- Never fabricate the two omitted grades or the private blind key.
- Do not pool the interrupted candidate04 CUDA development outputs with the later complete MPS review.
- Do not use validation loss as proof of response quality or safety.
- Do not compare absolute pass rates across v1, v2, and v3; their sets and judging differ.
- Do not expose the localhost demo API to the internet. It has no authentication or TLS.
- Do not retrain unless explicitly asked. Reproduction is expensive and creates a new experiment, not verification of the published result.

## Fast file map

| Question | Evidence |
|---|---|
| What model and prompt ran? | `artifacts/v3/manifest.json`, `configs/prompt-v3.txt` |
| What data trained candidate03? | `data/v3/candidate03_manifest.json`, `data/assemble_v3.py` |
| What was measured? | `eval/results/v3/final01/partial-mixed-analysis-001/analysis.json` |
| Why did safety fail? | `eval/results/v3/final01/partial-mixed-analysis-001/credential-review.json` |
| Why was candidate04 rejected? | `eval/results/v3/development/candidate04-mps/review.json` |
| What performance was observed? | `eval/results/v3/paired-api-warm02/summary.json` |
| Can the published arithmetic replay? | `eval/replay_published_v3.py` |
| Where is the demo? | `eval/results/v3/demo-recording-001/demo.mp4` |
