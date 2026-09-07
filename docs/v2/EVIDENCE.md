# v2 Evidence Pack

Written 2026-09-07 14:12 IST by Sonnet (task V2-E0). Numbers and citations only, no argument.

## 1. v1 verdict

`eval/results/summary.jsonl`, verbatim:

```json
{"n": 54, "base_pass_rate": 0.2962962962962963, "tuned_pass_rate": 0.12962962962962962, "diff_points": -16.666666666666664, "ci95": [-33.33333333333333, 0.0], "base_critical": 2, "tuned_critical": 8, "win": 18, "tie": 7, "loss": 29, "verdict": "negative", "n_boot": 2000, "seed": 42}
```

Pass 16/54 = 29.6% base vs 7/54 = 13.0% tuned. Critical 2 base vs 8 tuned. Win/tie/loss (tuned vs base) 18/7/29.

Scoring provenance (`docs/RESULTS.md` line 20-24): not human-scored. Gemini 3.8 Flash (`gemini-3.8-flash-high` via `agy`) scored all 108 answers twice (A/B swapped on pass 2); Fable 5.1 then adjudicated all 54 cards against `eval/RUBRIC.md`, changing 13 fields on 11 cards. Adjudication record: `eval/results/llm-judge/adjudication.json`.

By-kind (`docs/RESULTS.md` lines 32-35):

| kind | n | base pass | tuned pass | diff points | base critical | tuned critical |
|---|---:|---:|---:|---:|---:|---:|
| hard | 27 | 22.2% | 11.1% | -11.1 | 1 | 5 |
| ordinary | 27 | 37.0% | 14.8% | -22.2 | 1 | 3 |

By-intent, passes out of 2 (`docs/RESULTS.md` lines 39-67):

| intent | base pass | tuned pass | base critical | tuned critical |
|---|---:|---:|---:|---:|
| cancel_order | 2 | 0 | 0 | 0 |
| change_order | 0 | 0 | 0 | 0 |
| change_shipping_address | 0 | 0 | 0 | 0 |
| check_cancellation_fee | 2 | 0 | 0 | 0 |
| check_invoice | 1 | 0 | 0 | 0 |
| check_payment_methods | 1 | 0 | 0 | 1 |
| check_refund_policy | 2 | 0 | 0 | 1 |
| complaint | 0 | 0 | 0 | 0 |
| contact_customer_service | 1 | 0 | 0 | 2 |
| contact_human_agent | 0 | 0 | 0 | 0 |
| create_account | 0 | 0 | 0 | 0 |
| delete_account | 0 | 0 | 0 | 0 |
| delivery_options | 1 | 0 | 0 | 2 |
| delivery_period | 0 | 0 | 1 | 0 |
| edit_account | 0 | 2 | 0 | 0 |
| get_invoice | 0 | 1 | 0 | 0 |
| get_refund | 1 | 0 | 1 | 0 |
| newsletter_subscription | 1 | 0 | 0 | 0 |
| payment_issue | 1 | 0 | 0 | 0 |
| place_order | 0 | 1 | 0 | 0 |
| recover_password | 1 | 0 | 0 | 0 |
| registration_problems | 1 | 0 | 0 | 0 |
| review | 1 | 1 | 0 | 0 |
| set_up_shipping_address | 0 | 0 | 0 | 1 |
| switch_account | 0 | 1 | 0 | 1 |
| track_order | 0 | 0 | 0 | 0 |
| track_refund | 0 | 1 | 0 | 0 |

## 2. Corpus similarity

ROUGE-L and cosine, base (Q8, Ollama) vs tuned, on the 270-row group-disjoint test sample, references `eval/results/test-sample-refs.jsonl`:

| source file | rouge_l_f1 mean | rouge_l_f1 median | embedding_cosine mean | embedding_cosine median | truncated_rate | mean length (tokens) |
|---|---:|---:|---:|---:|---:|---:|
| `eval/results/base-test-sample-auto.json` | 0.215264961565221 | 0.20689655172413793 | 0.6740771923490144 | 0.7102304399013519 | 0.1037037037037037 | 107.81111111111112 |
| `eval/results/tuned-test-auto.json` (fp16 merged) | 0.3658998032866334 | 0.34673807655016387 | 0.8314805700823112 | 0.8570169806480408 | 0.025925925925925925 | 91.82962962962964 |
| `eval/results/tuned-q8-test-auto.json` (Q8 served) | 0.36673390193458066 | 0.35413423283169 | 0.8287723180320528 | 0.861555814743042 | 0.022222222222222223 | 91.78518518518518 |

