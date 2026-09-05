---
title: "GHL SLM Assignment: Compressed Plan for the Real Deadlines (2026-09-05 20:50 IST)"
---

# 0. What changed

The Astra plan (`E2E_PLAN_2026-09-05-1950IST.md`) assumed a September 11 deadline and spread 22 active hours over September 5 to 9 with September 10 as buffer.
Shark gave the real dates in the GoHighLevel-prep thread on September 5 at 20:44 IST:

| Checkpoint | Date (IST, "evening" read as 20:00) | Hours from now |
|---|---|---|
| Soft deadline 1 | Sunday 2026-09-06 20:00 | 23 |
| Soft deadline 2 | Monday 2026-09-07 20:00 | 47 |
| Final deadline | Tuesday 2026-09-08 20:00 | 71 |

The buffer day is gone. The 22 active hours still fit (Sat 2 + Sun 8 + Mon 7 + Tue 5) but only with zero slack, so this plan buys slack by cutting scope, not by working faster. Everything in the Astra plan that is not a date or a cut below still stands: decision audit, traps, evaluation rules, README outline, fresh-clone contract.

Compute update, same thread 21:28 IST: shark has Google Colab Pro (or will pay the twenty dollars for it). Colab Pro is now the primary trainer; free Kaggle T4 stays as the backup because a free backup costs nothing to keep. Note the readme, line 34: "Free compute (Kaggle / Colab) is sufficient; do not spend money on this." An existing subscription is fine to use and should be disclosed in the README; buying one for this assignment goes against that line, so the README should say the run also fits a free T4 and the config for that is included.

Verdict on scope: train + eval + serve + README + Loom is achievable by Tuesday 20:00 IST if three things hold. Colab Pro attaches a GPU with internet tonight. The cuts in section 2 are accepted. Sharad's three time blocks in section 4 land at the named slots. If any of the three slips, section 5 says what drops next.

# 1. Checkpoint milestones

Each checkpoint names what is demoable, what must exist on disk, and the check that proves it.

## Sunday 2026-09-06 20:00 IST: data frozen, harness proven, training running

Demoable: open the split audit and the sealed challenge file hashes; run the eval harness against the base model and show 20 inspected base answers; show the Kaggle notebook mid-epoch with a live loss curve.

Must exist: `data/processed/{train,val,test}.jsonl`, `data/splits.json`, `data/audit.json`, `eval/challenge.jsonl` (hashed, sealed), `eval/dev.jsonl`, `configs/prompt.txt`, `eval/run.py`, `eval/results/base-dev.jsonl`, `train/train.py`, a running or finished epoch-1 Kaggle run with checkpoints saved to Hub or Kaggle output.

Check: `python data/prepare.py --audit-only --strict` passes; `python eval/run.py --model base --split dev --check-complete` passes; the training notebook shows finite loss past step 100.

Stretch: epoch 1 finished and adapter downloaded.

## Monday 2026-09-07 20:00 IST: tuned model served locally, headline numbers exist

Demoable: two `curl` calls against the local Ollama endpoint, base then tuned, on the two fixed demo queries; the challenge scoreboard with pass rates, point difference and bootstrap interval; the bench JSON.

Must exist: `artifacts/adapter/`, `artifacts/merged/`, `artifacts/{base,tuned}-q8.gguf`, `artifacts/manifest.json`, `serve/Modelfile`, `serve/inference.py`, `serve/bench_results.json`, `eval/results/{raw,scores,summary,failures}.jsonl` for the challenge set, Bitext test automated metrics, `train/runs/main/{loss.csv,curves.png}`.

Check: `python eval/score.py --final --require-complete`; `python serve/bench.py --requests 30 --concurrency 1 --check`; the fresh-clone curl from Astra plan section 10 returns a nonempty answer.

This is the real submit-minus-docs point. Reaching it Monday turns Tuesday into writing and recording only.

