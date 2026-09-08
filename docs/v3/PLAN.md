# v3 execution plan

Status: active under the owner's 2026-09-08 persistent assignment goal. The earlier HARD STOP 1–4 procedures and proposed experiment below are superseded. They remain as historical planning evidence, not current launch requirements.

## Current execution contract (2026-09-08)

The hiring brief governs the deliverables. The owner explicitly authorizes autonomous local implementation, design changes, data preparation, training, evaluation, local serving, README/demo preparation, and local commits. A subsequent 2026-09-08 instruction supersedes the original $0/free-compute restriction: RunPod GPU and storage usage may consume at most $10 total from existing account credit. Ask before exceeding this ceiling; do not add funds or change auto-pay. Paid judge/API services remain unauthorized. This is a disclosed deviation from the hiring brief's "do not spend money" instruction, not evidence of employer approval. Publication, pushes, merges to main, employer submission, and deletion of historical work remain excluded. Earlier $0 observations below are historical, not the current authority.

Workspace reconciliation: `/Users/sharad/Documents/ChatGPT/GHL-support-assistant` is an empty Git repository. Work continues in the existing isolated `v3` worktree named below. The source `v2` checkout retains its original dirty state. Historical artifacts and data missing from the worktree will be read through explicit source paths or reproducibly reconstructed, never silently assumed present.

Current sequence:

1. Verify inherited tests and evidence. Add explicit experiment prompts and immutable run-input fingerprints; repair resumable training evidence and smoke verification.
2. Audit the eligible corpus and actual paraphrase overlap. Build a compact, documented v3 data intervention that teaches useful support without invented company knowledge. Keep historical source targets and provenance. Report target rewriting, if used, as new supervision.
3. Establish a modest development set and a fresh final set covering all 27 intents. Freeze rubric, primary task-success metric, meaningful improvement threshold, safety criteria, judge protocol, and analysis before final inference. Historical challenges are development/diagnostic material only for this iteration. No final test can guide candidate selection.
4. Train a candidate on one verified RunPod CUDA GPU within the $10 GPU-plus-storage ceiling, saving adapters, full run inputs, curves, and recovery evidence. Check authentication, SSH access, existing resources, live price and a working cost guard before provisioning. Run and inspect the smoke before full training. Download and verify artifacts, then release task-owned rental resources; do not leave GPU billing active while waiting for human grading. Select using development results; preserve unsuccessful experiments. No unconditional second pass or per-update 60-item remote-judge loop is required.
5. Export and serve the exact selected model and its starting base under identical prompt/decoding conditions. Complete the untouched paired evaluation, quantify uncertainty and failures, and measure API performance.
6. Verify the README commands and prepare a local demo, Loom script, interview notes, and requirement-to-evidence checklist. The improvement objective stays unmet unless the evidence supports it.

The earlier GoHighLevel contact URLs are removed from the proposed model contract: the assignment describes a generic business. The new prompt is versioned separately so v1/v2 reproduction retains its original prompt.

Access observation: Colab session listing required Google OAuth reauthorization. The owner chose funded RunPod instead, so Colab reauthorization is no longer the required next step. The linked task "Rent a GPU for training" was read; it reports no provisioned GPU and its old 500-step/A100/Gemini proposal is not the current experiment. On this machine the RunPod CLI, conventional configuration file, and RUNPOD_API_KEY environment variable were absent at the initial check. Funding alone does not establish CLI authentication. No paid resource has been provisioned by this task as of this amendment.

### Verified execution progress, 2026-09-08

