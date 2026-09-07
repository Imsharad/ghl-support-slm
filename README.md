# Customer-support SLM: fine-tuned Qwen2.5-1.5B-Instruct, self-hosted

This repository answers the customer-support fine-tuning assignment in
[`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md). It keeps training, evaluation, conversion, and local
serving reproducible from pinned inputs.

## 1. What this is, and the headline result

A QLoRA fine-tune of `Qwen2.5-1.5B-Instruct` on the Bitext customer-support corpus, exported to
Q8 GGUF and served behind a local HTTP API through Ollama. Every input is pinned by revision or
hash: the dataset commit, the base-model commit, the llama.cpp converter commit, the split seed,
and a sha256 for each shipped artifact.

**The fine-tune made the model worse at the job it was trained for.** On 54 sealed support
queries the model never trained on, the served tuned model answers fewer of them acceptably than
the served base model, and states four times as many invented facts.

| Sealed challenge set, n = 54 | base (`ghl-base`, Q8) | tuned (`ghl-support`, Q8) |
|---|---:|---:|
| pass rate | **16 / 54 = 29.6%** | **7 / 54 = 13.0%** |
| critical failures (invented facts) | 2 | 8 |

| difference (tuned minus base) | 95% interval (paired bootstrap, 2,000 draws, seed 42) | preferred: tuned / tie / base | verdict |
|---:|---:|---:|---|
| **-16.7 points** | **[-33.3, +0.0]** | 18 / 7 / 29 | **negative** |

Source: [`eval/results/summary.jsonl`](eval/results/summary.jsonl), written by
[`eval/score.py`](eval/score.py); full tables and the scoring provenance in
[`docs/RESULTS.md`](docs/RESULTS.md). The pass/fail rule was fixed before the run: positive needs a
gain of at least 5 points, an interval clear of zero, and no rise in critical failures. Nothing was
retuned, rescored, or reselected after this number appeared.

The secondary metric moved the other way, which is the whole finding. On a held-out, group-disjoint
sample of the Bitext test split, the tuned model matches the reference answers far more closely:

| held-out Bitext, 270 rows, 270 groups | base (Q8) | tuned (Q8, served) |
|---|---:|---:|
| ROUGE-L F1 mean | 0.2153 | **0.3667** |
| MiniLM embedding cosine mean | 0.6741 | **0.8288** |

Source: [`eval/results/tuned-q8-test-auto.json`](eval/results/tuned-q8-test-auto.json) and
[`eval/results/base-test-sample-auto.json`](eval/results/base-test-sample-auto.json); method in
[`docs/EXPORT.md`](docs/EXPORT.md).

One line: fine-tuning on 8,000 cleaned Bitext rows taught the model to **write like Bitext**
(+15 ROUGE-L points on held-out Bitext) and made it a **worse support assistant** on out-of-distribution
queries (29.6% to 13.0%, criticals 2 to 8). The cause is in the data, not the recipe: the corpus
almost never says "I do not know". 15 rows out of 17,701 admit a missing fact
(`eval/admission_scan.py`). The base model admitted one in 14 of 54 challenge answers; the tuned
model in 0.
[`docs/FAILURES.md`](docs/FAILURES.md) walks three cases through to the training rows behind them.

**v2, the data repair, is also negative on a fresh sealed set.** Branch `v2` keeps every part of the recipe and changes only the data: placeholders substituted instead of rejected, and 206 synthetic rows that admit a missing fact (section 3). Trained on a free Colab T4 ([`notebooks/v2_colab_run.ipynb`](notebooks/v2_colab_run.ipynb), the executed run) and scored on a second sealed set written under a reading ban and sealed before any v2 row existed:

| Fresh sealed set, n = 54 | base (`ghl-base`, Q8) | v2 tune (`ghl-support`, checkpoint-250, Q8) |
|---|---:|---:|
| pass rate | **8 / 54 = 14.8%** | **12 / 54 = 22.2%** |
| critical failures (invented facts) | 6 | 12 |

| difference (tuned minus base) | 95% interval (paired bootstrap, 2,000 draws, seed 42) | preferred: tuned / tie / base | verdict |
|---:|---:|---:|---|
| **+7.4 points** | [-7.4, +22.2] | 22 / 12 / 20 | **negative** |

The pass rate moved the right way and the critical count the wrong way, and the rule fixed before v1 makes any rise in critical failures a negative; the interval also crosses zero. Gate 2, pre-registered in [`docs/v2/PLAN_DECISIONS.md`](docs/v2/PLAN_DECISIONS.md), failed, so the v1 headline stands and so does the recommendation to ship the base model. Where the tune improved is navigational questions whose honest answer is a path; where it did not is any question about a fee, a window, support hours or a carrier, where it still answers in the corpus's confident voice (10 of its 12 critical failures carry the judge tag *invented policy, fee or window*). Full account in [`docs/RESULTS.md`](docs/RESULTS.md) (v2 section) and [`docs/FAILURES.md`](docs/FAILURES.md) (v2 section). Two caveats travel with these numbers: the sheet is LLM-judged with adjudication, as v1's was, and the judge drifts between sessions (v1's own base answers scored 16 of 54 on 6 September and 4 of 54 today), so only base-against-tuned inside one session is on one scale; v1 and v2 pass rates are not.

- Weights and adapter: <https://huggingface.co/seekingtroooth/ghl-support-qlora-t4> (public; adapter,
  merged fp16, both GGUFs, manifest).
- Repository: <https://github.com/Imsharad/ghl-support-slm> (public; tag `v1` marks the submitted commit,
  branch `v2` and tag `v2` the data repair; v2 artifacts on the Hub under `v2/`).
- Loss curves: [`docs/curves.png`](docs/curves.png). Training log: [`docs/TRAINING.md`](docs/TRAINING.md).

## 2. Model and method choices, and why

The base is
[`Qwen/Qwen2.5-1.5B-Instruct` at revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306).
The reviewed model license is Apache-2.0, which permits use, modification, self-hosting, and
commercial distribution subject to its notice and attribution conditions. The exact review and
redistribution notes are in [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md).

The training source is
[`bitext/Bitext-customer-support-llm-chatbot-training-dataset` at revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443`](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/tree/430d1a89bd93bd1fa23c16f29dd53e73f0087443),
whose dataset card declares CDLA-Sharing-1.0. Raw and processed rows are not published in this
repository: CDLA sharing conditions continue to apply to Data and Enhanced Data, so the repository
publishes fetch/prepare code and integrity hashes while keeping those rows gitignored. Trained
weights and aggregate metrics are treated as computational Results; see the license review for the
scope and legal caveat.