Paired diff, tuned fp16 minus base (`tuned-test-auto.json` `compare.diff`), n=270, n_boot=2000, seed=42:
- rouge_l_f1: point -0.15063484172141242, ci95 [-0.16519623303050934, -0.1367704888134519] (sign: tuned minus base is reported as -0.1506 because `compare.other_out` in that file is `base-test-sample-auto.json`; RESULTS.md line 89 reports the same magnitude as a +0.151 gain for tuned, i.e. the file stores base-minus-tuned sign convention here)
- embedding_cosine: point -0.15740337773329682, ci95 [-0.17928249086908718, -0.13652345054782927]

Base on the full 2,270-row test split (`eval/results/base-test-auto.json`): rouge_l_f1 mean 0.22603130327819126, embedding_cosine mean 0.7107196343094438, generated_at 2026-09-06 05:40 IST.

## 3. Data audit v1

Top-level (`data/audit.json`):

| key | value |
|---|---:|
| raw_rows | 26872 |
| kept_rows | 22448 |
| rejected_rows | 4424 |
| overlength_dropped | 8 |

`rule_counts`, every `reject_*` id (`data/audit.json`):

| rule id | count |
|---|---:|
| reject_completed_action | 1 |
| reject_invented_timeline | 50 |
| reject_placeholder_no_neutral_wording | 4355 |
| reject_request_credentials | 1 |
| reject_unresolved_placeholder | 9 |