- Owner asked about RunPod as an alternative. The linked discussion was read and public pricing checked. No paid resource was created. A proposed $5 total usage exception awaits explicit authorization; the active $0/free-training contract is unchanged. The obsolete multi-pass/Gemini budget in the linked discussion is not a current requirement.
- The v1 and v2 ignored processed inputs were copied from the original checkout without overwriting or altering originals. Initial inherited test failures were missing-file failures; after restoring those inputs, the inherited and first regression suite passed (81 passed, one skipped).
- `configs/prompt-v3.txt` supplies a generic business contract separately from the historical prompt. Training, evaluation, and inference accept explicit prompts. New checkpoints carry the tokenizer and prompt alongside the adapter.
- Run fingerprints cover source content, prompt, encoded training order, validation IDs, native chat template, effective step count, runtime versions/device, and training code. Resume rejects changed inputs. Python/NumPy/CPU/device RNG states are saved/restored; validation preserves RNG and prior training mode. The smoke proof preserves the original checkpoint trajectory in a separate resume directory. Actual GPU resume equivalence is still unverified.
- Validation now samples round-robin across intents instead of taking a potentially single-intent sorted prefix. Validation loss is token-weighted over predicted assistant labels. Historical run numbers are not reinterpreted as measurements made by this revised trainer.
- `data/audit_overlap_v3.py` checked query overlap across all intents with pinned MiniLM embeddings, normalized exact matches, groups, and six-word sequences. Despite zero shared IDs/groups/exact queries, the original test-to-train median maximum cosine was 0.9036 and 2,552/3,085 exceeded or equaled 0.86. A threshold is a screening heuristic, not proof of semantic independence.
- `data/prepare_source_v3.py` reproducibly removes complete training groups near either historical holdout and complete validation groups near historical test. It also removes all 206 old synthetic admission rows. The output has 3,071 Bitext training candidates, 489 validation rows, and 3,085 diagnostic test rows; all 27 intents survive. Post-filter maximum cosines are below 0.86 in every split comparison, with zero normalized exact/group/ID overlaps and zero shared six-grams. Hashes and filtering decisions are in `data/v3/source-candidates/manifest.json`; generated JSONL is ignored and rebuildable.
- This pool is explicitly **not ready for training**. Reviewing one retained original response per intent found invented payment methods, guarantees, claimed account access, corrupted placeholder substitutions, and fabricated interface details. Targets require curated corrections; the historical original targets remain unchanged. The historical test remains diagnostic, never the fresh final evaluation.
- New CLI evaluation runs write immutable manifests containing query-file hash, exact prompt, decoding, runner code, and model identity (resolved Ollama digest or local artifact hashes). Resume rejects mismatched conditions or unmanifested legacy output. Generation errors return a failing exit status.
- `serve/api.py` is a localhost-only FastAPI wrapper using the evaluation generation path. It fixes the prompt, rejects reserved chat tokens/oversized requests/prompt overrides, rejects concurrent generation with 429, and detects model-tag changes. A missing tuned model returns 503 rather than substituting base. Authentication and public exposure are not implemented or authorized.
- Live smoke: `127.0.0.1:8013/health` returned base digest `fa4e1b0f10cd2057e4f4ba8adafb8cbb6debcef94f123768928fbedcec86bd08` and prompt-content SHA-256 `6df9d82ec3d693df9934ab8a2c40d07c618574cf9188bd842d89986487cc9a79`. The password-reset development query returned 245 prompt tokens and 256 generated tokens in 12,775 ms request time, with `truncated=true`. This is one base-only correctness smoke, not a benchmark or paired improvement evidence. Its answer contained an unhelpful fallback to an email-based reset tool after email access was lost.

Commands verified for the new foundation:

```sh
uv run python data/audit_overlap_v3.py --source-dir data/processed/v2 \
  --output data/v3/source-overlap.json
# For a clean machine without cached MiniLM weights, add --allow-download.
uv run python data/prepare_source_v3.py --source-dir data/processed/v2 \
  --source-audit data/v3/source-overlap.json --output-dir data/v3/source-candidates
uv run --extra serve pytest -q
uv run --extra serve uvicorn serve.api:create_app --factory --host 127.0.0.1 \
  --port 8013 --no-access-log
curl --fail --silent http://127.0.0.1:8013/health
curl --fail --silent -H 'Content-Type: application/json' \
  -d '{"model":"base","query":"I forgot my password and cannot sign in. What should I do?"}' \
  http://127.0.0.1:8013/support
```

Audit/build commands intentionally refuse existing output paths; reuse verified existing outputs or choose a new directory for a second reproduction. Full training, new target approval, a fresh frozen final set, paired results, tuned API, credible throughput measurements, release README and demo remain unfinished.

### Candidate supervision and development baseline

The foundation above was committed locally as `cd9e6e8` (V3-R1), with 96 passing tests and one skipped test. Nothing was pushed or published.

The next data intervention is explicit target replacement, not more training on unsupported original business claims. `data/select_targets_v3.py` selects eight distinct groups per intent for training and two per intent for validation using a fixed SHA-256 ranking and seed 42. A conservative placeholder-artifact filter is recorded, but does not claim to catch all historical substitution artifacts. The original instruction and response remain available in each curation record. `data/v3/targets/` contains 216 individually authored training responses and 54 individually authored validation references, labelled as assistant-authored, not independently reviewed. Responses were composed against each selected query, including its ambiguity and concrete references, rather than copying one response per intent. The author self-reviewed alignment, claims, safety, and next steps; automated lint is not a substitute for an independent quality review.

