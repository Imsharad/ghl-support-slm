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
| B3r | Grok-4.5 | `eval/challenge_v2_draft.jsonl` (rework 14) | B3v | 18:15 | `uv run python eval/check_challenge.py eval/challenge_v2_draft.jsonl --against eval/challenge.jsonl eval/dev.jsonl` (must exit 0) | in progress | — |
| B3v2 | Sol | `docs/dag/CHALLENGE_REVIEW_v2.html`, `eval/check_challenge.py`\*, `docs/dag/render_challenge_review.py`\* (\*only if a fix is needed) | B3r | 18:35 | checker exit 0 + 40 unchanged ids byte-identical to 2e08d79 draft | blocked on B3r | — |
| Gate1 seal | Fable, Sol, shark | `eval/challenge_v2.jsonl`, `eval/SEAL_v2.json` | B3v2, shark approval | ~18:45 | `uv run python eval/check_challenge.py --seal` (refuses if seal exists) | blocked on B3v2 | — |
| A1 | Opus | `tools/admissions.py`, `data/prepare.py` (`cap_train_rows`, assemble path), `tests/test_prepare.py`, `tests/test_admissions.py`, `data/v2/admissions.jsonl`, `data/v2/admission_review.jsonl`, `data/v2/leakage.json`, `data/v2/cap.json`, `docs/v2/DATA_V2.md` (append) | Gate1 seal | dry run 18:30, rows 19:45 | one-intent dry run, then `uv run python data/prepare.py --audit-only --strict` | in progress (restarted after outage) | — |
| A2 | Grok | admission-row review (path per A1 brief) | A1 | ~19:45 | lint rules from `docs/v2/PLAN_DECISIONS.md` sec 4 | blocked on A1 | — |
| D0 | Sonnet | `docs/dag/v2/STATUS.md` | — | 18:20 | manual read, under 80 lines | in progress (this report) | — |
| Re-audit | Opus | `data/v2/audit.json`, `data/v2/splits.json` (v2 rows folded in) | A2 | 20:15 | `uv run python data/prepare.py --audit-only --strict` | blocked on A2 | — |
| Train launch | shark, Opus | detached training job, launcher posts finish line | Re-audit | target 20:30, hard 21:30 | launcher script `--mention` on completion | blocked on Re-audit | — |
| Checkpoint/merge | Sol | checkpoint, merge, Q8 quant, Ollama tag | Train launch | ~01:30 Tue | manual smoke of served model | blocked on Train launch | — |
| Gate2 scoring | Grok, Fable | 54 v2 answers x2, judge, adjudication | Checkpoint/merge | ~03:30 Tue | judge protocol, frozen rubric | blocked on Checkpoint/merge | — |
| Results writeup | Opus | `docs/RESULTS.md`, `README.md` (both sets) | Gate2 scoring | ~08:30 Tue | manual read | blocked on Gate2 scoring | — |
| Loom | shark | recording | Results writeup | 14:00 Tue | manual review | blocked on Results writeup | — |
| Submission | shark | final commit, tag, submission | Loom | 20:00 Tue | `check_submission.py` | blocked on Loom | — |