Training used QLoRA with NF4 4-bit double quantisation and fp16 compute; LoRA rank 16, alpha 32,
dropout 0.05, and no bias on `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, and
`down_proj`; sequence length 512; micro-batch 1 with accumulation 16; gradient checkpointing; AdamW
at learning rate `1e-4` on a cosine schedule with 3% warmup; seed 42; loss on assistant tokens only.
That shape has 18,464,768 trainable parameters, 1.2% of the base model.

The run that produced the shipped adapter is `train/runs/local-t4`: one epoch over an 8,000-row
group-aware cap of the train split, on this Mac's MPS device, 500 optimizer steps in 10,029 seconds
(2 h 47 m) at 8.24 GB peak memory. Validation loss fell from 1.099 to 0.652 and flattened after
step 400 ([`train/runs/local-t4/loss.csv`](train/runs/local-t4/loss.csv),
[`train/runs/local-t4/config.json`](train/runs/local-t4/config.json)).

![Training and validation loss for the local-t4 run](docs/curves.png)

`checkpoint-400` was selected on `eval/dev.jsonl` alone, by dev pass rate, then critical failures,
then earlier step: 13/54 passes against 12 for steps 300 and 500 and 9 for step 250. The margin is
one item and step 400 carries the most critical failures of the four, so this is a weak selection
and [`docs/SELECTION.md`](docs/SELECTION.md) says so; 400 and 500 should be read as tied. No Bitext
test row and no training validation loss entered the choice
([`artifacts/selection.json`](artifacts/selection.json)).

The Apple M1 Pro probe that sized this shape before the run measured 2.567 seconds per
forward/backward pass and 4.09 GB peak MPS memory. Its random-token losses are timing ballast, not
convergence evidence. Full measurements and caveats are in
[`docs/LOCAL_QLORA_PROBE.md`](docs/LOCAL_QLORA_PROBE.md).

Why these choices:

- **Qwen2.5-1.5B-Instruct.** Apache-2.0, verified offline at the exact pinned revision, so
  commercial self-hosting needs no further clearance. At 1.5B the Q8 GGUF is 1.6 GB, small enough
  that base and tuned can both be imported into one Ollama instance on a 16 GB laptop and compared
  through a single endpoint. It ships a native ChatML template with an explicit system turn, so
  training, the Transformers route and the Ollama route share one template and can be checked for
  parity rather than assumed equal. A 27B-class open base (Qwen3.8-27B, also Apache-2.0) was
  considered and set aside: about 28 GB at Q8 and roughly 20 GB of GPU memory for QLoRA at 512
  tokens, so it fits neither a free T4 nor this laptop, and the brief asks for a small model served
  on your own hardware. A 14B-class base (Qwen2.5-14B-Instruct or similar) was considered and not
  run: the assignment says free compute is sufficient and not to spend money on this
  (`docs/ASSIGNMENT.md`), and a 14B QLoRA at this shape does not fit a free T4. The v1 failure is a
  data-shape failure, the corpus never says "I don't know" (`docs/RESULTS.md`), which a larger base
  does not repair.
- **QLoRA over full fine-tuning.** 18.5M trainable parameters instead of 1.5B fit a free T4 or this
  Mac's MPS device with the base frozen in 4-bit. The shipped adapter is 74 MB against 3.1 GB of
  merged fp16 weights, so base-versus-tuned is one frozen base plus a named delta rather than two
  unrelated checkpoints, and a bad tune is one directory to discard. Weights are gitignored and
  live on the Hub; `tools/fetch_artifacts.py` pulls them back and checks every hash.
- **Rank 16 on all seven projection matrices.** Attention-only LoRA is the cheaper default, but the
  task is register and phrasing, which lives in the MLP blocks as much as in attention. Rank 16 with
  alpha 32 is the standard 2x scaling, and at 512 tokens the memory cost of the extra three modules
  was measured, not assumed: 4.09 GB peak on the probe against a 16 GB envelope.
- **512 tokens.** The whole rendered exchange fits for all but 8 of 26,872 rows, so the cap costs
  almost no data, and it is the length the 2.567 s/step probe measured.
- **One epoch with mid-run checkpoints.** The dev sweep in `docs/SELECTION.md` shows why more would
  not have helped: past step 250, each checkpoint answers more completely and invents more at the
  same time. Pass rate and critical-failure count rise together. This is a data ceiling, not an
  undertrained model.
- **Assistant-only loss.** The system prompt is fixed and identical on every row; training the model
  to predict it wastes the budget and teaches nothing.
- **Ollama for serving.** llama.cpp behind an OpenAI-compatible HTTP endpoint runs the exact
  quantised artifact the evaluation scored, on the hardware available here, with no GPU. vLLM and TGI
  are the right answer for concurrent production traffic and the wrong answer for a single-user Mac.

## 3. Data handling and split strategy

The data pipeline is deterministic and keeps source, cleaning, grouping, and split evidence
separate:

1. [`data/fetch.py`](data/fetch.py) downloads the pinned Bitext revision into gitignored
   `data/raw/`.
2. [`data/prepare.py`](data/prepare.py) applies the ordered rules in
   [`configs/cleaning.json`](configs/cleaning.json), renders the native Qwen chat format, and drops
   examples over the 512-token training limit instead of silently truncating answers.
3. Exact normalized instructions, response-template families, and MiniLM embeddings at cosine
   threshold 0.86 are grouped with average linkage. The grouping configuration and calibration
   evidence are in [`configs/grouping.json`](configs/grouping.json) and
   [`data/calibration/REPORT.md`](data/calibration/REPORT.md).
4. Whole groups, never individual paraphrases, are assigned to train, validation, and test with
   seed 42. [`data/splits.json`](data/splits.json) freezes group membership and
   [`data/audit.json`](data/audit.json) records hashes, intersections, and residual similarity risk.

The pinned CSV has 26,872 rows and the 27 intents the assignment card names, but **11 categories,
not the 10 on the card** (an extra `CONTACT`, and `CANCEL`/`SHIPPING`/`SUBSCRIPTION` are named
differently). The CSV is treated as truth. Field profile, per-intent counts and placeholder
inventory are in [`data/PROFILE.md`](data/PROFILE.md).

The configured ordered cleaning rules are:

- `reject_completed_action`: remove answers that claim an account, order, refund, or request was
  already changed.
- `reject_invented_timeline`: remove unsupported numeric timelines unless the user supplied the
  same numbers.
- `reject_request_credentials`: remove answers asking for passwords, PINs, CVV/CVC, or full card
  details.
- `replace_placeholders`: replace only placeholders with the configured neutral wording.
- `reject_unresolved_placeholder`: remove any row that still contains a placeholder marker.

After those rules, the `drop_overlength_512` gate removes a fully rendered exchange when it exceeds
512 tokens.

### What the cleaning removed

All counts from [`data/audit.json`](data/audit.json), generated 2026-09-06 00:42 IST.

| | rows |
|---|---:|
| raw | 26,872 |
| kept | **22,448** |
| rejected | **4,424** (16.5%) |

| rule | rows hit |
|---|---:|
| `replace_placeholders` (substitution, row kept) | 8,658 |
| `reject_placeholder_no_neutral_wording` | 4,355 |
| `reject_invented_timeline` | 50 |
| `reject_unresolved_placeholder` | 9 |
| `drop_overlength_512` | 8 |
| `reject_completed_action` | 1 |
| `reject_request_credentials` | 1 |

Almost every rejection is one rule: a placeholder with no safe neutral substitute, chiefly
`{{Customer Support Phone Number}}`, `{{Customer Support Hours}}` and `{{Online Company Portal Info}}`.
That choice is the single largest cause of the headline result and is analysed in
[`docs/FAILURES.md`](docs/FAILURES.md). The 8,658 substitutions are the rows that survived, with a
neutral phrase in place of the placeholder.

### Splits

| split | rows | groups | sha256 |
|---|---:|---:|---|
| train | 17,701 | 3,568 | `307c59da350336a7bc603c5b2221043099df828ef55e1d409095868c4d51c6a7` |
| validation | 2,477 | 447 | `b5f2e52d0d327cabd7cf8f83097c634c2f1132f6274e344d1677b05f02b304d3` |
| test | 2,270 | 447 | `ef864aace40157971664c067b12972fddc448ba24729a3a6f8658015faee20af` |

The shipped adapter trained on an 8,000-row group-aware cap of the train split, not all 17,701; the
cap keeps whole groups on one side and every intent represented
([`configs/train-t4.yaml`](configs/train-t4.yaml)).

Leakage checks, all from `data/audit.json`:

- Cross-split group-id intersections: **empty** for train/val, train/test and val/test.
- Cross-split normalized-instruction intersections: **0** for all three pairs.
- Every intent appears in every split; none collapsed to a single group.

### Residual risk, stated plainly

Grouping cannot prove zero leakage, and the audit says how much is left. The nearest cross-split
neighbour check, within intent, over 4,747 pairs: minimum cosine 0.4776, median 0.8923, p95 0.9387,
maximum 0.9708. **3,693 of those pairs sit at or above the 0.86 grouping threshold.** They are not
duplicates by group id or by normalized instruction, but they are close paraphrases across the split
boundary, so the held-out Bitext metrics in section 4 should be read as near-domain, not
out-of-distribution. This is exactly why the headline evaluation uses a separately authored
challenge set instead.

Threshold calibration reinforces the point. 40 within-intent pairs were labelled by hand (35 same
scenario, 5 different); 0.86 is the lowest threshold with zero labelled-different pairs above it,
but its recall on that sample is 0.46, so paraphrases below the threshold are not grouped
([`data/calibration/REPORT.md`](data/calibration/REPORT.md)).

One intent is near collapse: `cancel_order` keeps only 66 of 998 raw rows, in 12 groups, and its
largest group is 53 rows, 80.3% of the intent. 64 of the 66 landed in train. That intent's
behaviour after tuning is `ch-001` in [`docs/FAILURES.md`](docs/FAILURES.md).

### v2 data: substitute, do not reject, plus 206 admission rows

Branch `v2` changes the data and nothing else. Two edits, both recorded rule by rule in
[`docs/v2/DATA_V2.md`](docs/v2/DATA_V2.md) and verified by an independent recount in
[`docs/v2/DATA_V2_VERIFY.md`](docs/v2/DATA_V2_VERIFY.md):

1. **Substitution instead of rejection.** `data/prepare.py --placeholder-mode substitute` replaces a
   placeholder that has no factual neutral wording with a phrase that asserts nothing (a phone number
   becomes "the number on our contact page", support hours become "the hours shown on our contact
   page"). A machine check refuses any phrase containing a digit, a URL, a currency symbol, a duration
   or a policy verb. 4,318 rows come back; 37 stay rejected because no honest phrase exists. The v1
   default output is byte-identical (`data/prepare.py --audit-only --strict` still passes).
2. **206 synthetic admission rows**, one shape only: the fact is not available, here is where to get
   it, here is the one thing the assistant can do now. Written by a stateless model call that saw only
   the intent list, the specification and a scenario sketch, never an evaluation query
   (`grok-4.5-build` through `tools/admissions.py`; Gemini Flash was the planned author and was
   replaced after five runs died on the training machine, decision 11). Every row passed a lint (no
   digits, times, prices, URLs, credentials, claimed actions or policy claims), an independent
   eight-check review by a second stateless call (259 of 340 accepted,
   [`docs/v2/ADMISSION_REVIEW_A2.md`](docs/v2/ADMISSION_REVIEW_A2.md)), and a leakage check against
   both sealed sets, the dev set and the v2 validation and test splits (cosine under 0.80, no shared
   six-word gram; 53 quarantined). The rows carry the flag `SYNTH_ADMISSION` and their own group ids,
   enter train only, and are exempt from the 8,000-row cap so the intervention is not sampled away
   (decision 4). The 440-row target was not reached; no row was edited to close the gap
   (decision 10).

The re-clustering is from scratch (same MiniLM model, 0.86 average linkage, seed 42), so group ids
and split membership are not row-comparable with v1. Side by side:

| Quantity | v1 (`main`) | v2 (`v2`) | Source |
|---|---:|---:|---|
| Raw rows | 26,872 | 26,872 | `data/audit.json`, `data/v2/audit.json` |
| Corpus rows kept | 22,448 | 26,764 | same |
| Synthetic admission rows (train only, `SYNTH_ADMISSION`) | 0 | 206 | `data/v2/admissions.jsonl`, `docs/v2/DATA_V2.md` s10 |
| Rows rejected | 4,424 | 108 | audit `rejected_rows` |
| Rejected: placeholder with no neutral wording | 4,355 | 37 | audit `rule_counts` |
| Rejected: invented timeline / completed action / credentials / unresolved placeholder | 50 / 1 / 1 / 9 | 50 / 1 / 1 / 9 | same |
| Overlength (over 512 tokens) dropped | 8 | 10 | same |
| Placeholder substitutions applied (v2 only) | 0 | 9,638 | audit `rule_counts` `substitute_*` |
| Rows with the double-determiner defect (both runs) | 1,771 | 2,015 | `docs/v2/DATA_V2.md` s8 |
| train / val / test rows | 17,701 / 2,477 / 2,270 | 21,132 / 2,753 / 3,085 | `data/splits.json`, `data/v2/splits.json` |
| Groups (MiniLM, 0.86 average linkage, seed 42) | 4,462 | 4,992 | same |
| Intents near collapse (one group over 50 percent) | 1 | 0 | audit `near_collapse_intents` |
| Nearest cross-split cosine within intent: p50 / p95 / max | 0.8923 / 0.9387 / 0.9708 | 0.8959 / 0.9427 / 0.9825 | audit `nearest_cross_split_cosine` |
| Group-id and normalized-instruction intersections | empty | empty | audit `cross_split` |
| Split sha256 (train / val / test, first 12) | 307c59da3503 / b5f2e52d0d32 / ef864aace401 | 26ab60319908 / 6f35948d7c03 / 70e1de8594f7 | same |
| Train cap at load time | 8,000 | 8,000 corpus rows plus 206 admissions exempt (decision 4) | `configs/train-t4.yaml`, `data/prepare.py cap_train_rows` |

Per intent, corpus rows kept (v1 -> v2): cancel_order 66->996, change_order 942->997, change_shipping_address 973->973, check_cancellation_fee 950->950, check_invoice 926->999, check_payment_methods 942->999, check_refund_policy 889->960, complaint 887->999, contact_customer_service 151->997, contact_human_agent 884->998, create_account 933->997, delete_account 908->993, delivery_options 564->963, delivery_period 973->997, edit_account 739->1000, get_invoice 977->998, get_refund 857->997, newsletter_subscription 979->998, payment_issue 837->999, place_order 934->994, recover_password 435->994, registration_problems 924->999, review 961->996, set_up_shipping_address 944->997, switch_account 969->983, track_order 962->993, track_refund 942->998

Sources: [`data/audit.json`](data/audit.json), [`data/v2/audit.json`](data/v2/audit.json),
[`data/splits.json`](data/splits.json), [`data/v2/splits.json`](data/v2/splits.json). The v1 files
are untouched; v2 writes only under `data/v2/` and `data/processed/v2/`.

## 4. Evaluation design and results

Two evaluations answer two different questions, and they disagree on purpose.

**The headline is a sealed challenge set**, because the assignment's question is whether the model
is a better support assistant, not whether it writes like the corpus. 54 items,
[`eval/challenge.jsonl`](eval/challenge.jsonl), sha256 `76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6`,
two per intent, one ordinary and one hard. Each card carries the query, the facts the assistant does
and does not have, the acceptable actions, and the lines that make an answer a critical failure.
The 54 cards were drafted from the intent list, edited and approved by the repository owner at
2026-09-06 12:50 IST (all 54 approved unchanged), and sealed one minute later into
[`eval/SEAL.json`](eval/SEAL.json). No tuned-model answer existed before the seal, and
[`eval/blind.py`](eval/blind.py) refuses to build a sheet against a mismatching hash.

**Protocol.** Both models answered through the same Ollama HTTP path, greedy decoding, seed 42,
2,048-token context, 256 new tokens: `ghl-base` Q8 against `ghl-support` Q8, the exact artifacts a
grader can download. Answers were shuffled into A/B columns; model identity lived only in
`eval/results/blind-key.json`, which is gitignored and was read by
[`eval/score.py`](eval/score.py) only after the sheet was final. The rubric is
[`eval/RUBRIC.md`](eval/RUBRIC.md): a pass addresses every request, gives a step the customer can
actually take, and admits what the assistant does not know; a critical failure is invented policy,
invented status, a completed action, a stated timeline, or a request for a password or full card
number, and a critical failure cannot also be a pass.

**Scoring provenance, and the caveat that comes with it.** The plan called for a single human to
blind-score all 108 answers by hand. That is not what happened. **The sheet was LLM-judged with
adjudication, not human-scored:** Gemini 3.8 Flash scored every card twice with A and B swapped
(self-agreement 107/108 on critical, 102/108 on pass, 49/54 on preferred), then a second model read
all 54 cards against `RUBRIC.md` with the Flash reason line beside each, resolved the 12 cards where
Flash disagreed with itself, and changed 13 fields on 11 cards. Every change and its rubric reason is
in [`eval/results/llm-judge/adjudication.json`](eval/results/llm-judge/adjudication.json) and in the
`notes` column of the scored sheet. An LLM judge is harsher than a person on "no actionable next
step", so both pass rates are probably a few points low; the direction is not in doubt, and the eight
tuned critical failures are invented facts anyone can check in
[`eval/results/failures.jsonl`](eval/results/failures.jsonl). Full account in
[`docs/RESULTS.md`](docs/RESULTS.md) section 2.

### Result

| | base (`ghl-base` Q8) | tuned (`ghl-support` Q8) |
|---|---:|---:|
| pass rate (n = 54) | **16 / 54 = 29.6%** | **7 / 54 = 13.0%** |
| critical failures | 2 | 8 |

| difference | 95% interval (paired bootstrap, 2,000 draws, seed 42) | preferred: tuned / tie / base | verdict |
|---:|---:|---:|---|
| **-16.7 points** | [-33.3, +0.0] | 18 / 7 / 29 | **negative** |

| kind | n | base pass | tuned pass | diff | base critical | tuned critical |
|---|---:|---:|---:|---:|---:|---:|
| hard | 27 | 22.2% | 11.1% | -11.1 | 1 | 5 |
| ordinary | 27 | 37.0% | 14.8% | -22.2 | 1 | 3 |

Source: [`eval/results/summary.jsonl`](eval/results/summary.jsonl),
[`eval/results/scores.jsonl`](eval/results/scores.jsonl). Per-intent breakdown in
[`docs/RESULTS.md`](docs/RESULTS.md).

The tune is not uniformly worse. It wins outright on `edit_account`, `switch_account`,
`get_invoice`, `place_order` and `track_refund` -- self-serve navigation questions where Bitext's
"log in, open Settings" shape is the correct answer. It loses wherever the query asks for a fact the
assistant cannot know: fees, policy windows, support hours, delivery options, payment methods. That
split is the finding.

### v2 result on the fresh sealed set

Same protocol, second sealed set ([`eval/challenge_v2.jsonl`](eval/challenge_v2.jsonl), sha256 in [`eval/SEAL_v2.json`](eval/SEAL_v2.json), 54 items, two per intent, drafted by a model that had read no v1 result, checked against the v1 set for shared six-grams and cosine, approved and sealed at 18:12 IST on 7 September before a single v2 row was generated). The v2 tune is checkpoint-250 of the Colab T4 run, selected on dev by the pre-registered rule ([`docs/SELECTION.md`](docs/SELECTION.md)), served as `ghl-support` Q8 through the same Ollama path; v1's artifacts are archived under `artifacts/v1/` and served as `ghl-support-v1`.

| | base (`ghl-base` Q8) | v2 tune (`ghl-support` Q8) |
|---|---:|---:|
| pass rate (n = 54) | **8 / 54 = 14.8%** | **12 / 54 = 22.2%** |
| critical failures | 6 | 12 |
| difference, interval, verdict | | **+7.4** points, [-7.4, +22.2], **negative** |

By kind, per intent, the old set as a contaminated secondary number, the judge-drift caveat and the file hashes are in [`docs/RESULTS.md`](docs/RESULTS.md), v2 section. Gate 2 asked for a positive verdict plus ordinary-item passes at or above base; the guard held (8 against 5) and the verdict did not.

### Why: it learned the voice and unlearned the admission

Counts over the challenge answers and the training split:

| | base answers (54) | tuned answers (54) | training split (17,701 rows) |
|---|---:|---:|---:|
| admits a missing fact | 14 | **0** | 15 |
| refuses outright | 5 | **0** | 0 |
| contains "I'm on it" | 0 | 11 | 250 |
| contains "I'm on the same wavelength" | 0 | 13 | 43 |
| contains "Rest assured" | 0 | 9 | 3,632 |

The first two rows are phrase families counted in [`docs/RESULTS.md`](docs/RESULTS.md); the last
three are exact substring counts over `eval/results/base-challenge-raw.jsonl`,
`eval/results/tuned-challenge-raw.jsonl` and `data/processed/train.jsonl`. Widening or narrowing the
admission patterns moves the base and training counts by a few either way. The tuned column stays at
zero under every variant.

One epoch was enough to remove the base model's admission habit entirely, because the corpus has
almost no example of it: 3,632 training rows say "Rest assured" and 15 say the assistant does not
know something.

### Three failure cases

Full text of both answers, the rubric reason and the training rows behind each are in
[`docs/FAILURES.md`](docs/FAILURES.md):

- [`ch-017`](docs/FAILURES.md), support hours and phone numbers. The tuned model invents a weekly
  schedule and two phone numbers. Cause: 849 of 1,000 `contact_customer_service` rows were rejected
  for carrying a phone or hours placeholder, so the intent nearly vanished while the confident frame
  was learned everywhere else.
- [`ch-025`](docs/FAILURES.md), delivery options. The tuned model invents four delivery tiers, two
  delivery windows and an in-store pickup in Pune. Cause: `delivery_options` responses in Bitext are
  enumerated lists; cleaning stripped the windows out of the training rows and the model put them
  back from its own prior.
- [`ch-001`](docs/FAILURES.md), order cancellation. Not a critical failure, but a pass the base model
  had and the tune lost: it echoes the request, says "contact support" with no step, and adds "Rest
  assured". Cause: `cancel_order` kept 64 train rows out of 998, none of which describe the
  cancellation steps, so the model borrows a cross-intent deflection.

The fix is data, not another checkpoint: substitute rather than reject the phone/hours/URL/policy
placeholders, add a few hundred "admit and redirect" rows, and add refusal rows for out-of-scope
asks. `docs/FAILURES.md` closes with those three in order of expected effect.

### Secondary: held-out Bitext reference metrics

Same 270-row group-disjoint sample on every side, 270 distinct groups, 2,000 group-bootstrap
resamples, seed 42, references in
[`eval/results/test-sample-refs.jsonl`](eval/results/test-sample-refs.jsonl):

| | base (Q8, Ollama) | tuned (bf16 adapter) | tuned (Q8, served) | tuned Q8 minus base Q8, 95% CI |
|---|---:|---:|---:|---|
| ROUGE-L F1 mean | 0.2153 | 0.3659 | **0.3667** | +0.1515 [+0.1380, +0.1662] |
| MiniLM cosine mean | 0.6741 | 0.8315 | **0.8288** | +0.1547 [+0.1335, +0.1766] |
| truncated at 256 tokens | 10.4% | 2.6% | 2.2% | |
| mean generated tokens | 107.8 | 91.8 | 91.8 | |

Source: [`eval/results/tuned-q8-test-auto.json`](eval/results/tuned-q8-test-auto.json),
[`eval/results/base-test-sample-auto.json`](eval/results/base-test-sample-auto.json); method and the
fp16-versus-Q8 drift check in [`docs/EXPORT.md`](docs/EXPORT.md). Base on the full 2,270-row test
split: ROUGE-L 0.226, cosine 0.711
([`eval/results/base-test-auto.json`](eval/results/base-test-auto.json)).

Read this as what it is. Reference similarity measures whether the model writes like Bitext, and it
does, by 15 ROUGE points, on the same serving path as the base, so precision and runtime do not
explain the gain. It says nothing about correctness or safety. A submission that reported only this
table would look like a clear win. Q8 quantisation costs nothing measurable: fp16 and Q8 sit within
0.002 on both metrics.

### Checkpoint selection on dev

`checkpoint-400` was chosen on `eval/dev.jsonl` alone -- 13/54 passes with 20 critical failures,
against 12/18 for steps 300 and 500 and 9/14 for 250. The same pattern, more fluency and more
invention with more training, appears on the challenge set.
[`docs/SELECTION.md`](docs/SELECTION.md) records that the pick is weak; the challenge result does not
change it and it was not revisited, because revisiting it against the challenge set would have
destroyed the seal.

## 5. Exact prompt template, and how to load and run

Training and direct Transformers inference use the tokenizer's native Qwen2.5 ChatML template.
Ollama uses the equivalent template in [`serve/Modelfile.base`](serve/Modelfile.base). The system
turn appears exactly once. Running `uv run python train/render.py` produces this rendered sample
text before printing token IDs:

```text
<|im_start|>system
You are a customer support assistant. Answer clearly and helpfully. Do not invent company policy, account details, or completed actions. Ask for missing context when needed. Never ask for passwords or full payment card details.<|im_end|>
<|im_start|>user
I forgot my password and cannot sign in. What should I do?<|im_end|>
<|im_start|>assistant
Use the password-reset option on the sign-in page. If the reset message does not arrive, check your spam folder and contact support without sharing your password.<|im_end|>
```

The system text is [`configs/prompt.txt`](configs/prompt.txt) and is applied once, as the `system`
turn, for training and for both serving routes.

### Get the weights

Everything is on the Hub at <https://huggingface.co/seekingtroooth/ghl-support-qlora-t4>: the LoRA
adapter, the merged fp16 model, both Q8 GGUFs and the manifest. From a clone, fetch and verify them
against the recorded hashes:

```sh
uv run python tools/fetch_artifacts.py --manifest artifacts/manifest.json          # all 22 files
uv run python tools/fetch_artifacts.py --manifest artifacts/manifest.json --target serve   # GGUFs only
uv run python tools/check_artifacts.py --manifest artifacts/manifest.json
```

### Route 1: Ollama HTTP endpoint (the served artifact, and what the evaluation scored)

```sh
ollama create ghl-base    -f serve/Modelfile.base    # base Q8
ollama create ghl-support -f serve/Modelfile         # tuned Q8
ollama serve                                          # omit if the desktop service runs
```

```sh
curl --fail-with-body http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ghl-support","messages":[{"role":"user","content":"I forgot my password and cannot sign in. What should I do?"}],"temperature":0,"max_tokens":256,"stream":false}'
```

[`serve/Modelfile`](serve/Modelfile) bakes in the system prompt and the evaluated decoding
parameters (temperature 0, top_p 1.0, repeat penalty 1.0, 256 new tokens, 2,048 context, seed 42,
stop `<|im_end|>`), so a bare request like the one above reproduces the configuration section 4
scored. Send your own `system` turn to override it.

The wrapper exposes the same route, a single query, and a fixed safety check that fails on an empty
answer or on language asking the customer for a password, full card detail, PIN or CVV:

```sh
uv run python serve/inference.py --backend ollama --model ghl-support --self-test
uv run python serve/inference.py --backend ollama --model ghl-support \
  --query "How do I update the shipping address on an order?"