## Tuesday 2026-09-08 20:00 IST: submitted

Demoable: the submission email or form receipt.

Must exist: README with results, failures, prompt template, trade-offs and real-versus-cut section; public Hub links for adapter, merged weights and GGUF; Loom link; `submission.json`; a fresh-clone smoke transcript from a temp directory on this Mac.

Check: `python tools/check_submission.py submission.json`; open every link in a private browser window; watch the Loom once end to end. Target send time 18:00 IST, leaving two hours for link or upload failures.

# 2. Scope cuts beyond the Astra DROP list

These are the cuts that create the buffer. Estimated savings are planning figures, not measurements.

| Cut | Astra plan said | Now | Saves | Cost to the submission |
|---|---|---|---|---|
| Challenge set size | 108 sealed queries (54 ordinary + 54 hard) | 54: two per intent, one ordinary and one hard | ~1h authoring, ~2h blind scoring | Wider bootstrap interval; a 5-point gain is harder to confirm. Disclose. |
| Challenge authorship | Sharad authors all queries before outputs | Agent drafts 54 from intent list, Sharad edits and approves in one 45-minute block Sunday; hashed before any tuned output exists | ~1h of Sharad's time | None if approval happens before generation. Disclose drafting method. |
| LLM judge | Local Llama-3.1-8B Q4, order-swapped, on challenge + 270 Bitext test, human-checked | Cut from the required path. Bitext test gets automated reference metrics only (ROUGE-L, BERTScore or embedding similarity, placeholder rate, length). Judge becomes a Monday stretch on the 54 challenge pairs only | 5 to 7h of Mac time plus model pull and memory juggling | Secondary metric weaker. Human blind pass rate was already the headline. |
| fp16 scored pass | Compare both fp16 checkpoints and both Q8 builds separately | Score only the served Q8 artifacts (base-Q8 vs tuned-Q8 through Ollama). Ship fp16 merged weights for graders; spot-check 10 dev answers for Q8 drift | ~1.5h generation and scoring | Headline reflects the served artifact, which is arguably more honest. Disclose the drift spot-check size. |
| Epoch comparison | One epoch, optionally two, pick on dev | One epoch with mid-epoch checkpoints at 50% and 100%; pick on dev. Second epoch only if epoch 1 ends before Sunday 22:00 IST | ~1.5h GPU + a dev eval pass | Loss curve shorter. State the choice. |
| Threshold calibration | Label 100 candidate pairs across similarities before splitting | Label 40 pairs in a 30-minute time box; normalized-exact match + template family + embedding threshold | ~1h | Slightly weaker leakage argument. Report residual uncertainty as the plan already does. |
| Training rows | Cap 8,000 diverse rows (unmeasured choice) | Lift the cap. On a Colab Pro A100 or L4 at 512 tokens, the full ~21k grouped train rows run one epoch in roughly 30 to 60 minutes (planning estimate; measure on the smoke run). Keep 8,000 as the free-T4 config so the README can say the run also fits free compute | 0h; Colab Pro pays for it | Removes the unmeasured cap that was the weakest choice in the Astra plan. If the smoke run shows the full set overrunning 90 minutes, fall back to the 8,000-row config. |
| Fresh-clone check | Fresh clone on a clean machine | Fresh clone into a temp dir on this Mac with a fresh venv | ~1h | Weaker portability proof. Say so. |
| Loom length | 4 minutes | 3 minutes, shot list trimmed to 5 shots, one take plus one retake | ~30 min | None material. |
| Concurrency bench | Concurrency 4 optional and labeled | Serial only | ~20 min | None material. |

Net: roughly 12 to 15 hours removed from the critical path, which is the buffer the calendar took away. Sharad's involvement drops from 4 to 6 hours to about 3.5 hours.

# 3. Hour-by-hour schedule

Blocks are IST. Engineer hours are the agent's active time; GPU hours run unattended.