Sum of `reject_*` = 4416; plus `drop_overlength_512` (also counted under `overlength_dropped`) = 8; total = 4424 = `rejected_rows`. This confirms the 4,355 figure quoted earlier in the thread for placeholder rejections with no substitute (`reject_placeholder_no_neutral_wording`, the rule fired by `configs/cleaning.json`'s `placeholder_reject_name_regex` on names like phone, hours, url, policy).

Per-intent, raw (`data/PROFILE.md`, "Per-intent counts" section) vs kept/train/val/test (`data/audit.json` `per_intent`), all 27 intents:

| intent | raw (PROFILE.md) | kept | train | val | test |
|---|---:|---:|---:|---:|---:|
| cancel_order | 998 | 66 | 64 | 1 | 1 |
| change_order | 997 | 942 | 685 | 48 | 209 |
| change_shipping_address | 973 | 973 | 756 | 109 | 108 |
| check_cancellation_fee | 950 | 950 | 729 | 77 | 144 |
| check_invoice | 1000 | 926 | 656 | 101 | 169 |
| check_payment_methods | 999 | 942 | 761 | 109 | 72 |
| check_refund_policy | 997 | 889 | 667 | 196 | 26 |
| complaint | 1000 | 887 | 673 | 88 | 126 |
| contact_customer_service | 1000 | 151 | 122 | 12 | 17 |
| contact_human_agent | 999 | 884 | 678 | 95 | 111 |
| create_account | 997 | 933 | 769 | 102 | 62 |
| delete_account | 995 | 908 | 816 | 38 | 54 |
| delivery_options | 995 | 564 | 504 | 47 | 13 |
| delivery_period | 999 | 973 | 779 | 97 | 97 |
| edit_account | 1000 | 739 | 423 | 135 | 181 |
| get_invoice | 999 | 977 | 736 | 160 | 81 |
| get_refund | 997 | 857 | 676 | 45 | 136 |
| newsletter_subscription | 999 | 979 | 816 | 107 | 56 |
| payment_issue | 999 | 837 | 717 | 90 | 30 |
| place_order | 998 | 934 | 742 | 101 | 91 |
| recover_password | 995 | 435 | 327 | 66 | 42 |
| registration_problems | 999 | 924 | 771 | 84 | 69 |
| review | 997 | 961 | 788 | 113 | 60 |
| set_up_shipping_address | 997 | 944 | 651 | 115 | 178 |
| switch_account | 1000 | 969 | 808 | 123 | 38 |
| track_order | 995 | 962 | 894 | 13 | 55 |
| track_refund | 998 | 942 | 693 | 205 | 44 |

Sums confirmed against top-level totals: kept 22448, train 17701, val 2477, test 2270 (`data/audit.json` per-intent, summed).

Note: raw per-intent total from `data/PROFILE.md` sums to 26872 (matches `raw_rows`); PROFILE.md's per-intent counts are pre-cleaning, HF-mirror counts and do not distinguish rejection reason per intent.

Split sizes and sha256 (`eval/SEAL.json`):

| split | rows (audit.json) | sha256 (SEAL.json split_sha256) |
|---|---:|---|
| train | 17701 | 307c59da350336a7bc603c5b2221043099df828ef55e1d409095868c4d51c6a7 |
| val | 2477 | b5f2e52d0d327cabd7cf8f83097c634c2f1132f6274e344d1677b05f02b304d3 |
| test | 2270 | ef864aace40157971664c067b12972fddc448ba24729a3a6f8658015faee20af |

`SEAL.json` also records: `split_seed` 42, `split_threshold` 0.86, `challenge_sha256` 76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6, `rows` 54, `sealed_by` Fable 5.1, `sealed_at` 2026-09-06 12:51 IST.

Row cap the v1 checkpoint actually trained on: **8,000**, `configs/train-t4.yaml` line 14 (`cap_train: 8000`), the group-aware cap from `data/prepare.py --cap-train` (`docs/TRAINING.md` lines 6-15). Confirmed as the served run: `docs/SELECTION.md` line 3 and lines 94/136/141 name `train/runs/local-t4/checkpoint-400` as the tuned artifact; `docs/LOCAL_RUN.md` confirms `local-t4` used `configs/train-t4.yaml` unchanged and trained 500 optimizer steps (8,000 rows at grad-accum 16) to completion on `mps`. The full 17,701-row `configs/train.yaml` (Colab Pro target) was not the run selected (`docs/LOCAL_RUN.md` line 5: "If a Colab run lands later, that one is the main run and this is the documented fallback"; no later Colab run is recorded as superseding it in `docs/SELECTION.md`).

## 4. Admission counts

From `docs/RESULTS.md` lines 75-79 ("Why" table) and `docs/FAILURES.md` line 5:

| | base answers (54) | tuned answers (54) | training split (17,701 rows) |
|---|---:|---:|---:|
| admits a missing fact ("I don't have access", "I'm not able to", "I can't") | 14 | 0 | 15 |
| uses a Bitext template phrase ("I'm on it", "I'm on the same wavelength", "Rest assured"; first two as openers, third anywhere) | 0 | 11 + 13 + 9 | 250 + 43 + 3,632 |
| refuses outright ("I can't assist with that") | 5 | 0 | 0 |

Method: `eval/admission_scan.py` (landed 2026-09-07, node V2-E0v/V2-E0f), documented case-insensitive phrase list, not fitted to the earlier hand counts. The earlier hand counts (17, 24) were not reproducible under any recorded method and are superseded; the direction of the finding is unchanged.

```
uv run python eval/admission_scan.py \
  eval/results/base-challenge-raw.jsonl \
  eval/results/tuned-challenge-raw.jsonl \
  data/processed/train.jsonl
```

| metric | script |
|---|---:|
| base admit / 54 | 14 |
| tuned admit / 54 | 0 |
| train admit / 17,701 | 15 |
| train "I'm on it" opener | 250 |
| train "I'm on the same wavelength" opener | 43 |
| train "Rest assured" anywhere | 3,632 |

Additionally, for the "17 of the 8,000 rows the T4 config trains on" clause in `docs/RESULTS.md`: the frozen `data/processed/train.jsonl` (17,701 rows) capped with `train/train.py`'s own `cap_rows` (which calls `data/prepare.py`'s `cap_train_rows`, the same group-aware routine the T4 run used, seed 42, no re-embedding or re-clustering) gives an 8,000-row subset with **5** admission hits, run 2026-09-07 to a gitignored scratch path, not committed.

`docs/FAILURES.md` gives additional per-intent counts behind three named failures (`ch-017`, `ch-025`, `ch-001`), each citing `data/audit.json` / `data/PROFILE.md` / `configs/cleaning.json`:
- `contact_customer_service`: 773 of 1,000 raw rows carry a phone/hours placeholder; 849 of 1,000 rejected, 151 kept, 122 in train/8,000-cap (line 43).
- `delivery_options`: 542 of 995 raw rows enumerate shipping tiers; 410 rejected for placeholder name, 21 more by `reject_invented_timeline`, 564 kept, 504 in train split, 166 still enumerate tiers, 96 mention in-store pickup (line 74).
- `cancel_order`: 932 of 998 raw rows rejected (placeholder names), 66 kept, 64 in train split and in the 8,000-row cap, 0.8% of what the model saw (line 105).

These three intent-level figures are internally consistent with the audit.json `per_intent` table in section 3 above (cancel_order kept=66/train=64; delivery_options kept=564/train=504; contact_customer_service kept=151/train=122).

