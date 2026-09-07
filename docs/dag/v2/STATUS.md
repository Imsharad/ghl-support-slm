# v2 node board

Thread root: `05b9e7942333e90470353b414345289c20836eb94901ecf7b497fb33f8e8a240`.
Fable 5.1 hand-edits this file after each worker's verified report; other workers do not edit it.

| id | worker | owned paths | deps | due IST | verify command | status | commit |
|---|---|---|---|---|---|---|---|
| H0 | Fable | `tools/hygiene_check.py`, `.gitignore` | — | 14:50 | `python3 tools/hygiene_check.py --tree` | done | `5d8f799` |
| E0 | Sonnet | `docs/v2/EVIDENCE.md` | H0 | 14:50 | manual read against source files | done | `f09cbc4` |
| B3 | Grok-4.5 | `eval/challenge_v2_draft.jsonl` (draft) | H0 | 15:30 | `uv run python eval/check_challenge.py eval/challenge_v2_draft.jsonl --against eval/challenge.jsonl eval/dev.jsonl` | done, superseded by B3r | `aa3aa51` |
| C0 | Sonnet | `notebooks/train_colab.ipynb`, `notebooks/README.md` | H0 | 16:00 | manual open in Colab | done | `7c32d0a` |
| E0v | Grok | `eval/admission_scan.py`, `docs/v2/EVIDENCE_VERIFY.md` | E0 | 15:15 | independent recompute vs EVIDENCE.md | done | `7ff840c` |
| G0 | Sonnet | `README.md` (secs 2, 7 only) | H0 | 15:15 | manual read | done | `3da5fd6` |
| B1 | Opus | `data/prepare.py`, `configs/cleaning.json`, `tests/test_prepare.py`, `data/v2/{audit,splits}.json`, `docs/v2/DATA_V2.md` | E0 | 17:00 | `uv run python data/prepare.py --audit-only --strict` | done | `c44970a` |
| P0 | Fable | `docs/plans/V2_PLAN.md`, `docs/v2/PLAN_DECISIONS.md`, `docs/v2/SEED_PROMPT.md` | E0 | 16:30 | manual read, shark approval | done | `53ede92` |
| B3v | Sol | `eval/check_challenge.py`, `eval/blind.py`, `eval/run.py`, `tests/test_eval.py`, `docs/dag/render_challenge_review.py`, `docs/dag/CHALLENGE_REVIEW_v2.html` | B3 | 16:15 | `uv run pytest -q`; `uv run python tools/hygiene_check.py --tree` | done, found 14 collisions | `2e08d79` |
| B1v | Grok | `docs/v2/DATA_V2_VERIFY.md` | B1 | 15:30 | independent regex recount vs `DATA_V2.md` | done, 2 mismatches corrected | `23be885` |
| E0f | Sonnet | `docs/v2/EVIDENCE.md`, `docs/RESULTS.md`, `docs/FAILURES.md`, `README.md` (fix) | E0 | 15:00 | manual read | done, inside 53ede92 | `53ede92` (Authored-by Sonnet) |
| B3r | Grok-4.5 | `eval/challenge_v2_draft.jsonl` (rework 14) | B3v | 18:15 | `uv run python eval/check_challenge.py eval/challenge_v2_draft.jsonl --against eval/challenge.jsonl eval/dev.jsonl` (must exit 0) | done | `b64f486` |
| B3v2 | Sol | `docs/dag/CHALLENGE_REVIEW_v2.html`, `eval/check_challenge.py`\*, `docs/dag/render_challenge_review.py`\* (\*only if a fix is needed) | B3r | 18:35 | checker exit 0 + 40 unchanged ids byte-identical to 2e08d79 draft | done | `680ed19` |
| Gate1 seal | Fable, Sol, shark | `eval/challenge_v2.jsonl`, `eval/SEAL_v2.json` | B3v2, shark approval | ~18:45 | `uv run python eval/check_challenge.py --seal` (refuses if seal exists) | done 18:12 IST (shark delegated 39e0b99e; Grok-4.5 author pass, Sonnet G1r independent, no changes) | `e9f691f` |
| A1 | Opus (runs 1-5, Flash), Fable (run 6, Grok) | `tools/admissions.py`, `data/prepare.py` (`cap_train_rows`, assemble path), `tests/test_prepare.py`, `tests/test_admissions.py`, `data/v2/admissions.jsonl`, `data/v2/admission_review.jsonl`, `data/v2/leakage.json`, `data/v2/cap.json`, `docs/v2/DATA_V2.md` (append) | Gate1 seal | rows ~23:50 | one-intent dry run, then `uv run python data/prepare.py --audit-only --strict` | runs 1-5 (Flash via `agy`, 18:44-19:09 IST) all killed silent, 1 row banked; decision 11: author switched to `grok-4.5-build` via `grok -p` (`--provider grok`); run 6 launched 23:22:58 IST, parallel 8, log `/tmp/gen_full6.log`; closer check as pre-registered | `f5ae72e` + working tree |
| A2 | Grok, by shell-out (`grok -p`, restricted prompt, driven by `tools/admission_review.py`) | `tools/admission_review.py`, `data/v2/admission_review_a2.jsonl`, `docs/v2/ADMISSION_REVIEW_A2.md` | A1 | ~00:20 Tue | eight checks from plan s4 per row; independent `closer_audit.py` rerun | starts on run 6 rows | — |
| D0 | Sonnet | `docs/dag/v2/STATUS.md` | — | 18:20 | manual read, under 80 lines | done | `b10c1da` |
| Re-audit | Fable (Opus at session limit) | `data/v2/audit.json`, `data/v2/splits.json`, `data/v2/leakage.json`, `data/v2/admissions.jsonl` | A2 | ~01:05 Tue | `uv run python data/prepare.py --placeholder-mode substitute --out data/v2 --admissions data/v2/admissions.jsonl` then `--audit-only --out data/v2 --strict` | waits on A2 | — |
| Train launch | Fable (Colab T4 notebook run `v2-t4`; Mac `v2-mps` insurance stopped at step 325, decision 14) | `train/runs/v2-t4` (checkpoints 100, 200, 250, 300, 400, 500), `notebooks/v2_colab_run.ipynb` | Re-audit | done 03:41 Tue | `tools/check_run.py train/runs/v2-t4 --max-memory-gb 12` PASS (VM and Mac) | done; 500 steps, 4,832 s, peak 2.94 GB, git sha 33bdbbd; two notebook cells errored (smoke cap, eval path) and are fixed at 77f6f1e; dev answers regenerated on the VM | `77f6f1e` |
| Checkpoint/merge | Fable (Sol did not answer) | dev judging by `grok -p` per checkpoint, selection, v1 archive, merge, Q8, Ollama tag `ghl-support` (v1 kept as `ghl-support-v1`) | Train launch | ~05:00 Tue | `tools/check_artifacts.py`; curl from CONTRACTS s6 | live 04:05 IST | — |
| Gate2 scoring | Fable (judge: Gemini Flash x2 via `~/.buzz/scripts/ghl-llm-judge.py`, results under `eval/results/v2/fresh`) | 54 v2 answers x2, judge, adjudication | Checkpoint/merge | ~06:00 Tue | judge protocol, frozen rubric; base answers on the fresh set done 00:30 IST (54/54, check pass) | blocked on Checkpoint/merge | — |
| Results writeup | Fable (Opus if back) | `docs/RESULTS.md`, `README.md` (both sets), `docs/FAILURES.md`, `docs/SELECTION.md` (append) | Gate2 scoring | ~09:00 Tue | manual read | blocked on Gate2 scoring | — |
| Loom | shark | recording | Results writeup | 14:00 Tue | manual review | blocked on Results writeup | — |
| Submission | shark | final commit, tag, submission | Loom | 20:00 Tue | `check_submission.py` | blocked on Loom | — |

Colab path (18:45 IST): `colab --auth adc` uses the existing gcloud ADC file, no OAuth code. Fallback if the CLI fails at launch: `notebooks/train_colab.ipynb` plus shark's Run-all, which needs the repo public (shark approved the flip 18:29 IST).

A1 closer check (pre-registered 18:52 IST, before the numbers exist): over accepted rows, normalise the final sentence (lowercase, strip punctuation) and count. Concentrated means any one closing sentence, or any closing 6-gram, in more than 10 percent of rows or spanning more than 5 intents, or any of the prompt's three step-3 closers above 60 percent of rows. If concentrated: no patching; assign the step-3 closer per scenario in the prompt and make the have-to-hand list name the facts that intent needs, then regenerate only the affected cells under the new prompt_sha. Not concentrated: proceed to A2 unchanged.