```

### Route 2: merged fp16 weights through Transformers

`artifacts/merged/` is the pinned base with the adapter merged in. The wrapper loads it
automatically when it is present, on CPU or MPS, with no Ollama and no bitsandbytes:

```sh
uv run python serve/inference.py --backend transformers --device mps \
  --query "How can I reset my password?"
```

### Route 3: LoRA adapter on the pinned base

Loads 74 MB of adapter onto the base you already have cached. Verified on this Mac:

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen2.5-1.5B-Instruct"
REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
ADAPTER = "artifacts/adapter"  # fetched by tools/fetch_artifacts.py, above

tokenizer = AutoTokenizer.from_pretrained(ADAPTER)
model = AutoModelForCausalLM.from_pretrained(BASE, revision=REVISION, dtype="auto")
model = PeftModel.from_pretrained(model, ADAPTER, is_trainable=False)
model.to("mps").eval()  # or "cuda" / "cpu"

system = open("configs/prompt.txt", encoding="utf-8").read().strip()
messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": "I forgot my password and cannot sign in. What should I do?"},
]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
with torch.inference_mode():
    output = model.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=256,
        eos_token_id=[tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|im_end|>")],
        pad_token_id=tokenizer.eos_token_id,
    )
print(tokenizer.decode(output[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
```