## Saturday 2026-09-05, 21:00 to 23:00 (2h): Phase A, access and scaffold

- 21:00 Sharad: open Colab Pro, attach a GPU runtime, run `nvidia-smi` and paste the output into the thread (GPU type and memory decide the training config). Also confirm a free Kaggle T4 attaches with internet as the backup. This is the single hard gate for the whole plan.
- 21:00 Engineer: repo scaffold, `uv` lock, download Bitext CSV, record revision and checksum, profile fields, lengths, duplicates, templates. Verify Qwen2.5-1.5B-Instruct pinned revision and LICENSE offline.
- 22:30 Engineer: `tools/preflight.py` report saved.
- Gate: free training device confirmed by 23:00. If not, section 5 row 1 fires tomorrow at 12:00.

## Sunday 2026-09-06, 09:00 to 20:00 (8h engineer, ~3h GPU)

- 09:00 to 11:30 Phase B: normalize, group, 40-pair threshold check, group split 80/10/10, audit, freeze hashes. Draft 54 challenge queries from the 27 intents.
- 11:30 to 12:15 Sharad block 1 (45 min): edit and approve the 54 challenge queries and the pass rubric. Hash and seal on approval.
- 12:00 Fallback trigger: if no free GPU confirmed, start the local fallback in section 5.
- 12:15 to 15:30 Phase C: prompt frozen in `configs/prompt.txt`, eval harness, loss-mask fixtures, tests, base fp16 dev answers on Kaggle GPU, 20 answers inspected, base GGUF built and imported into Ollama, prompt parity checked between Transformers and Ollama.
- 15:30 to 16:30 Phase D launch: `train/train.py --smoke` on Colab Pro, then full epoch-1 run started with checkpoints pushed to Hub every 100 steps. Resume tested once on the smoke run. With an A100 or L4, epoch 1 should end inside this window, so epoch 2 becomes the default rather than the stretch.
- 16:30 to 20:00 while GPU runs: `serve/inference.py`, `serve/bench.py`, `eval/score.py` with bootstrap, README skeleton with fixed sections, Bitext test automated-metric code. Base-model bench recorded.
- 20:00 Checkpoint 1 review in the thread.
- 20:00 to 22:00 if epoch 1 is done: download adapter, dev eval of both checkpoints, decide epoch 2 or not.

## Monday 2026-09-07, 09:00 to 20:00 (7h engineer, ~1h GPU, 1.5h Sharad)

- 09:00 to 10:30 Phase D close: select checkpoint on dev pass rate then critical errors then earlier checkpoint; write `artifacts/selection.json`; generate Bitext test answers for base and tuned in fp16 on the GPU; compute automated metrics.
- 10:30 to 12:30 Phase E: merge adapter into original fp16 base, adapter-versus-merged parity on 10 dev items, convert tuned to Q8 GGUF with the same pinned converter as the base, import into Ollama, Q8 drift spot-check on 10 dev answers, write manifest, push adapter + merged + GGUF to Hub.
- 12:30 to 13:30 Generate the 54 challenge answers for base-Q8 and tuned-Q8 through the Ollama HTTP path. Randomize order, hide identities, produce the blind scoring sheet.
- 13:30 to 15:00 Phase F: Modelfile, bench 30 dev prompts serial after 5 warmups, cold-load time, bench JSON, fresh-clone curl.
- 15:00 to 17:00 Loss curves, failure extraction scaffolding, README results tables wired to `eval/results/summary.jsonl`.
- 18:00 to 19:30 Sharad block 2 (90 min): blind-score 108 answers on the sheet. Engineer scores nothing.
- 19:30 to 20:00 Unblind, compute pass rates, difference, bootstrap interval, critical-error counts. Classify positive, inconclusive or negative per the Astra rule.
- 20:00 Checkpoint 2 review in the thread, including the honest verdict.

## Tuesday 2026-09-08, 09:00 to 18:00 (5h engineer, ~45 min Sharad)