## 5. Frozen items

| path | line count | sha256 |
|---|---:|---|
| `configs/versions.json` | 22 | c38c69c941986fa5e53bad37d13d041cf3abd073a2e814a345df7ced2f9d99f8 |
| `configs/train.yaml` | 67 | 0e664f11671c652d507c8d21ab7eedc7c2211462e91d484b71bc40cb2605ea62 |
| `configs/train-t4.yaml` | 67 | a24d4ce29f0d0bd6a1c7efe5f7fe18efc56c61e595e6bc03b857455387d4a219 |
| `configs/prompt.txt` | 1 | d738ddb811ab3d1bb0d0804b2f1a9978b48435f9adb518159b5360ff7bd53443 |
| `configs/eval.yaml` | 48 | 2591638608d3393334ae86451c11d73f3dd431950fc49b00077dfe7b4342f8b1 |
| `eval/RUBRIC.md` | 40 | 2c6a43da3068119e976dc01d9e9bba409d4393aa34d9a89971ff835ad0e2eef1 |
| `eval/challenge.jsonl` | 54 | 76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6 |

`eval/challenge.jsonl` sha256 matches `eval/SEAL.json` `challenge_sha256`, confirming the sealed file on disk is unchanged.

## 6. Compute facts

Machine (`docs/dag/CONTRACTS.md` section 1): Apple M1 Pro, 16 GB unified memory, 230 GiB free at profiling time, no CUDA. `python3` system is 3.14; repo venv is Python 3.11.11 via `uv run`.

v1 training wall time and config, served run (`docs/LOCAL_RUN.md`):
- Config: `configs/train-t4.yaml`, unchanged, `--device mps` override, git sha `ea665794329394bc36be8b31934011f661b2922f`.
- Started 2026-09-06 00:55:54 IST, finished 2026-09-06 03:43:04 IST. Wall time 10,028.9 s (2 h 47 min 09 s), about 20.1 s per optimizer step.
- 500 of 500 steps, one full epoch. Peak memory 8.24 GB (gate limit 12 GB). Final train loss 0.79433, final validation loss 0.65170.
- Checkpoints at steps 100, 200, 250, 300, 400, 500 (`save_every: 100` plus `checkpoint_fractions: [0.5, 1.0]`).

Checkpoint selection (`docs/RESULTS.md` line 100, `docs/SELECTION.md` lines 3, 19): `checkpoint-400` chosen on `eval/dev.jsonl`, 13/54 dev passes with 20 critical failures, against 12/18 for checkpoints 300 and 500 and 9/14 for 250.

Eval/score/bench run times recorded:
- `eval/results/base-test-auto.json` / `tuned-test-auto.json`: `generated_at` 2026-09-06 05:40 IST / 10:26 IST.
- `eval/results/tuned-q8-test-auto.json`: `generated_at` 2026-09-06 11:03 IST.
- `eval/results/llm-judge/meta.json`: Gemini judging started 2026-09-06 16:37 IST, finished 16:49 IST, 54 cards, 0 missing.
- Serving bench (`docs/RESULTS.md` lines 104-111): `serve/bench.py`, 30 serial requests after 5 warmups, Ollama 0.24.0, M1 Pro 16 GB. `ghl-base` p50 1.35 s / p95 3.34 s / 66.8 tok/s / cold load 0.89 s / 0 failures. `ghl-support` p50 1.43 s / p95 2.94 s / 65.9 tok/s / cold load 2.30 s / 0 failures.

## 7. Sealed-set rule and contamination

`eval/SEAL.json` `rule`: "eval/challenge.jsonl must not change after this seal; eval/blind.py refuses a mismatching hash."

Contamination fact: the v2 data-fix direction (substitute placeholders instead of rejecting) was chosen after `docs/RESULTS.md` and `docs/FAILURES.md` were written, both dated 2026-09-06 17:35 IST, which required reading all 54 challenge answers and their failure content (`docs/FAILURES.md` walks through verbatim answers for `ch-017`, `ch-025`, `ch-001`). `eval/challenge.jsonl` itself was not edited (sha256 unchanged, section 5/6 above), but the fix that v2 will apply to `configs/cleaning.json` was informed by having read the sealed set's answers, which `configs/eval.yaml` line 48 (`never_retune_on_challenge: true`) and `eval/SEAL.json`'s rule both bear on.

## 8. Clock

Mon 2026-09-07 20:00 IST soft. Tue 2026-09-08 20:00 IST final.