The same route through the evaluation harness, which writes a checkable JSONL instead of printing:

```sh
uv run python eval/run.py --model tuned --backend transformers --split dev --device mps \
  --adapter artifacts/adapter --output eval/results/dev-adapter-raw.jsonl --check-complete
```

The three routes do not produce byte-identical text. `artifacts/adapter` on a bfloat16 base,
`artifacts/merged` in fp16, and the Q8 GGUF are three rounding paths, and greedy decoding can pick a
different token at a tie. Measured on the first ten dev items: merged fp16 against tuned Q8 agree on
8 of 10 exactly; adapter against merged agree on 3 of 10. One item, `dv-008`, changes rubric class
(critical fail to plain fail) across the precision change; the other nine keep their class. Numbers
and cause in [`docs/EXPORT.md`](docs/EXPORT.md). **The scored artifact is the Q8 GGUF served by
Ollama**, so route 1 is the one that reproduces section 4.

## 6. Serving and measured latency/throughput

Both benchmarks come from [`serve/bench_results.json`](serve/bench_results.json), measured on an
Apple M1 Pro with 16 GiB unified memory, macOS 26.5 arm64, and Ollama 0.24.0: base at
2026-09-05 23:21:44 IST, tuned at 2026-09-06 13:06:09 IST. Each run unloads the model, times one
cold request, runs five unreported warmups, then sends the first 30 rows of `eval/dev.jsonl`
serially with greedy decoding and a 256-new-token cap.

