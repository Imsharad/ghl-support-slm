# v2 Evidence Pack Verification

Written 2026-09-07 14:22 IST by Grok (task V2-E0v). Re-derived every number in `docs/v2/EVIDENCE.md` from the file it cites. Did not edit `EVIDENCE.md`.

Checked file: `docs/v2/EVIDENCE.md`, 202 lines, sha256 `7d35c6d704b983b1cae317db3780b11d27bcd262a837e8a1784ffbea1f91dc60` (matches Sonnet's report). That blob last changed in `f09cbc4`; still identical on current `v2`.

Mismatch count: **1**. All other cited machine-readable numbers match. Admission/template counts match `docs/RESULTS.md` as copies; the generating method was not recorded (section 4). `eval/admission_scan.py` is now that method; its counts are the ones v2 will report (part 2).

## Table

| number | stated | re-derived | source | match |
|---|---|---|---|---|
| EVIDENCE.md line count | 202 | 202 | `docs/v2/EVIDENCE.md` newline count | yes |
| EVIDENCE.md sha256 | 7d35c6d704b983b1cae317db3780b11d27bcd262a837e8a1784ffbea1f91dc60 | 7d35c6d704b983b1cae317db3780b11d27bcd262a837e8a1784ffbea1f91dc60 | sha256 of file at HEAD | yes |
| summary.jsonl row (verbatim) | n=54, base_pass_rate=0.2962962962962963, tuned_pass_rate=0.12962962962962962, diff_points=-16.666666666666664, ci95=[-33.33333333333333, 0.0], base_critical=2, tuned_critical=8, win=18, tie=7, loss=29, verdict=negative, n_boot=2000, seed=42 | identical | `eval/results/summary.jsonl` | yes |
| base pass 16/54 = 29.6% | 16/54 = 29.6% | 16/54 = 0.2962962962962963 → 29.6% to 1 d.p. | summary `base_pass_rate` × n | yes |
| tuned pass 7/54 = 13.0% | 7/54 = 13.0% | 7/54 = 0.12962962962962962 → 13.0% to 1 d.p. | summary `tuned_pass_rate` × n | yes |
| critical 2 vs 8 | 2, 8 | 2, 8 | summary `base_critical`, `tuned_critical` | yes |
| win/tie/loss | 18/7/29 | 18/7/29 | summary | yes |
| Gemini 108 answers × 2 passes | 108 answers twice | 54 cards × 2 answers = 108; pass1.json and pass2.json each have 54 keys | `eval/results/llm-judge/pass1.json`, `pass2.json` | yes |
| Flash self-disagreement | (RESULTS: 12 cards) | 12 cards, 12 fields: ch-006, ch-008, ch-012, ch-013, ch-014, ch-017, ch-023, ch-037, ch-039, ch-040, ch-047, ch-048 | pass1 vs pass2 on pass_A/pass_B/critical_A/critical_B/preferred | yes vs RESULTS L23 first clause |
| Fable field changes vs pass1 | 13 fields on 12 cards | 13 fields on **11** unique cards (ch-005, 006, 007, 008, 012, 013, 033, 037, 040, 047, 053); ch-013 and ch-053 have two fields each | `eval/results/llm-judge/adjudication.json` `changes_vs_pass1` | **no** |
| by-kind hard | n=27, 22.2%, 11.1%, -11.1, crit 1/5 | n=27, 0.2222…, 0.1111…, -11.111…, 1, 5 | summary `per_kind.hard`; RESULTS.md L34 | yes |
| by-kind ordinary | n=27, 37.0%, 14.8%, -22.2, crit 1/3 | n=27, 0.3703…, 0.1481…, -22.222…, 1, 3 | summary `per_kind.ordinary`; RESULTS.md L35 | yes |
| by-intent passes out of 2 (27 intents) | EVIDENCE L28–54 table | all 27 match `int(round(rate * 2))` and criticals | summary `per_intent`; RESULTS.md L41–67 | yes |
| base-test-sample-auto rouge_l_f1 mean/median | 0.215264961565221 / 0.20689655172413793 | identical | `eval/results/base-test-sample-auto.json` | yes |
| base-test-sample-auto embedding_cosine mean/median | 0.6740771923490144 / 0.7102304399013519 | identical | same | yes |
| base-test-sample-auto truncated_rate / mean length | 0.1037037037037037 / 107.81111111111112 | identical | same `truncated_rate`, `length_tokens.mean` | yes |
| tuned-test-auto rouge_l_f1 mean/median | 0.3658998032866334 / 0.34673807655016387 | identical | `eval/results/tuned-test-auto.json` | yes |
| tuned-test-auto embedding_cosine mean/median | 0.8314805700823112 / 0.8570169806480408 | identical | same | yes |
| tuned-test-auto truncated_rate / mean length | 0.025925925925925925 / 91.82962962962964 | identical | same | yes |
| tuned-q8-test-auto rouge_l_f1 mean/median | 0.36673390193458066 / 0.35413423283169 | identical | `eval/results/tuned-q8-test-auto.json` | yes |
| tuned-q8-test-auto embedding_cosine mean/median | 0.8287723180320528 / 0.861555814743042 | identical | same | yes |
| tuned-q8-test-auto truncated_rate / mean length | 0.022222222222222223 / 91.78518518518518 | identical | same | yes |
| compare.diff n, n_boot, seed | 270, 2000, 42 | 270, 2000, 42 | `tuned-test-auto.json` `compare.diff` | yes |
| compare.diff rouge_l_f1 point / ci95 | -0.15063484172141242, [-0.16519623303050934, -0.1367704888134519] | identical | `tuned-test-auto.json` `compare.diff` (`other_out` = `base-test-sample-auto.json`, so this is base−tuned) | yes |
| compare.diff embedding_cosine point / ci95 | -0.15740337773329682, [-0.17928249086908718, -0.13652345054782927] | identical | same | yes |
| base-test-auto full split | n=2270, rouge mean 0.22603130327819126, cosine mean 0.7107196343094438, generated_at 2026-09-06 05:40 IST | identical | `eval/results/base-test-auto.json` | yes |
| tuned-test-auto generated_at | 2026-09-06 10:26 IST | 2026-09-06 10:26 IST | `tuned-test-auto.json` | yes |
| tuned-q8-test-auto generated_at | 2026-09-06 11:03 IST | 2026-09-06 11:03 IST | `tuned-q8-test-auto.json` | yes |
| raw_rows | 26872 | 26872 | `data/audit.json` `raw_rows`; `data/PROFILE.md` L18 | yes |
| kept_rows | 22448 | 22448 | audit `kept_rows`; sum of `per_intent.*.rows` | yes |
| rejected_rows | 4424 | 4424 | audit `rejected_rows` | yes |
| overlength_dropped | 8 | 8 | audit `overlength_dropped`; `rule_counts.drop_overlength_512` | yes |
| reject_completed_action | 1 | 1 | audit `rule_counts` | yes |
| reject_invented_timeline | 50 | 50 | audit `rule_counts` | yes |
| reject_placeholder_no_neutral_wording | 4355 | 4355 | audit `rule_counts` | yes |
| reject_request_credentials | 1 | 1 | audit `rule_counts` | yes |
| reject_unresolved_placeholder | 9 | 9 | audit `rule_counts` | yes |
| sum reject_* + drop_overlength_512 | 4416 + 8 = 4424 | 4416 + 8 = 4424 | audit `rule_counts` | yes |
| per-intent raw/kept/train/val/test (27 intents) | EVIDENCE L99–126 | all 27 match; kept is `per_intent.<intent>.rows` (no `kept` key) | PROFILE.md L35–61 (raw); audit `per_intent` | yes |
| per-intent sums | kept 22448, train 17701, val 2477, test 2270 | 22448, 17701, 2477, 2270 | sum of audit `per_intent` | yes |
| PROFILE raw sum | 26872 | 26872 | sum of PROFILE.md L35–61 | yes |
| split sha256 train | 307c59da350336a7bc603c5b2221043099df828ef55e1d409095868c4d51c6a7 | identical | `eval/SEAL.json` `split_sha256.train`; also audit `splits.train.sha256` | yes |
| split sha256 val | b5f2e52d0d327cabd7cf8f83097c634c2f1132f6274e344d1677b05f02b304d3 | identical | SEAL + audit | yes |
| split sha256 test | ef864aace40157971664c067b12972fddc448ba24729a3a6f8658015faee20af | identical | SEAL + audit | yes |
| split_seed / split_threshold | 42 / 0.86 | 42 / 0.86 | SEAL.json; audit `seed`/`threshold` | yes |
| challenge_sha256 / rows | 76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6 / 54 | file sha256 identical, 54 nonempty lines | SEAL.json; sha256 of `eval/challenge.jsonl` | yes |
| sealed_by / sealed_at | Fable 5.1 / 2026-09-06 12:51 IST | identical | SEAL.json | yes |
| cap_train | 8000 | 8000 at `configs/train-t4.yaml` L14 | train-t4.yaml `data.cap_train` | yes |
| train.yaml vs t4 | t4 is the served 8,000-row run; full 17,701 is train.yaml | train.yaml has no cap_train; LOCAL_RUN.md L5, L38; SELECTION.md L3, L94, L136, L141 name `train/runs/local-t4/checkpoint-400` | configs + those docs | yes |
| optimizer steps | 500 steps, 8,000 rows at grad-accum 16 | 8000/16 = 500; LOCAL_RUN.md L62, L71 | LOCAL_RUN.md; train-t4.yaml | yes |
| RESULTS admission 17 / 0 / 24 | 17, 0, 24 | 17, 0, 24 copied from RESULTS.md L77; no script in repo | `docs/RESULTS.md` L77; `docs/FAILURES.md` L5 | yes as copy; method not recorded |
| RESULTS template train 250 + 43 + 3,632 | 250 + 43 + 3,632 | identical copy of RESULTS.md L78 | RESULTS.md L78 | yes as copy; method not recorded |
| RESULTS template tuned 11 + 13 + 9 | 11 + 13 + 9 | identical copy | RESULTS.md L78 | yes as copy |
| RESULTS refuse 5 / 0 / 0 | 5, 0, 0 | identical copy of RESULTS.md L79 | RESULTS.md L79 | yes as copy |
| contact_customer_service 849 rejected / 151 kept / 122 train | 849, 151, 122 | 1000−151=849; rows=151; train=122 | PROFILE raw 1000; audit `per_intent.contact_customer_service` | yes |
| contact_customer_service 773 phone/hours placeholders | 773 of 1,000 | not in audit.json or PROFILE.md | FAILURES.md L43 only | n/a |
| delivery_options 564 kept / 504 train | 564, 504 | rows=564, train=504 | audit | yes |
| delivery_options 995−564 = 431 rejected; 410 + 21 | 410 placeholder + 21 timeline | 995−564=431; 410+21=431 arithmetic holds; no per-intent rule breakdown in audit (`reject_invented_timeline` is 50 globally) | FAILURES.md L74; audit totals only | n/a for the 410/21 split |
| delivery_options 542 / 166 / 96 | 542 enumerate, 166 still enumerate, 96 pickup | not in audit.json or PROFILE.md | FAILURES.md L74 only | n/a |
| cancel_order 932 rejected / 66 kept / 64 train / 0.8% | 932, 66, 64, 0.8% | 998−66=932; rows=66; train=64; 64/8000=0.8% | PROFILE 998; audit; 8000 cap | yes |
| configs/versions.json lines / sha256 | 22 / c38c69c941986fa5e53bad37d13d041cf3abd073a2e814a345df7ced2f9d99f8 | 22 / identical | file | yes |
| configs/train.yaml lines / sha256 | 67 / 0e664f11671c652d507c8d21ab7eedc7c2211462e91d484b71bc40cb2605ea62 | 67 / identical | file | yes |
| configs/train-t4.yaml lines / sha256 | 67 / a24d4ce29f0d0bd6a1c7efe5f7fe18efc56c61e595e6bc03b857455387d4a219 | 67 / identical | file | yes |
| configs/prompt.txt lines / sha256 | 1 / d738ddb811ab3d1bb0d0804b2f1a9978b48435f9adb518159b5360ff7bd53443 | 1 / identical | file | yes |
| configs/eval.yaml lines / sha256 | 48 / 2591638608d3393334ae86451c11d73f3dd431950fc49b00077dfe7b4342f8b1 | 48 / identical | file | yes |
| eval/RUBRIC.md lines / sha256 | 40 / 2c6a43da3068119e976dc01d9e9bba409d4393aa34d9a89971ff835ad0e2eef1 | 40 / identical | file | yes |
| eval/challenge.jsonl lines / sha256 | 54 / 76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6 | 54 / identical; equals SEAL `challenge_sha256` | file + SEAL.json | yes |
| machine | Apple M1 Pro, 16 GB, 230 GiB free, no CUDA | quoted from CONTRACTS.md s1; 16 GB = 17179869184 bytes in `serve/bench_results.json` hardware; 230 GiB free is a snapshot, not re-measured | `docs/dag/CONTRACTS.md` L7; bench_results.json | yes as quote |
| python | system 3.14; venv 3.11.11 via uv | CONTRACTS.md L8–9; `configs/versions.json` `"python": "3.11.11"` | those files | yes |
| git sha of served run | ea665794329394bc36be8b31934011f661b2922f | commit exists (`dag: C1b done; D2L relaunched by Fable; C5 needs detached resume`) | LOCAL_RUN.md L39; `git cat-file` | yes |
| wall clock | start 2026-09-06 00:55:54 IST, finish 03:43:04 IST, 10028.9 s, 2 h 47 min 09 s, ~20.1 s/step | identical | LOCAL_RUN.md L68–70 | yes |
| 500/500, peak 8.24 GB, gate 12 GB | same | same | LOCAL_RUN.md L71–72 | yes |
| final losses | train 0.79433, val 0.65170 | identical | LOCAL_RUN.md L73–74 | yes |
| checkpoints | 100, 200, 250, 300, 400, 500 | listed LOCAL_RUN.md L111–116; `save_every: 100` + `checkpoint_fractions: [0.5, 1.0]` in train-t4.yaml L49, L51 | LOCAL_RUN.md; train-t4.yaml | yes |
| checkpoint-400 on dev | 13/54, 20 critical; 12/18 for 300 and 500; 9/14 for 250 | SELECTION.md L11–14: 250=9/14, 300=12/18, 400=13/20, 500=12/18 | SELECTION.md; RESULTS.md L100 | yes |
| llm-judge meta | started 2026-09-06 16:37 IST, finished 16:49 IST, 54 cards, 0 missing | identical (`missing: []`) | `eval/results/llm-judge/meta.json` | yes |
| bench ghl-base | p50 1.35 s, p95 3.34 s, 66.8 tok/s, cold 0.89 s, 0 failures | 1347.897 ms, 3336.968 ms, 66.787 tok/s, 894.253 ms, failure_count 0 | `serve/bench_results.json` `ghl-base.summary` | yes |
| bench ghl-support | p50 1.43 s, p95 2.94 s, 65.9 tok/s, cold 2.30 s, 0 failures | 1428.14 ms, 2942.103 ms, 65.855 tok/s, 2296.166 ms, failure_count 0 | `serve/bench_results.json` `ghl-support.summary` | yes |
| bench n / warmup / ollama | 30 serial after 5 warmups, Ollama 0.24.0 | request_count 30, warmup_requests 5, `ollama version is 0.24.0` | bench_results.json | yes |
| SEAL rule | eval/challenge.jsonl must not change after this seal; eval/blind.py refuses a mismatching hash. | exact string | SEAL.json `rule` | yes |
| RESULTS/FAILURES date | 2026-09-06 17:35 IST | both files open with that timestamp | RESULTS.md L3; FAILURES.md L3 | yes |
| never_retune_on_challenge | true at eval.yaml L48 | L48 `never_retune_on_challenge: true` | `configs/eval.yaml` | yes |
| clock | Mon 2026-09-07 20:00 IST soft; Tue 2026-09-08 20:00 IST final | CONTRACTS.md L16 also lists Sun 2026-09-06 20:00 IST (elapsed); remaining two match the brief | CONTRACTS.md L16; V2-E0 brief | yes |

## Mismatch

**13 fields on 12 cards.** EVIDENCE.md L15 (from RESULTS.md L23) says Fable changed 13 fields on 12 cards. `eval/results/llm-judge/adjudication.json` `changes_vs_pass1` has 13 tuples and 11 unique `item_id`s. Flash's pass1/pass2 self-disagreement is a different 12 cards. RESULTS conflates those two 12s. Sonnet should change EVIDENCE.md L15 to "13 fields on 11 cards" (and RESULTS.md L23 if that file is in scope later). Not edited here.

## Not independently re-derivable (not counted as mismatches)

These EVIDENCE numbers exist only as prose in `docs/FAILURES.md`. `data/audit.json` has no per-intent reject breakdown and no placeholder-name census: 773 phone/hours rows, 542 enumerated delivery tiers, 410+21 delivery reject split, 166 remaining enumerated-tier train rows, 96 in-store pickup train rows. Arithmetic around them (849=1000−151, 431=995−564=410+21, 932=998−66) holds.

Admission 17/0/24 and template 250+43+3632 were copied from RESULTS.md. No regex or script was in the tree. That is the missing method.

## Part 2: `eval/admission_scan.py`

Documented, case-insensitive, not fitted to the v1 counts. Admission phrases: "I don't have access", "I'm not able to", "I can't", "I do not have", "I'm unable to", "I don't know". Template: "I'm on it" and "I'm on the same wavelength" as openers; "Rest assured" anywhere. `I can't` is a substring of `I can't assist with that`, so those rows also increment admit. Unicode apostrophes fold to ASCII.

Command:

```
uv run python eval/admission_scan.py \
  eval/results/base-challenge-raw.jsonl \
  eval/results/tuned-challenge-raw.jsonl \
  data/processed/train.jsonl
```

| metric | stated (RESULTS.md) | script | same? |
|---|---:|---:|---|
| base admit / 54 | 17 | 14 | no |
| tuned admit / 54 | 0 | 0 | yes |
| train admit / 17,701 | 24 | 15 | no |
| train "I'm on it" opener | 250 | 250 | yes |
| train "I'm on the same wavelength" opener | 43 | 43 | yes |
| train "Rest assured" anywhere | 3,632 | 3,632 | yes |

Tuned template openers also match RESULTS (11 + 13 + 9). Base refuse is 2 in the script vs 5 stated.

**v2 will report the script column**, not the RESULTS.md column. The three template train counts were already exact under this method. The admission counts were not: RESULTS used a method that is gone, and this list is the replacement.

EVIDENCE.md content verified is the `f09cbc4` blob, still unchanged on `v2` at commit time.