The first assembled data revision (`data/processed/v3-candidate01`, 216/54 rows) was not trained. A second revision (`data/processed/v3-candidate02`) adds 27 fictional supplied-context training scenarios, one per intent. These teach use of quoted policies, calculations, concrete status distinctions, and verification constraints instead of unconditional inability disclaimers. Their nearest-query screening against all 5,838 historical held-out queries passed at maximum cosine 0.7430 with zero shared six-grams. The second revision has 243 training rows (nine per intent) and 54 validation rows. Its saved manifest is `data/v3/candidate02_manifest.json`; generated corpus files remain ignored. All 297 targets (243 training plus 54 validation) passed the credential-request lint, but that lint is not a full factuality or safety assessment. Maximum rendered length is 347 tokens, so the existing 512-token cap is sufficient without truncation.

This is a small-data first experiment, not a reduction of the final quality objective. A balanced subset makes individual target review feasible within the part-time assignment and avoids adding thousands of known-incorrect targets. It also risks narrow language coverage, template-like outputs, and overfitting; only development and fresh evaluation can establish whether it works. Same-author validation references measure fit to this supervision style, not independent support quality. Expand or revise using development evidence if needed, never using final-test answers.

`configs/train-v3-t4.yaml` retains the exact pinned Qwen base and known rank-16/all-linear NF4 LoRA recipe, with a smaller 5e-5 learning rate, 0.05 dropout, 0.01 weight decay, six warmup steps, effective batch eight (micro-batch two × accumulation four), and 120 steps (approximately four passes). These are conservative starting choices for the much smaller curated dataset, not tuned optima. Four checkpoints at steps 30/60/90/120 support development-based selection. Validation covers all 54 rows; initial validation loss is also recorded. The 20-step smoke uses the same micro-batch/accumulation shape and separately verifies resume. Actual Qwen GPU memory, timing, convergence, and resume parity remain unmeasured. The real optimizer-loop CPU integration test uses a tiny 72-parameter dropout fixture and reproduces resumed losses and saved weights exactly; it is not a Qwen or GPU smoke.

The exact base was run on all 54 curated validation queries through Ollama with the new prompt. Files: `eval/results/v3/development/base-curated-val.jsonl` and its immutable manifest. All 54 requests succeeded; one answer truncated. Median request latency was 1,226 ms and median generation length 69 tokens in this particular sequential development run. These are descriptive development measurements, not a hardware-controlled serving benchmark. Unblinded inspection found concrete failure modes:

- `bitext-001335`: an item-swap request answered as an account-access problem.
- `bitext-002826`: claimed it could access and change the account after receiving an account number.
- `bitext-004940`: asserted PayPal acceptance without business payment information.
- `bitext-008038`: invented `1-800-123-4567` and a support URL.
- `bitext-009125` and `bitext-009339`: refused benign requests for human assistance without a route forward.
- `bitext-010567`: invented a registration interface option specifically for a fiancé.
- `bitext-017367`: offered to inspect newsletter status and resend it despite no account tools.
- `bitext-019340`: answered a purchase request as an account-access problem and invented an email destination.
- `bitext-025015`: suggested editing an order's status to a customer who only asked to view it.

No numeric human task-success score has been assigned. `eval/v3/protocol.json` is a draft for a 108-case, four-per-intent fresh comparison with blinded owner grading, a +5 percentage-point primary threshold, positive lower 95% intent-cluster bootstrap bound, no increased critical-failure count, and zero observed credential/verification violations. It must be sealed with actual fresh items and candidate hashes before final inference. Historical challenge sets remain development-only.

A prompt-only development ablation also ran the same base and 54 inputs with `configs/prompt-v3-compact.txt`, saved separately as `base-compact-val.jsonl` with its own manifest. All 54 requests succeeded and two truncated; median latency was 1,174 ms and median generation length 70 tokens. Unblinded inspection showed mixed changes: item-swap and password-reset guidance improved, but refund timing became a fabricated fixed 14 business days, and several answers newly claimed account/policy inspection. No numeric quality winner is claimed. The original prompt remains the provisional training prompt; both development baselines are retained, and this prompt-only comparison must not be reported as a fine-tuning improvement.

`tools/build_training_bundle.py` creates a deterministic training-only ZIP from a clean, committed worktree using an explicit whitelist and corpus hashes. It excludes final test data and credentials and refuses publication-enabled configs. `tools/run_training_bundle.py` checks every bundled hash, requires a single CUDA GPU, prefetches the pinned model, and requires a passing smoke from the exact same bundle before full training. It does not provision resources, fund an account, publish weights, or imply paid-compute approval. The actual launch bundle has not yet been built because the experiment edits are still being verified. Source commit and bundle identity are recorded in run metadata even when an extracted bundle has no Git directory.

Additional reproduction commands (run only into absent output directories):