- 09:00 to 11:30 README complete: model and method reasons, data and split, results with interval, three real failures with both answers and cause, exact prompt template, load and run commands, real-versus-cut, production trade-offs.
- 11:30 to 12:30 Fresh-clone smoke in a temp directory with a new venv; save the transcript.
- 12:30 to 13:30 Optional stretch only if Monday landed on time: Llama judge on the 54 challenge pairs, order-swapped, reported as secondary.
- 14:00 to 15:00 Sharad block 3 (45 min): record the 3-minute Loom with the engineer driving the shot list; one retake allowed.
- 15:00 to 17:00 `submission.json`, all links opened in a private window, Loom watched once, final read of README.
- 18:00 Submit. Post the receipt in the thread. 20:00 is the wall; nothing changes after 18:00 except a fix for a dead link.

# 4. What Sharad has to do, and when

| Block | When (IST) | Length | Task |
|---|---|---|---|
| 0 | Tonight by 23:00 | 15 min | Attach a Colab Pro GPU and paste `nvidia-smi`; confirm a free Kaggle T4 as backup. Ask the recruiter whether they want a public endpoint or runnable artifacts; the plan assumes runnable artifacts plus a live local demo. |
| 1 | Sun 11:30 to 12:15 | 45 min | Edit and approve 54 agent-drafted challenge queries and the pass rubric. Nothing tuned may be generated before this is sealed. |
| 2 | Mon 18:00 to 19:30 | 90 min | Blind-score 108 challenge answers (54 queries x 2 models, order randomized, names hidden). |
| 3 | Tue 14:00 to 15:00 | 45 min | Record the Loom. |

Total about 3.5 hours. Blocks 1 and 2 are on the critical path; moving them moves the checkpoint.

# 5. If a gate slips

| Trigger | Action |
|---|---|
| Colab Pro fails to attach a GPU tonight | Use the free Kaggle T4 with the 8,000-row config; schedule unchanged. |
| Neither Colab Pro nor Kaggle attaches a GPU by Sun 12:00 | Train locally on the M1 Pro. bitsandbytes does not run on Apple silicon, so QLoRA is out; use `mlx-lm` LoRA (fp16 base, about 3 GB weights) on 2,000 rows, 1 epoch, rank 8. The Astra plan dropped MLX for serving; this reintroduces it only as the fallback trainer, and the adapter still exports to a merged fp16 checkpoint and GGUF. Expect 3 to 5 hours wall; the Sunday checkpoint becomes "training running", not "harness plus training". Disclose the smaller training set. |
| Epoch 1 not finished by Mon 10:30 | Ship the latest saved checkpoint. Loss curve shows where it stopped. |
| Monday checkpoint missed | Tuesday becomes eval plus docs. Cut the Llama judge stretch, cut the fresh-clone smoke, Loom to 2 minutes recorded at 16:00, submit by 19:00. |
| Blind scoring cannot happen Monday evening | Sharad scores Tuesday 09:00 to 10:30; README results section is written last, 11:00 to 12:30; everything else in Tuesday's list shifts by 90 minutes and the judge stretch is cut. |
| Challenge gain under 5 points or interval crosses zero | Report inconclusive exactly as the Astra rule says. Do not retune against the challenge set. The README's failure analysis and the honest verdict are the deliverable. |
| Hub upload fails | Attach the adapter (about 60 MB at rank 16) to the repo release and the GGUFs to a second free host; record hashes in the manifest either way. |

# 6. What did not change

Model, method, split rules, target inspection, evaluation rules, judge design (now optional), serving stack, README order, trap table, fresh-clone contract, and the 8,000-row cap all stand as written in the Astra plan. Section 8 of that plan still lists the open questions; rows 1, 2 and 6 are now Sharad block 0 above. Deadline row is closed: Tuesday 2026-09-08 20:00 IST, with Sunday and Monday 20:00 as soft checkpoints.