| Model | Requests | Failures | p50 end-to-end | p95 end-to-end | Mean generation | Total throughput | Cold load | Cold first request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ghl-base` Q8_0 | 30 | 0 | 1,348 ms | 3,337 ms | 66.79 tok/s | 60.69 tok/s | 894 ms | 2,892 ms |
| `ghl-support` Q8_0 | 30 | 0 | 1,428 ms | 2,942 ms | 65.86 tok/s | 60.89 tok/s | 2,296 ms | 4,262 ms |

The base window generated 2,687 tokens in 44.272 seconds; the tuned window 2,927 tokens in 48.071
seconds. Generation rate is Ollama's `eval_count / eval_duration`; total throughput is generated
tokens over wall time across the 30 measured requests, so it includes prompt evaluation and request
overhead. Method in [`docs/SERVING.md`](docs/SERVING.md).

The two models cost the same to run: identical GGUF size, generation rate within 1.4%, total
throughput within 0.3%. The adapter changes what the model says, not what it costs to serve. The
latency differences are answer length, not speed. The tuned model's answers are more uniform: over
the same 30 prompts its shortest answer is 38 tokens against the base model's 13, and its longest
227 against 225, which raises p50 and lowers p95 at the same time. The same uniformity shows up as a
truncation rate on the Bitext sample falling from 10.4% to 2.2%. Cold load is the one real gap,
2,296 ms against 894 ms, and it is a one-time cost per model residency.

These are single-user, single-request local numbers on a laptop. They are not a concurrency or
capacity claim; nothing here was measured above concurrency 1. In the separate 54-item base
development run, [`eval/results/base-dev-raw.jsonl`](eval/results/base-dev-raw.jsonl) records two
answers that reached the 256-token cap, `dv-033` and `dv-041`, so the cap is an observed truncation
risk and not only a configured limit.

## 7. Real vs cut for time, and production trade-offs

### What was cut, and what it costs

The plan of record is [`docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md`](docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md).
These are its cuts, each one a real reduction in evidence:

| Cut | Full version | What shipped | Cost to the claim |
|---|---|---|---|
| Challenge set size | 108 sealed queries | 54, two per intent (one ordinary, one hard) | Wider bootstrap interval. At n = 54 the interval is [-33.3, +0.0]; a 5-point effect either way would not have been separable. |
| Challenge authorship | Owner authors all queries before any output exists | Drafted from the intent list, owner edited and approved all 54 unchanged, hashed before any tuned answer was generated | Query wording carries the drafter's idea of a hard case. The seal timing is the guarantee that matters, and it held. |
| Blind scoring | One human scores 108 answers by hand | LLM judge, two passes with A/B swapped, then model adjudication of all 54 cards against the rubric | The largest cut in the submission. See below. |
| LLM judge scope | Local Llama-3.1-8B, order-swapped, on challenge and the 270 Bitext rows | Automated reference metrics only on Bitext; the judge moved onto the challenge set instead | The Bitext side has no judge, only ROUGE-L and cosine, which measure style not correctness. |
| fp16 scored pass | Score fp16 and Q8 separately on both sides | Score only the served Q8 pair; ship fp16 merged weights and spot-check drift on 10 dev answers | Drift is characterised on 10 items, not 54. One of the 10 changed rubric class. |
| Epoch comparison | One epoch, optionally two, pick on dev | One epoch; checkpoints every 100 steps plus the halfway mark, four of them scored on dev (250, 300, 400, 500) | No two-epoch comparison. `docs/SELECTION.md` suggests it would have made things worse, not better. |
| Threshold calibration | 100 labelled candidate pairs | 40 pairs in a 30-minute box | Weaker leakage argument, quantified: recall 0.46 at the chosen threshold, 3,693 cross-split pairs above it. |
| Training rows | Full 17,701-row grouped split on a cloud GPU | 8,000-row group-aware cap, one epoch, on this Mac | The corpus problem in section 4 is a coverage problem, and a larger sample of the same corpus would not have added the missing "I don't know" rows. Untested. |
| Fresh-clone check | Clone on a clean machine | A clone into a temp directory on this Mac with a fresh venv, serving steps only; run 2026-09-06, transcript in [`docs/FRESH_CLONE_TRANSCRIPT.md`](docs/FRESH_CLONE_TRANSCRIPT.md) | Same OS and same machine, so it proves the instructions, not portability. It also caught a README defect (two tests failed after a serve-only install), fixed since. |
| Concurrency bench | Concurrency 4, labelled optional | Serial only | No concurrency number at all. Section 6 says so. |
| Second base-model arm | 14B-class base trained and scored alongside 1.5B | 14B second arm: considered, not run — reasons in section 2 | Untested whether a larger base changes anything; section 2's argument is that the failure is data-shape, not capacity. |
| Loom | 4 minutes | 3 minutes, 5 shots; **not recorded as of 2026-09-06** | Nothing material once recorded. |

### Three disclosures that matter more than the table

**The blind sheet was not human-scored.** The plan put a human in the loop for the one number the
whole submission turns on, and that step was replaced under time pressure by an LLM judge with model
adjudication, described in full in section 4 and in `docs/RESULTS.md` section 2. Both judges were
blind to model identity and the key was read only by `score.py` after the sheet was final, so the
comparison is not contaminated, but a machine applied the rubric. Every verdict, including the 13
adjudicated changes, is written down and checkable, which is the mitigation on offer. If the
adjudication is wrong it is wrong symmetrically: the same rubric lines were applied to A and B
without knowing which was which.

**The challenge set was drafted by an assistant.** The 54 cards were drafted from the intent list,
then edited and approved by the repository owner in one session before any tuned output existed, and
sealed at 2026-09-06 12:51 IST with a recorded hash. Approval preceded generation, which is the
property that makes the set held-out. It does not make the set neutral about what "hard" means.

**Compute.** The assignment says free compute is sufficient and not to spend money on this. A Colab
Pro subscription was bought for this work and then **not used**: no training ran on it. The shipped
adapter was trained on the local Apple M1 Pro through MPS in 2 h 47 m, and the config that produced
it, [`configs/train-t4.yaml`](configs/train-t4.yaml), is the 8,000-row variant sized for a free
Colab or Kaggle T4. Nothing in this repository requires paid compute to reproduce.

### v2 disclosures

- **The admission rows were written by a model, not a person.** A stateless `grok-4.5-build` call authored them from the intent list, a specification and a scenario sketch; Gemini 3.8 Flash was the planned author and was replaced after five generator runs died on the training machine (decision 11). A second stateless call reviewed every row against eight checks; an automated leakage check quarantined 53. 206 rows reached train against a 440 target; nothing was edited to close the gap (decision 10).
- **Two lint rules were relaxed for two intents** so that `check_cancellation_fee` could say fee or charge and `recover_password` could say password (decision 12). Every other price and credential word still rejects.
- **Checkpoint selection on dev used a Grok judge**, not the hand pass v1 used, so v2 dev counts are lower than v1's and not comparable; only the ordering was used (`docs/SELECTION.md`).
- **The judge drifts.** v1's base answers on the old set scored 16 of 54 on 6 September and 4 of 54 when rescored today beside the v2 answers. Every number in this README is a paired comparison inside one scoring session; v1 and v2 pass rates are not on one scale.
- **The held-out Bitext reference metrics were not recomputed for v2.** The v1 sample draws from the v1 test split, whose ids can be v2 training ids; a fresh group-disjoint sample from the v2 test split was planned and cut for time.
- **Two cells of the executed Colab notebook errored** (a smoke-run cap that could not exempt the admission rows, and a missing `PYTHONPATH` for the dev-answer runner). Neither touched the training or the gate; both are fixed in the source notebook, and the executed copy is committed as it ran, with a note.
- **Two training runs were started and one was scored.** A first Colab VM was reclaimed mid-epoch; the second completed and was gated. A Mac `mps` insurance run of the same config was stopped at step 325 once the Colab run was clean (decision 14).

### What is real

Every number in this README comes from a file in this repository, cited next to it. What exists and
was run: a pinned dataset with deterministic cleaning and frozen split hashes, a training run with a
resume proof, a checkpoint selection with all four candidates' scores written down, a sealed
evaluation set generated after the seal, a served HTTP endpoint, and a benchmark script that fails
rather than silently reporting a partial run. Section 8 is the path from a clone to those numbers, and
[`docs/FRESH_CLONE_TRANSCRIPT.md`](docs/FRESH_CLONE_TRANSCRIPT.md) is a run of its serving steps
from a fresh clone on the same machine. The verdict is negative and is reported as negative.

### What I would revisit for production

1. **Fix the data before touching the model.** The three changes in `docs/FAILURES.md` are the whole
   job: substitute instead of reject for phone/hours/URL/policy placeholders, which returns ~4,400
   rows concentrated in the two worst intents; add several hundred "I don't have that, here is where
   to get it" rows; add refusal rows for out-of-scope and unsafe asks, of which the corpus has none.
   Bitext alone cannot teach a support model to decline.
2. **Ship the base model, not this tune.** On the evidence here, the honest recommendation is to keep
   `ghl-base` in front of customers and treat the adapter as a register experiment. A tune that
   invents phone numbers is worse than a verbose one that says it does not know.
3. **Put a factuality gate in front of the endpoint.** Even a good tune needs a check that refuses to
   emit a phone number, a date, an order id or a currency amount that did not appear in the request
   or in a retrieved record. That is a serving-layer guard, cheap and independent of the weights.
4. **Retrieval over fine-tuning for facts.** Hours, fees, policy windows and delivery options change
   weekly and belong in a retrieved context, not in weights. Fine-tuning is the right tool for tone
   and format only, which is exactly what it delivered here.
5. **Human evaluation, and more of it.** 54 items were enough to see a 17-point regression, and even
   there the interval's upper bound sits exactly at zero. They are nowhere near enough to certify a
   5-point gain. Production needs a few hundred items, two or three human scorers, and an
   inter-rater number.
6. **A real serving stack.** vLLM or TGI on a GPU with continuous batching, plus concurrency
   benchmarks. The numbers in section 6 are a laptop, one request at a time.

## 8. Reproduce

Run these steps from the repository root in dependency order.

1. Install the locked Python 3.11 serving environment and run the suite:

   ```sh
   uv sync --frozen --extra serve
   uv run pytest -q
   ```

   Two tests skip at this point: the split-leakage check needs the processed splits from step 2,
   and the zero-effect adapter check needs `peft` from the train extra in step 3. Rerun
   `uv run pytest -q` after step 3 for the full suite.

2. Fetch the pinned dataset, build the processed splits, then verify their frozen hashes and
   intersections:

   ```sh
   uv run python data/fetch.py
   uv run python data/prepare.py
   uv run python data/prepare.py --audit-only --strict
   ```

3. Train. The smoke run trains 20 steps, deletes the later checkpoints, resumes from step 10 and
   compares the two loss series, so a match proves resume rather than merely not crashing:

   ```sh
   uv sync --frozen --extra train
   uv run python train/train.py --config configs/train.yaml --smoke --data-dir data/processed
   # off a CUDA machine, add --device mps (or --device cpu)

   # free Colab or Kaggle T4, 8,000 rows (open notebooks/train_colab.ipynb, set CONFIG)
   uv run python train/train.py --config configs/train-t4.yaml

   # the run that produced the shipped adapter: same config on this Mac's MPS device
   uv run python train/train.py --config configs/train-t4.yaml --device mps --run-name local-t4

   # gate the run directory, then plot
   uv run python tools/check_run.py train/runs/local-t4 --max-memory-gb 12
   uv run python train/plot_curves.py train/runs/local-t4
   ```

   `configs/train.yaml` is the same recipe over the full 17,701-row split for a Colab Pro A100 or L4;
   it stops with a message naming `--device mps` if no CUDA GPU is visible. Details and expected wall
   times in [`docs/TRAINING.md`](docs/TRAINING.md).

   **v2 (branch `v2`).** The same recipe over the v2 split, on a free Colab T4, run as a notebook so a
   reviewer can read every cell's output:

   ```sh
   # data: substitution mode, admission rows appended to train, strict audit
   uv run python data/prepare.py --placeholder-mode substitute --out data/v2 --admissions data/v2/admissions.jsonl
   uv run python data/prepare.py --audit-only --out data/v2 --strict
   # the run: notebooks/train_colab.ipynb, executed top to bottom on a free T4 (2026-09-08);
   # the executed copy with outputs is notebooks/v2_colab_run.ipynb
   uv run python train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push
   uv run python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12
   ```

   The admission rows themselves are regenerated with `uv run python tools/admissions.py generate
   --provider grok`, reviewed with `tools/admission_review.py`, then `leakage` and `assemble`
   ([`docs/v2/DATA_V2.md`](docs/v2/DATA_V2.md) section 10 has every count and hash).

4. With the full pinned Hugging Face snapshot available locally, merge the selected adapter and
   convert both models using the pinned llama.cpp checkout. `HF_MODEL_DIR` must point to revision
   `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`:

   ```sh
   HF_MODEL_DIR=~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306
   tools/convert.sh "$HF_MODEL_DIR" artifacts/base-q8.gguf
   # checkpoint-400 is gitignored; artifacts/adapter from the Hub is the same weights
   # (adapter_model.safetensors sha256 1a94ede7..., docs/EXPORT.md)
   uv run python tools/merge.py --adapter train/runs/local-t4/checkpoint-400 --output artifacts/merged
   tools/convert.sh artifacts/merged artifacts/tuned-q8.gguf
   uv run python tools/check_artifacts.py --manifest artifacts/manifest.json --target serve
   ollama create ghl-base    -f serve/Modelfile.base
   ollama create ghl-support -f serve/Modelfile
   ```

5. Run the evaluation harness. Each raw JSONL is appended by ID and can resume safely:

   ```sh
   # base and tuned answers on the dev set and on the sealed challenge set, through Ollama
   uv run python eval/run.py --model base  --backend ollama --split dev       --check-complete
   uv run python eval/run.py --model base  --backend ollama --split challenge --check-complete
   uv run python eval/run.py --model tuned --backend ollama --split challenge --check-complete

   # build the blind A/B sheet; refuses to run against a mismatching challenge hash
   uv run python eval/blind.py --split challenge

   # score the completed sheet and write scores, summary and failures
   uv run python eval/score.py --final --require-complete --sheet eval/results/blind-sheet-scored.csv

   # held-out Bitext reference metrics on the 270-row sample
   uv run python eval/run_sample.py --model tuned --backend ollama \
     --output eval/results/tuned-q8-test-raw.jsonl --check-complete
   uv run python eval/auto_metrics.py --raw eval/results/base-test-sample-raw.jsonl \
     --refs eval/results/test-sample-refs.jsonl --out eval/results/base-test-sample-auto.json \
     --compare eval/results/tuned-q8-test-raw.jsonl --out-compare eval/results/tuned-q8-test-auto.json
   ```

   `eval/score.py` reads `eval/results/blind-key.json`, which is gitignored. Scoring a fresh sheet
   requires regenerating the answers and the key with `eval/blind.py` first.

   **v2 scoring on the fresh sealed set** ([`eval/challenge_v2.jsonl`](eval/challenge_v2.jsonl),
   sealed in [`eval/SEAL_v2.json`](eval/SEAL_v2.json)) uses the same scripts with explicit paths, so
   the v1 results above are never overwritten:

   ```sh
   uv run python eval/run.py --model base  --backend ollama --split challenge --challenge eval/challenge_v2.jsonl --seal eval/SEAL_v2.json --output eval/results/v2/fresh/base-challenge-raw.jsonl  --check-complete
   uv run python eval/run.py --model tuned --backend ollama --split challenge --challenge eval/challenge_v2.jsonl --seal eval/SEAL_v2.json --output eval/results/v2/fresh/tuned-challenge-raw.jsonl --check-complete
   uv run python eval/blind.py --challenge eval/challenge_v2.jsonl --seal eval/SEAL_v2.json --base eval/results/v2/fresh/base-challenge-raw.jsonl --tuned eval/results/v2/fresh/tuned-challenge-raw.jsonl --csv eval/results/v2/fresh/blind-sheet.csv --html eval/results/v2/fresh/blind-sheet.html --key eval/results/v2/fresh/blind-key.json
   uv run python eval/score.py --final --require-complete --sheet eval/results/v2/fresh/blind-sheet-scored.csv --key eval/results/v2/fresh/blind-key.json --scores eval/results/v2/fresh/scores.jsonl --summary eval/results/v2/fresh/summary.jsonl --failures eval/results/v2/fresh/failures.jsonl --n-boot 2000 --seed 42
   ```

6. Reproduce the 30-request serial benchmark and validate all currently manifested artifacts:

   ```sh
   uv run python serve/bench.py --requests 30 --concurrency 1 --check --model ghl-base
   uv run python serve/bench.py --requests 30 --concurrency 1 --check --model ghl-support
   uv run python tools/check_artifacts.py --manifest artifacts/manifest.json
   ```

---

## Developer quickstart

Python is pinned to 3.11 by `.python-version`; the system interpreter is 3.14 and is not used.
Everything runs through `uv run` against the locked environment.

```sh
make sync     # uv sync --frozen --extra serve
make test     # uv run pytest -q
make audit    # uv run python data/prepare.py --audit-only --strict
make eval-base
make bench
```

`bitsandbytes` lives in the `train` extra only. The pinned environment loads and steps an NF4 QLoRA
model on this Apple M1 Pro through MPS; the measured scope and caveats are in
[`docs/LOCAL_QLORA_PROBE.md`](docs/LOCAL_QLORA_PROBE.md). The default `uv sync` and `--extra serve`
also work here.