```sh
uv run python data/select_targets_v3.py --source-dir data/v3/source-candidates \
  --output-dir data/v3/curation-queue
uv run python data/check_augmentation_v3.py --input data/v3/augmentation_context.json \
  --against data/processed/v2/val.jsonl data/processed/v2/test.jsonl \
  --output data/v3/augmentation_context_audit_v2.json
uv run python data/assemble_v3.py --source-dir data/v3/source-candidates \
  --selection data/v3/curation-queue/selection.json --targets-dir data/v3/targets \
  --prompt-file configs/prompt-v3.txt --output-dir data/processed/v3-candidate03 \
  --max-length 512 --augmentation data/v3/augmentation_context.json \
  --augmentation-audit data/v3/augmentation_context_audit_v2.json \
  --review-note 'Reproduction of the tracked assistant-authored, self-reviewed targets; no independent review claimed.'
uv run --extra serve python -m eval.run --model base --backend ollama --split dev \
  --input data/processed/v3-candidate03/val.jsonl --prompt-file configs/prompt-v3.txt \
  --tag ghl-base --output eval/results/v3/development/base-curated-val.jsonl --check-complete
```

Repository hygiene rejected a reserved fictional email literal in the context augmentation during the first R2 commit attempt. The check was not bypassed. That one scenario was changed to a named official contact form, then re-screened and reassembled as `data/processed/v3-candidate03`; the launch config now points to candidate03. The 243/54 row counts and selected Bitext targets are unchanged. Candidate01 and candidate02 are untrained data revisions, not training attempts. Their files and manifests remain historical evidence; the original email-containing draft is retained only under ignored `.scratch/v3-drafts/`. The current reproducible augmentation audit is `augmentation_context_audit_v2.json`, and the current corpus manifest is `candidate03_manifest.json`.

### R3 — fresh evaluation preparation, paired scoring and live API measurement

The training bundle was built from local commit `321ec361ecc3221cfb0760ae80ad1063cb60ed39` after R2 verification. `.scratch/training-bundles/v3-candidate03.zip` is 183,123 bytes with SHA-256 `5df675dd6159e45f36ad13bcd8ce82716dc184d7114a9983e1e9aa3ffa4692fb`. Extracting it and running its `--verify-only` command verified all 18 files. Subsequent R3 evaluation, serving benchmark and merge changes do not modify the bundled training implementation. No remote training has run. The last Colab session-list attempt required Google reauthorization. The local Kaggle CLI is absent, the conventional credential/token files are absent, and the three standard Kaggle credential environment variables are absent; this is not a claim that no browser account exists. A RunPod alternative was researched at the owner's request, but the proposed paid-compute exception and budget remain unapproved. The active goal still requires $0 spending.

`eval/v3/final_draft_part01.json` through `part04.json` contain 108 assistant-authored cases, four per intent: missing information, supplied context, failed prior attempt/constraint, and multi-request/boundary. Each contains acceptable actions and critical-failure criteria, not a model answer. The author also prepared training targets; the set is not independently human-authored and does not represent the employer's internal distribution.

`eval/prepare_v3.py` validates complete unique intent/scenario coverage and mandatory checklists, then screens queries against actual candidate03 train/validation and both historical challenge sets (405 comparator queries). It requires zero normalized exact/ID/six-gram matches and maximum pinned-MiniLM cosine below 0.86. It also reports within-final high-similarity pairs descriptively. `screening01` rejected one six-word phrase; the original cases and failed audit remain intact. `final_revisions01.json` records the pre-inference wording revision and reason. `screening02` passes all 108 queries, maximum cosine 0.724695, zero shared six-grams, and no within-final pair at or above 0.86. The compiled cases hash is `0d926b77b5820256e0b640c335bbade68adace5627413df8616601c0061c8340`. This is **screened, not sealed**: candidate selection, artifact lineage and final model/protocol seal remain outstanding. No final model answers or primary human grades exist.

`eval/paired_v3.py` prepares a shuffled A/B CSV, holds the reproducible mapping only under ignored `.scratch`, binds all immutable item/answer text and raw-output manifests, and rejects incomplete or contradictory scores. It never supplies human judgments. Unrecoverable generation failures stay in the denominator as task failures. The scorer requires the v3 model/data/protocol seal, exact shared inference conditions and complete owner-scored pairs. `eval/v3_metrics.py` implements the protocol's 27-intent paired cluster bootstrap, secondary query bootstrap, +5-point threshold, safety gates, per-intent/scenario summaries, both-failure cases and tuned-regression IDs. Unit fixtures are synthetic tool tests, not evidence of model improvement. The final-seal creation and generation handoff still need to be connected to the actual selected trained artifacts.

Reproduce screening into a **new** output directory:

```bash
uv run --extra serve python eval/prepare_v3.py \
  --drafts eval/v3/final_draft_part01.json eval/v3/final_draft_part02.json \
    eval/v3/final_draft_part03.json eval/v3/final_draft_part04.json \
  --revisions eval/v3/final_revisions01.json --output-dir .scratch/final-screen-reproduction
```

`serve/bench_api.py` measures the actual HTTP `/support` route, requires configured model identities and a stable prompt, saves every warmup/measurement/error, and refuses to overwrite results. It reports successful-request p50/p95 latency separately from failures and uses the entire measured wall interval for throughput. It does not measure streaming TTFT, cold starts or concurrent saturation. The live base-only run in `eval/results/v3/base-api-warm01/` used three warmups then all 54 development queries in file order, concurrency one. On this Apple M1 Pro (10 logical CPUs, 16 GiB RAM, macOS 26.5), all 54 succeeded, one truncated, p50 client latency was 1,170.29 ms, p95 3,582.38 ms, serial throughput 0.6645 successful requests/s and 59.7447 generated tokens/s over 81.2625 seconds. Exact model/prompt identities are in metadata and responses. Background desktop activity and initial cache state were uncontrolled. No tuned v3 benchmark or performance claim exists. The unchanged raw measurement files were moved from the initial `serve/results/` location into the repository's established model-output evidence directory.

```bash
uv run --extra serve python serve/bench_api.py --models base --requests 54 --warmup 3 \
  --hardware-note 'Record actual server placement and hardware here; do not infer it from the client.' \
  --output-dir .scratch/base-api-benchmark-reproduction
```

Handoff inspection found that `tools/merge.py` always copied the historical prompt. It now selects the adapter's recorded `prompt.txt`, rejects a conflicting override, and requires an explicit actual training prompt for older adapters lacking one. A merge manifest binds adapter hashes, pinned base revision, exact prompt, output files and merge implementation. Tests cover prompt/identity handling; no v3 merge has occurred because no v3 adapter exists yet. `tools/convert.sh` now refuses to overwrite an existing GGUF or use a converter checkout with tracked modifications.

R3 verification: `uv run --extra serve --with peft==0.20.0 pytest -q -rs` completed with **126 passed, zero skipped**, in 41.86 seconds. The two warnings concern deprecated FastAPI/Starlette HTTP test-client interfaces, not failed assertions. This includes a real pinned-Qwen CPU zero-effect-adapter comparison on development queries; it is inference parity, not training or improvement evidence. The plain serve-only environment skips that PEFT-dependent test, so the explicit package overlay is needed on this Mac (the full CUDA `train` extra includes bitsandbytes and is not a macOS installation route). Shell syntax validation and staged secret/PII hygiene checks passed. The source v2 worktree's dirty-file list remains unchanged.

The locally served base's Modelfile resolves to GGUF blob `eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5`. Hashing the actual 1.6 GB blob produced that same SHA-256, matching the base entry in the historical artifact manifest, which records the pinned Qwen revision and converter commit. This verifies reuse of the recorded base artifact; no fresh base conversion was performed in R3. The new prompt is supplied explicitly at request time and is separately hashed in evaluation/API responses.

### R4 — artifact-bound final evaluation and funded RunPod preparation

`tools/convert_verified.py` checks the merged-model lineage and input hashes before conversion and records Q8 GGUF hash, pinned converter revision, environment and selected-adapter lineage. `eval/final_v3.py seal` requires a completed CUDA candidate, a passing same-bundle CUDA/resume smoke, development selection note, valid overlap screen, matching export lineage, and the actual local base/tuned Ollama identities. It freezes cases, rubric, scoring code, inference code, exact prompt, templates and parameters before final inference. `generate` checks identities around each response, preserves errors, binds every result to the seal, and rejects incompatible resumes. The blinded scoring CLI requires the same seal binding. No real v3 export, seal, final inference or human grading has run.

Verification before the compute amendment: `uv run --extra serve --with peft==0.20.0 pytest -q -rs` passed **132 tests, zero skipped**, with two deprecation warnings in 54.30 seconds. New final-launch tests use explicitly synthetic model outputs to exercise freeze/generate/resume and tamper rejection, not to measure model quality.

`configs/train-v3-runpod.yaml` preserves candidate03's 120 updates, length 512, learning rate 5e-5, rank 16 and 20-step resume smoke; only run names differ from the T4 configuration. Neither configuration enforces provider billing. The owner authorized $10 total RunPod GPU/storage usage and no automatic top-up. The separate linked task's 500-step, eight-hour A100 and paid Gemini proposal is not adopted.

After adding the RunPod configuration, a structural YAML comparison verified that only the two run names differ. The full suite again passed **132 tests, zero skipped**, with two deprecation warnings in 51.72 seconds. Staged hygiene passed for all seven changed files; the original v2 checkout's unrelated dirty-file list was unchanged.

Installed official `runpodctl` **2.12.0-51ca7f0**, Darwin ARM64 binary SHA-256 `ea5d936c0d9df23f7b2ff667480cb5a8344ac29b7c769751182c6180f4277408`, verified against the official GitHub release asset. Live `pod create --help` confirms this version has no `--stop-after` or `--terminate-after`; stale skill examples must not be used as a cost guarantee. Establish an actual deadline/cleanup mechanism and check live prices before launch. `runpodctl user` currently returns `no_credentials`; the owner was asked to complete `runpodctl doctor` privately for API-key and SSH setup. No RunPod resource or charge has been created by this task.

## Historical proposed plan (superseded)

## Starting evidence

- Execution seed: `docs/v3/SEED_PROMPT.md`, SHA-256 `12548db754fa66889e70e6b4697eb2968fedd13a069be54538548a93a4ce5652`.
- Source branch: `refs/heads/v2` at `f9262cc833ed579e65dbf6d87bae70d3c94126de`.
- v3 branch: `refs/heads/v3`, created directly from that source commit.
- Isolated worktree: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1-v3`.
- Source checkout: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`; it remains on `v2` and was not switched, reset, stashed, or staged.
- README start hash: `570835a9a44b037c40e7cfa3030005fc7c13b03c5afc7fdb2b11aceeb9edd8c2`.
- Existing release refs: `refs/tags/v2` is `caf0fa42dea3e84332c2b0aeb986dda6783803a3`; `refs/tags/v1` is absent at the start. No tag was created or moved.
- Required ignored analysis source: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1/docs/analysis/why-we-failed.html`, SHA-256 `f7a881ba672294f8c57dc5a029c5ca566939b9f62cfcdb8ad322dee4715adce5`. It was read in place and not copied into v3.

The protected source checkout had these unrelated changes at branch creation:

```text
 M docs/dag/DAG.html
 M docs/dag/DAG.json
 M docs/dag/build_dag.py
?? .context/
?? artifacts/v1/adapter/
?? artifacts/v1/merged/
?? candidate_test.py
?? docs/v3/
?? test_candidates.py
?? train/runs/v2-mps/
?? train/runs/v2-t4/
```

Only the required seed was carried into the isolated worktree. The other owner files remain solely in the source checkout.

## Phase state and approval gates

| Phase | State | Gate |
|---|---|---|
| 0. Inspect and establish branch | complete | `V3-R0` commit `19163e2fbdb90c5e1afbf051aa909a0512983480` records the start |
| 1. Prepare pre-registration | complete, unapproved | HARD STOP 1: owner approves exact hashes of `PLAN.md` and `PRE_REGISTRATION.md` |
| 2. Measurement and calibration | not started | requires HARD STOP 1 approval |
| 3. Draft/review/seal evaluation | not started | HARD STOP 2 approves exact draft hash |
| 4. Card-conditioned data | not started | requires the primary seal |
| 5. Training controls | not started | requires approved/frozen data |
| 6. Free-T4 run | not started | HARD STOP 3 approves compute launch |
| 7. Export and serve | not started | requires a guard-safe candidate |
| 8. Frozen paired evaluation | not started | requires served Q8 pair |
| 9. Results and README proposal | not started | HARD STOP 4 approves exact README patch |

README, `main`, serving files, evaluation items, training rows, model artifacts, and registered Ollama tags are unchanged.

## Phase 1 feasibility findings

- The exact proposed card is 230 content tokens and 235 tokens as a rendered system turn with the pinned Qwen tokenizer. Its one-terminal-LF SHA-256 is `f197fe99f25b3220e7850479d5c3a42382420efc2cb510cca07e78d25ed10479`.
- Full rendered v2-train examples at 512 retain 20,254/21,132 rows overall but only 159/791 `check_refund_policy` rows. At the proposed 768 limit, all 21,132 rows and every intent survive. This passes the length gate but not the future MPS/T4 memory and timing gates.
- The help destination returned HTTP 200 without changing URL. The exact contact destination redirected to the GoHighLevel homepage. The owner must approve that redirecting destination or provide a replacement before the card is frozen.
- The current v2 challenge passes its checker against v1 and dev. A read-only reconstruction of the original v2 draft found 14/54 shared-six-gram rejections (25.9%); this supports the six-attempt v3 replacement ceiling. No v3 prose was drafted.
- Direct single-turn Gemini REST calls are the proposed isolation mechanism. The existing `grok` CLI is excluded because its inspection surface includes global instructions, skills, permissions, and MCP configuration. A read-only provider-model listing confirmed `gemini-3.8-flash` and `gemini-3.7-flash` in the configured project. No generation call was made.
- Local disk has 201 GiB free. Prior v2 evidence records 4,832 seconds and 2.94 GB for 500 T4 steps at length 512. The proposed ceiling is one free-T4 session of at most eight hours, 12 GB peak allocated GPU memory, 15 GB free VM storage at launch, and 10 GB verified transfer. This is not compute approval.
- No paid model use is authorized. The hard call ceiling is 30 million input tokens and 10 million output/thinking tokens; current provider list pricing makes that a $60 maximum only if the owner separately authorizes paid usage. The default approval request is free-tier-only and fail-closed.

## Read-only commands already run

The following commands inspected evidence or performed in-memory/read-only checks. They did not author evaluation prose, generate training rows, run inference, train, alter serving, or allocate compute.

```sh
git status --short
git branch --show-current
git log --oneline -20
git rev-parse v2
git rev-parse refs/tags/v1 refs/tags/v2
shasum -a 256 README.md docs/v3/SEED_PROMPT.md data/intents.json \
  data/processed/v2/train.jsonl data/processed/v2/val.jsonl \
  data/processed/v2/test.jsonl data/v2/splits.json data/v2/audit.json
uv run python eval/check_challenge.py eval/challenge_v2.jsonl \
  --against eval/challenge.jsonl eval/dev.jsonl
```

The tokenizer feasibility check loaded the locally cached pinned tokenizer, rendered each `data/processed/v2/train.jsonl` conversation through its native chat template, then encoded that rendered text with `add_special_tokens=False`. Destination checks used redirect-aware HTTP requests. Provider discovery used only the direct Gemini REST model-list endpoint; it did not call `generateContent`.

## Planned files

Nothing in this section exists because it is listed here. The phase table remains authoritative.

- Phase 2: `eval/factual_lint.py`, `tests/test_factual_lint.py`, `eval/results/v3/calibration/`, and pre-training calibration sections in `docs/v3/RESULTS.md`.
- Phase 3: `eval/challenge_v3_draft.jsonl`, `eval/challenge_v3.jsonl`, `eval/SEAL_v3.json`, `eval/regression_v3.jsonl`, `eval/smoke_v3.jsonl`, `eval/window_probe_v3.jsonl`, `eval/safety_guard_v3.jsonl`, and `eval/reference_probe_v3.jsonl`.
- Phase 4: reviewed/rejected candidate, audit, leakage, admissions, corpus, split, and encoded artifacts under `data/v3/` and `data/processed/v3/`; the exact filenames become CLI outputs rather than hidden defaults.
- Phase 5: `configs/train-v3-t4.yaml`, `configs/train-v3-pass2-t4.yaml`, deterministic sampler evidence, pass-2 initialization evidence, and required smoke evidence.
- Later approved phases: immutable run evidence under `train/runs/v3-*`, model artifacts under `artifacts/v3/`, paired outputs under `eval/results/v3/`, and the executed v3 notebook copy. No README patch is created before HARD STOP 4.

## Exact planned command contracts

These commands are proposals. Options marked by Phase 2–5 work do not exist yet and must be implemented, tested, and shown in `--help` before use.

Measurement and calibration after HARD STOP 1:

```sh
python3 /Users/sharad/.codex/skills/grok-correction-loop/scripts/ledger.py init \
  --repo /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1-v3
python3 /Users/sharad/.codex/skills/grok-correction-loop/scripts/ledger.py query \
  --repo /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1-v3 \
  --milestone V3-R2
uv run pytest -q tests/test_eval.py tests/test_factual_lint.py
uv run python eval/check_challenge.py --help
uv run python eval/factual_lint.py --help
uv run python eval/score.py --help
uv run python eval/factual_lint.py calibrate \
  --profile v3 \
  --raw-answer eval/results/base-challenge-raw.jsonl \
  --raw-answer eval/results/tuned-challenge-raw.jsonl \
  --raw-answer eval/results/v2/fresh/base-challenge-raw.jsonl \
  --raw-answer eval/results/v2/fresh/tuned-challenge-raw.jsonl \
  --label-source eval/results/blind-sheet-scored.csv \
  --label-source eval/results/failures.jsonl \
  --label-source eval/results/v2/fresh/blind-sheet-scored.csv \
  --label-source eval/results/v2/fresh/failures.jsonl \
  --output-dir eval/results/v3/calibration \
  --seed 42 --min-negative-sample 30 --strict
```

Primary checker after its v3 options exist, followed by an owner review and HARD STOP 2:

```sh
uv run python eval/check_challenge.py eval/challenge_v3_draft.jsonl \
  --profile v3 \
  --against eval/challenge.jsonl eval/challenge_v2.jsonl
```

Frozen development baselines, before any seed authoring:

```sh
uv run python eval/run.py --profile v3 --mode development \
  --model ghl-base-v3 --backend ollama \
  --sets eval/smoke_v3.jsonl eval/safety_guard_v3.jsonl eval/reference_probe_v3.jsonl \
  --result-dir eval/results/v3/baseline/q8 --seed 42 --strict
uv run python eval/run.py --profile v3 --mode development \
  --model Qwen/Qwen2.5-1.5B-Instruct --backend hf \
  --sets eval/smoke_v3.jsonl eval/safety_guard_v3.jsonl eval/reference_probe_v3.jsonl \
  --result-dir eval/results/v3/baseline/hf --seed 42 --strict
```

Corpus-only preparation and frozen holdouts:

```sh
uv run python data/prepare.py --profile v3 --placeholder-mode substitute \
  --out data/v3 --source-splits data/v2/splits.json --max-length 768 --corpus-only
```

Background target review is a separate operation, not an implied side effect of preparation:

```sh
uv run python tools/admission_review.py background \
  --profile v3 --input data/v3/corpus_candidates.jsonl \
  --output data/v3/background_review.jsonl \
  --card configs/prompt.txt --max-candidates 12000 \
  --max-input-tokens 8000000 --max-output-tokens 2000000 --strict
```

Both-field leakage is also a separate operation. Every comparison file must exist or the command fails:

```sh
uv run python tools/admissions.py leakage data/v3/admissions_reviewed.jsonl \
  --profile v3 --fields query response \
  --against eval/challenge.jsonl eval/challenge_v2.jsonl eval/challenge_v3.jsonl \
    eval/dev.jsonl eval/smoke_v3.jsonl eval/safety_guard_v3.jsonl \
    eval/reference_probe_v3.jsonl eval/window_probe_v3.jsonl \
    data/processed/v3/val.jsonl data/processed/v3/test.jsonl \
  --max-cosine 0.80 --ngram 6 \
  --output data/v3/leakage.json --strict
```

Final assembly and explicit quota audit:

```sh
uv run python tools/admissions.py lint data/v3/admissions_raw.jsonl --profile v3
uv run python data/prepare.py --profile v3 --placeholder-mode substitute \
  --out data/v3 --source-splits data/v2/splits.json --max-length 768 \
  --target-review data/v3/background_review.jsonl \
  --admissions data/v3/admissions.jsonl --cap-train 8000 --require-frozen-holdouts
uv run python data/prepare.py --profile v3 --audit-only --out data/v3 --strict
uv run python train/render.py
uv run pytest -q tests/test_prepare.py tests/test_admissions.py tests/test_prompt.py
```

Deterministic sampler and pass-2 initialization checks after their Phase 5 options exist:

```sh
uv run python train/train.py --config configs/train-v3-t4.yaml \
  --sampler-dry-run --draws 8000 --seed 42 --output train/runs/v3-sampler-dry-run.json
uv run python train/train.py --config configs/train-v3-pass2-t4.yaml \
  --init-adapter train/runs/v3-pass1-init-test/adapter \
  --max-steps 1 --smoke --device mps --run-name v3-pass2-init-mps --no-push
```

MPS correctness smoke after data and training controls freeze:

```sh
uv run pytest -q
uv run python train/train.py --config configs/train-v3-t4.yaml \
  --smoke --device mps --data-dir data/processed/v3 \
  --run-name v3-smoke-mps --no-push
uv run python tools/check_run.py train/runs/v3-smoke-mps \
  --device mps --max-memory-gb 12
```

The exact Colab CLI invocation is intentionally not proposed yet. Phase 6 must first read `docs/v2/COLAB_CLI_HISTORY.md`, verify installed `colab --help` and relevant subcommand help, bind an immutable code commit and approved hashes, and then present the real launch/download commands at HARD STOP 3.

## HARD STOP 1 decisions required

Approval must name the exact hashes of this plan and `docs/v3/PRE_REGISTRATION.md` and include an actual timestamp/reference. It must also resolve these items:

1. Approve the redirecting `https://www.gohighlevel.com/contact-us` destination as intentional, or supply a verified replacement and require a new card hash/length preflight.
2. Acknowledge that `refs/tags/v1` was absent at start and authorize preserving that absence rather than inventing a tag.
3. Confirm the default zero-paid-spend policy, or state a nonzero paid API ceiling explicitly. Free-T4 compute remains separately gated at HARD STOP 3.

Until that approval is recorded, Phase 2 does not begin and `V3-R1` is not committed.
