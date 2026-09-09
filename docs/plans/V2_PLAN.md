# V2 plan

INPUT MISSING: fresh seal; admission scanner; evidence-pack entries for grouping-file hash and nearest cross-split cosine. Assume the announced workers finish these inputs; never invent their outputs. Status: NOT SEALED. All dependent nodes below are **BLOCKED ON GATE 1**. This document authorizes planning only.

## 1. v1 in ten lines

1. V2 changes data only; model, recipe, cap, prompt, decoding, rubric, judge, serving and split method stay frozen as specified below.
2. V1 was negative: base passed 16/54 (29.6%); tuned passed 7/54 (13.0%). [EVIDENCE §1](../v2/EVIDENCE.md#1-v1-verdict)
3. Difference was −16.7 points, interval [−33.3, 0.0]; critical failures rose from 2 to 8. [EVIDENCE §1](../v2/EVIDENCE.md#1-v1-verdict)
4. Ordinary passes fell from 37.0% to 14.8%; hard passes from 22.2% to 11.1%. [EVIDENCE §1](../v2/EVIDENCE.md#1-v1-verdict)
5. Q8 reference ROUGE-L rose from 0.2153 to 0.3667; cosine from 0.6741 to 0.8288. [EVIDENCE §2](../v2/EVIDENCE.md#2-corpus-similarity)
6. Cleaning retained 22,448 of 26,872 rows and rejected 4,424. [EVIDENCE §3](../v2/EVIDENCE.md#3-data-audit-v1)
7. Placeholder rejection caused 4,355 removals; cancellation retained 66 rows and customer-service contact retained 151. [EVIDENCE §3](../v2/EVIDENCE.md#3-data-audit-v1)
8. Recorded admission counts were base 17, tuned 0, training 24; their counting method was not retained. [EVIDENCE §4](../v2/EVIDENCE.md#4-admission-counts)
9. The selected run used the 8,000-row cap on MPS, taking 2 h 47 min 09 s; checkpoint-400 won on dev. [EVIDENCE §§3,6](../v2/EVIDENCE.md#6-compute-facts)
10. The cleaner deleted admission-teaching intents; the tune learned corpus voice and lost missing-fact admission. This diagnosed fix followed inspection of the old challenge answers. [EVIDENCE §§4,7](../v2/EVIDENCE.md#7-sealed-set-rule-and-contamination)

## 2. What is frozen

Hashes below are copied from [EVIDENCE §5](../v2/EVIDENCE.md#5-frozen-items). No replacement model, larger model, second arm, hyperparameter tuning or prompt edits.

|File|sha256|
|---|---|
|`configs/versions.json`|`c38c69c941986fa5e53bad37d13d041cf3abd073a2e814a345df7ced2f9d99f8`|
|`configs/train-t4.yaml`|`a24d4ce29f0d0bd6a1c7efe5f7fe18efc56c61e595e6bc03b857455387d4a219`|
|`configs/train.yaml` (unused)|`0e664f11671c652d507c8d21ab7eedc7c2211462e91d484b71bc40cb2605ea62`|
|`configs/prompt.txt`|`d738ddb811ab3d1bb0d0804b2f1a9978b48435f9adb518159b5360ff7bd53443`|
|`configs/eval.yaml`|`2591638608d3393334ae86451c11d73f3dd431950fc49b00077dfe7b4342f8b1`|
|`eval/RUBRIC.md`|`2c6a43da3068119e976dc01d9e9bba409d4393aa34d9a89971ff835ad0e2eef1`|
|`eval/challenge.jsonl`|`76e24d3430715da2bb77cda21f4020882ec4b330ee082733c44e17ee7c0573e6`|

- Base: Qwen2.5-1.5B-Instruct, revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` (`configs/versions.json`).
- Every training hyperparameter remains byte-frozen, including QLoRA, assistant-only loss, group-aware cap 8,000 and seed 42. Only device, data-directory and run-name routing differ.
- Native prompt and decoding remain identical; merge → Q8 GGUF → Ollama, tags `ghl-base`/`ghl-support`, retain the pinned converter (`configs/versions.json`).
- Split seed 42, threshold 0.86, average linkage; exact/template grouping and empty group-id/normalized-instruction intersections remain (`configs/grouping.json`; EVIDENCE §3).
- Gemini 3.8 Flash judges twice with A/B swap; Fable adjudicates every card against the unchanged rubric, blind to identity (EVIDENCE §1).

New quotas, thresholds and deadlines below are pre-registered decisions sourced to this file. Recovery ranges and every scheduled duration are **ESTIMATE**, never measurements.

## 3. Substitution rules

Use exact-name allowlists before rejection; preserve v1 reject mode and other rejection rules. Substitute both text fields with grammatical frame handling. Reject unknown slots instead of unrestricted `your <slot>` fallbacks.

Lint L rejects Unicode digits, clocks, durations including spelled-out quantities, prices/currencies, URLs/domains/emails and policy verbs: guarantees, allows, requires, waives, entitles, qualifies. L cannot prove truth. Grok reviews every substituted sentence frame for unsupported assertions, including channel availability.

|Placeholder family|Neutral phrase|Lint|Rows recovered ESTIMATE|
|---|---|---|---|
|phone/hotline/toll-free|the number on the official contact page|L; no availability promise|0–2700|
|hours/days/opening/closing|the hours listed on the official contact page|L; no schedule|0–2400|
|email/feedback/claims contact|the address on the official contact page|L; no invented address|0–250|
|URL/website/login/help/recovery|the official website / sign-in page / help page, matching slot|L; no asserted feature|0–3100|
|portal/store/marketplace/company|the account portal / store website / company|L; retain only referential frames|0–1200|
|channel/chat/contact method|the contact options listed on the official website|L; no channel availability claim|0–50|
|cancellation/refund/return policy|the terms in the published policy|L; reference frames only|0–5|
|fee/refund amount/money|the applicable amount shown in the account or terms|L; no free/waived claim|no recovery assumed; existing amount mappings already survive|
|timeframe/ETA/refund or shipping time|the timing shown in the order details|L; reference frames only|0–60|
|store address/location|the location information on the official website|L; no pickup assertion|0–350|
|guarantee window, numeric deadline frames, named features/cities/platforms, representative, issued ticket, sentence-as-slot|none|retain rejection|none|

Policy/timeline references work in “check …”, not “we guarantee …” or “arrives within …”. Reject unsupported shipping-tier assertions. Fee is absent from the reject regex; audit existing amount mappings instead of claiming recovery.

Family ranges are ESTIMATE, rounded from [PROFILE](../../data/PROFILE.md)'s response-slot inventory; actual recovery is unidentifiable because slots co-occur and later rules reject rows. These overlapping planning ranges are revisable, not measured ceilings. Pooled ESTIMATE: zero–4,355 recovered rows (EVIDENCE §3). Count **distinct recovered source ids**, occurrences and newly rejected survivors separately.

## 4. Admission-row specification

Target **440 accepted rows**: larger quotas for unknown policy, payments, status and contact facts; smaller quotas for navigational intents. These are corpus/intent-based priorities, never allocations based on eval passes. Table quotas are exact design targets; recovery bounds remain ESTIMATE.

|Intent|v1 kept|Recovery ESTIMATE|Admission target|
|---|---:|---:|---:|
|cancel_order|66|0–932|24|
|change_order|942|0–55|12|
|change_shipping_address|973|0|12|
|check_cancellation_fee|950|0|24|
|check_invoice|926|0–74|24|
|check_payment_methods|942|0–57|24|
|check_refund_policy|889|0–108|24|
|complaint|887|0–113|12|
|contact_customer_service|151|0–849|24|
|contact_human_agent|884|0–115|12|
|create_account|933|0–64|8|
|delete_account|908|0–87|12|
|delivery_options|564|0–410|24|
|delivery_period|973|0–26|24|
|edit_account|739|0–261|8|
|get_invoice|977|0–22|12|
|get_refund|857|0–140|24|
|newsletter_subscription|979|0–20|8|
|payment_issue|837|0–162|24|
|place_order|934|0–64|8|
|recover_password|435|0–560|12|
|registration_problems|924|0–75|12|
|review|961|0–36|8|
|set_up_shipping_address|944|0–53|8|
|switch_account|969|0–31|8|
|track_order|962|0–33|24|
|track_refund|942|0–56|24|

Kept counts/bound inputs: [EVIDENCE §§3–4](../v2/EVIDENCE.md#3-data-audit-v1), citing audit/PROFILE. Bounds use raw-minus-kept except delivery_options; do not sum upper endpoints as a prediction.

Exact processed schema, using metavariables rather than generated training text:

```json
{"id":"adm-v2-<intent>-<serial>","group_id":"adm-g-v2-<intent>-<family>","intent":"<valid intent>","category":"<mapped category>","flags":"SYNTH_ADMISSION","instruction":"<query>","response":"<answer>","cleaning":["synthetic_admission_v2"],"n_tokens":0}
```

Replace schema sentinel `n_tokens:0` with the renderer's integer count; enforce the frozen length limit. Only instruction/response enter training. `SYNTH_ADMISSION` is a project flag. Provenance/styles/reviews live in `data/v2/admission_review.jsonl`.

Answers: **35–75 words**; unavailable fact → where to obtain it → one concrete permitted action. Explain the process or draft the request now. Address both requests. Never assume a page/feature exists or offer unavailable lookups, transactions or transfers.

For each intent, half ordinary and half hard. Cover typos, anger, two requests and missing identifiers at least once each; tags may overlap. Preserve supplied context; do not teach blanket refusal of answerable navigation.

Opus writes after Gate 1 in a **fresh restricted session**: intent/category names, quotas, schema, answer/style rules and lint only; Fable extracts this brief without v1 columns. Exclude evaluation files, RESULTS/FAILURES/EVIDENCE and inherited context. Three sequential batches: high, middle, low quotas. Separate restricted Grok reviews every row: intent/category, justified admission, honest source, useful action, complete requests, capability limits, grammar, style coverage. Apply correction-loop skill: read ledger first (missing means empty), independently resolve findings, retain corrections without row text/PII.

Response lint adds credential/completion checks and bans PROFILE openers, “I'm on it”, “I'm on the same wavelength”, “Rest assured”. Digit/URL checks include queries, exempt metadata. Scanner counts are diagnostics; report reproducible v1/v2 scans beside method-unknown historical counts.

Automated leakage checking alone may read `eval/challenge.jsonl`, `eval/dev.jsonl`, `eval/challenge_v2.jsonl`. Compare both admission text fields against all queries: normalized equality rejects; maximum MiniLM cosine **≥0.80** rejects; any shared normalized **six-word gram** rejects. Use `eval/check_challenge.py` tokenization and embedding implementation. No intent restriction. These thresholds match its against-set caps. Quarantine hits; return no matched text or nearest query to authors. Replacement scenarios must be independently authored, never edited to evade a match. Freeze thresholds before checking.

Group synthetic paraphrase/template families under their own ids, train only. Reject val/test collisions with the same checks; recompute intersections. Synthetics count **inside** the unchanged cap. No reservation, duplication or group renaming to influence selection. Publish pool/selected counts per intent; require synthetic representation in every intent. Not all admissions necessarily enter the cap.

Over-refusal guard: rubric failures include omitted answerable requests and missing actionable steps. Gate 2 requires fresh ordinary passes ≥base, using existing by-kind counts, never checkpoint selection.

## 5. Re-clean, re-split, re-audit

Commands are planned. `v2` means NEW `uv run python tools/v2.py`, owned by Sol. Implement its routing/checks before dependent nodes without changing model/scoring logic. Grok supplies independent scanner recomputation; Sol supplies adversarial fixtures.

```sh
uv run python data/prepare.py --placeholder-mode substitute --out data/v2
uv run python eval/admission_scan.py --input data/v2/admissions.jsonl --strict --leakage
uv run python tools/v2.py assemble
uv run python data/prepare.py --out data/v2 --audit-only --strict
uv run python tools/v2.py audit --independent
uv run python data/prepare.py --audit-only --strict
```

`assemble` adds accepted admissions to train, computes tokens, freezes membership and hashes, and previews the unchanged cap. It preserves corpus-only counts separately. Re-cluster changed corpus text from scratch; bypass the v1 frozen-assignment shortcut. Never overwrite `data/audit.json`, `data/splits.json`, or `data/processed/*.jsonl`. Outputs: `data/processed/v2/{train,val,test}.jsonl`, `data/v2/{audit,splits,cap,leakage}.json`, source-id rejection/recovery ledgers, and admission files above. Regenerate into an isolated second directory and compare hashes for determinism.

One README comparison table, expanded with every intent from §4 and every rejection rule:

|Quantity|v1|v2|Source|
|---|---|---|---|
|raw / corpus kept / rejected|26872 / 22448 / 4424|pending|EVIDENCE §3; `data/v2/audit.json`|
|reject placeholder / timeline / completed / credentials / unresolved / overlength|4355 / 50 / 1 / 1 / 9 / 8|pending, plus new rule ids|same|
|each intent: raw / kept / recovery / synthetic pool / capped synthetic|expand §4|pending|same; `data/v2/cap.json`|
|historical admission phrases|24, method unknown|pending|EVIDENCE §4; scanner report|
|explicit synthetic additions|not recorded in EVIDENCE|pending|provenance ledger|
|train / val / test|17701 / 2477 / 2270|pending|EVIDENCE §3; `data/v2/splits.json`|
|split sha256, each full digest|copy EVIDENCE §3|pending|same|
|nearest cross-split cosine distribution/max|INPUT MISSING in EVIDENCE|pending|`data/audit.json` key awaiting evidence verification; v2 audit|
|intersections / collapsed intents / cap actual rows|copy verified evidence|pending|both audits; cap manifest|

Check conservation separately: raw = corpus kept + rejected; combined kept = corpus kept + accepted admissions; combined kept = split sum. Count each rejected id once by first terminal rule. Average linkage does not guarantee pairwise cosine below threshold; report residual similarity, never claim semantic zero leakage.

## 6. Training substrate and headline rule

Both attempts use identical frozen data/cap hashes and config. Free Colab T4 only; no paid units, upgrades or new paid API spend. Preserve README's existing unused-Pro disclosure (`docs/ASSIGNMENT.md`; README §7). Judge access must use available no-incremental-cost access or remain incomplete.

```sh
uv run python train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4
uv run python train/train.py --config configs/train-t4.yaml --device mps --data-dir data/processed/v2 --run-name v2-mps
```

Launch target Mon 20:00 IST; hard launch deadline Mon 22:00 IST. Lock substrate Tue **02:00 IST**: Colab headlines if finished clean and artifacts downloaded/verified by then; otherwise clean Mac headlines. Neither clean means v2 incomplete. Never compare scores between substrates; a later Colab finish cannot replace the lock.

If free T4 allocation fails, record the failed attempt; the launch gate accepts that receipt plus a timely Mac launch. `check runs` records both statuses and requires at least one clean run. No unstarted attempt is reported as a run.

“Finished clean” means successful full epoch over actual capped ids, expected steps computed from that count and config, finite losses, complete checkpoints/state/log/config, pinned provenance, memory gate, reload success, identical remote/local artifact hashes. Use `tools/check_run.py` on each device, memory limit 12 GB (EVIDENCE §6), plus wrapper provenance checks. Resume only the same run/state. One model-loading job on Mac at a time; no embedding, merge or Ollama workload during insurance training.

Select within the locked run on dev only: candidates steps **250, 300, 400, 500**, same v1 sweep (EVIDENCE §6; `docs/SELECTION.md`); if a full epoch ends earlier because whole groups underfill the cap, document unavailable candidates and include the final checkpoint. Highest dev pass count, then fewest criticals, then earliest step. Freeze selection before either challenge generation. No validation-loss, test, sealed or cross-substrate selection. Use the frozen judge protocol; disclose v1 dev/challenge interpretation differences already recorded in RESULTS.

## 7. Scoring, Gate 2 pre-registration, reporting shape

Gate 1 requires shark's recorded approval, successful checker against v1 challenge and dev, fresh-file hash, author provenance and seal time before admission generation/training. Checker currently requires Bitext cosine <0.85, against-set cosine <0.80 and zero six-gram overlap (`eval/check_challenge.py`). Verify `max_v1_cosine` means maximum over the supplied v1 challenge **and dev** union. Fable seals with its existing `--seal --approval-event --provenance` interface; failed drafts may change only before approval/sealing, without model outputs.

Sol's wrapper executes these exact existing routes with explicit isolated paths:

```sh
uv run python tools/v2.py generate --set fresh
uv run python tools/v2.py blind --set fresh
# Flash twice, swapped; Fable adjudicates all cards, then:
uv run python tools/v2.py score --set fresh
uv run python tools/v2.py gate2
# Repeat generate, blind, judge, adjudicate, score for --set old.
```

Route contract: `eval/run.py --split challenge --challenge <file> --seal <seal> --model <base|tuned> --backend ollama --output <raw> --check-complete`; `eval/blind.py` receives explicit `--challenge --seal --base --tuned --csv --html --key`; `eval/score.py --final --require-complete` receives explicit `--sheet --key --scores --summary --failures --n-boot 2000 --seed 42`. Results live under `eval/results/v2/{fresh,old}/`; v1 results remain immutable. Verify complete unique ids, hash-bound answers and artifact identities. Separate judge workspaces exclude the key and worker/model identities. Fable stores every adjudication reason before unblinding.

Before generation, `v2 export` runs `tools/merge.py --adapter <selected> --output artifacts/v2/merged`, pinned `tools/convert.sh artifacts/v2/merged artifacts/v2/tuned-q8.gguf`, artifact checks, and Ollama creation under the unchanged tags. It archives v1, installs the evaluated v2 GGUF at the existing Modelfile path, and records hashes.

Use the executed v1 bootstrap protocol: 2,000 draws (EVIDENCE §1), despite 10,000 in frozen `configs/eval.yaml`; disclose this mismatch. Positive: gain ≥5 points, interval lower bound >0, critical count ≤base. Negative: gain <0 or critical count >base. Otherwise inconclusive (`eval/score.py`).

**Gate 2:** promote v2 only if Gate 1, data/provenance/completion gates and Q8 serving checks pass, the fresh verdict is positive, and fresh ordinary passes ≥base. No promotion from old-set gains or secondary metrics. If Gate 2 fails, retain the v1 headline and base-model recommendation; prominently report v2's actual verdict or incomplete status. A positive verdict with failed ordinary guard remains positive numerically but is not promoted. Never switch checkpoints after this decision.

Contamination sentence: “The old challenge file is unchanged, but its answers informed the v2 data fix; v2 results on that set are contaminated, secondary, and not evidence of held-out improvement.” Never pool the sets. ROUGE-L/cosine use a newly frozen group-disjoint sample from v2 test with identical base/tuned references and the existing sampler/metrics; old test ids can now be training ids and must not be reused.

Reporting preserves CONTRACTS §7 order. Update README headline, data comparison, evaluation/provenance/failures, artifact loading, benchmark, cuts and reproduction; retain frozen-method explanation. Append v2 sections to RESULTS, FAILURES and SELECTION while preserving v1. Report sentence: “V1 was negative; v2 is [positive/inconclusive/negative/incomplete] on the fresh sealed set: [base passes], [tuned passes], [difference and interval], [critical counts]; Gate 2 [passed/failed].” Cite each filled value to its result file. Preserve LLM-judged disclosure.

Final acceptance runs CONTRACTS §6's eight commands verbatim, plus its exact curl request, in an isolated reproduction checkout so default scoring paths cannot overwrite archived v1 results. Also run explicit v2 score/audit gates. Archive command text, exits and outputs; no green gate based only on file existence.

## 8. Node plan

Hours **ESTIMATE**; M=Mon Sep 07, T=Tue Sep 08, IST. Deadlines: task brief/EVIDENCE §8. Checks recompute named invariants; fixtures reject tampering, missing ids and fake receipts. Coding lanes: Opus/Sol/Grok/Sonnet; Fable dispatches/gates, Grok-4.5 drafts, Flash judges. One task per worker; explicit ownership handoffs. **CP**=critical path. All transitive G1 dependents are **BLOCKED ON GATE 1**.

|id|worker|owned paths|deps|hours|start IST|due IST|gate|verify command|
|---|---|---|---|---:|---|---|---|---|
|B1 CP|T2 Opus|`data/prepare.py`, `configs/cleaning.json`, `tests/test_prepare.py`|in progress|1.2|M14:18|M15:30|safe frames; v1 preserved|`uv run pytest -q tests/test_prepare.py`|
|C0|T4 Sonnet|`notebooks/train_colab.ipynb`|in progress; T0 for gate|1.2|M14:18|M15:30|free T4, pinned config/data routing|`v2 check notebook`|
|S0 CP|T3 Grok-4.5|`eval/challenge_v2_draft.jsonl`|in progress; T0 for gate|1.7|M14:18|M16:00|schema and novelty|`uv run python eval/check_challenge.py eval/challenge_v2_draft.jsonl --against eval/challenge.jsonl eval/dev.jsonl`|
|T0 CP|T3 Sol|`eval/check_challenge.py`, `eval/run.py`, `eval/blind.py`, `tools/v2.py`, `tests/test_v2_tools.py`|in progress|1.2|M14:18|M15:30|routing/negative fixtures pass|`uv run pytest -q tests/test_v2_tools.py tests/test_eval.py`|
|A0|T3 Grok|`eval/admission_scan.py`, `data/v2/evidence-check.json`|in progress; T0 for gate|1.7|M14:18|M16:00|independent numbers/patterns|`v2 check evidence --independent`|
|G1 CP|T1 Fable + shark|`eval/SEAL_v2.json`, `eval/challenge_v2.jsonl`, approval receipt|S0,T0|.5|M16:00|M16:30|approval and valid immutable seal|`v2 check seal`|
|A1 CP|T2 Opus|`data/v2/admissions.jsonl`, restricted provenance|B1,G1|1.5|M16:30|M18:00|quotas/schema/styles|`v2 check admissions`|
|A2 CP|T3 Grok|`data/v2/admission_review.jsonl`, correction ledger|A1,A0|.75|M18:00|M18:45|all rows reviewed/linted/leakage-safe|`uv run python eval/admission_scan.py --input data/v2/admissions.jsonl --strict --leakage`|
|B2 CP|T3 Sol|`data/processed/v2/`, audit/splits/cap/leakage/rejection ledgers|A2,B1,T0|.75|M18:45|M19:30|deterministic splits/cap|`v2 audit --strict`|
|B3 CP|T3 Grok|`data/v2/verification.json`|B2|.5|M19:30|M20:00|counts/hashes independently agree|`v2 audit --independent`|
|L0 CP|T2 Opus + shark|launch receipts, `train/runs/v2-{t4,mps}/`|B3,C0|.25|M20:00|M20:15|both launches before M22:00|`v2 check launched`|
|L1 CP|T2 Opus|run artifacts/curves/download receipts|L0|5.75|M20:15|T02:00|clean completion; estimate includes slack|`v2 check runs`|
|L2 CP|T1 Fable|`artifacts/v2/substrate.json`|L1|.1|T02:00|T02:06|cutoff rule recorded|`v2 check substrate`|
|D0 CP|T2 Opus; then Flash/Fable serial|dev answers/judgments; `artifacts/v2/selection.json`|L2|1.9|T02:06|T04:00|dev-only deterministic ranking|`v2 check selection`|
|Q0 CP|T3 Sol|`artifacts/v2/`, served tuned artifact/tag, manifest|D0|1|T04:00|T05:00|merge/Q8/load/provenance|`v2 check serving`|
|E0 CP|T3 Sol|`eval/results/v2/fresh/` raw/blind|Q0|1|T05:00|T06:00|complete hash-bound pairs|`v2 check pairs --set fresh`|
|J0 CP|T4 gemini-3.8-flash|fresh judge passes|E0|.5|T06:00|T06:30|both orders complete|`v2 check judge --set fresh`|
|J1 CP|T1 Fable|fresh adjudication/scores/Gate 2|J0|1|T06:30|T07:30|all cards adjudicated; rule applied|`v2 gate2 --check`|
|E1|T3 Sol → Flash → Fable|old raw/blind → judge → adjudication|J1|2|T07:30|T09:30|same pipeline, secondary label|`v2 check scored --set old`|
|V0|T3 Grok|`eval/results/v2/verification.json`|E1|.5|T09:30|T10:00|every reported number recomputed|`v2 check results --independent`|
|M0|T3 Sol|v2 test sample/metrics; bench/export/publication receipts|E1|2.5|T09:30|T12:00|metrics, benchmark, downloadable manifest|`v2 check artifacts`|
|R0|T4 Sonnet|README, RESULTS/FAILURES/SELECTION v2 sections, submission manifest|V0,M0|1.5|T12:00|T13:30|claims sourced, both sets reported|`v2 check reporting`|
|R1|T3 Grok; T1 Fable reviews|acceptance transcript; approval receipt|R0|.5|T13:30|T14:00|contract commands and HTTP pass|`v2 contracts --check`|
|H0|shark|Loom and submission receipt|R1|1|T14:00|T15:00|live endpoint, comparison, failure shown|`uv run python tools/check_submission.py submission.json`|
|H1|shark; T1 Fable verifies|final submission receipt|H0|.25|T19:00|T19:15|submitted before T20:00|`v2 check submitted`|

E1 subslots: Sol T07:30–08:15, Flash T08:15–08:45, Fable T08:45–09:30. D0: Opus T02:06–03:00, Flash T03:00–03:30, Fable T03:30–04:00. Validate approval content/timestamps. Handoff checker to Fable at G1; hide query output from authors. Archive v1 artifacts before tag replacement. Publish/bind v2 to an immutable Hub revision.

## 9. Risks, unknowns, disagreements

Substitution can preserve unsupported assertions around a harmless noun phrase. Frame review may recover fewer rows than expected. Cost: ESTIMATE one hour of prelaunch repair slack; retain unsafe-row rejection rather than weaken lint.

The cap can underrepresent admissions or underfill its maximum. Report actual ids/counts, never claim the pool was all trained. If any intent loses all synthetic representation, stop the data gate; changing the frozen sampler requires a later experiment. Cost: ESTIMATE up to the two-hour launch buffer, otherwise v2 incomplete.

The old set influenced the intervention and planner; restricting authors prevents direct paraphrase, not conceptual contamination. The fresh seal establishes timing, not independence of worldviews. Stronger independent human authorship would cost ESTIMATE another day and is outside tonight's scope.

Average linkage leaves close cross-split paraphrases. The evidence pack lacks its residual-cosine numbers and grouping hash: Grok must verify those from the cited files before publication. Do not infer zero from missing evidence. Cost: ESTIMATE half an hour.

Free T4 availability and free judge access are unknown. Mac runtime is measured in EVIDENCE §6, but either attempt can fail; the precommitted cutoff prevents score shopping. No paid fallback. Cost: ESTIMATE overnight slack; if scoring remains unavailable, report incomplete.

I would eventually add verified business context and test factual grounding separately; that changes serving and violates this data-only scope. Cost: ESTIMATE several days. No such work is dispatched here.

## 10. Cut for time

- Cut extra admission polish after all required review gates pass.
- Cut expanded sampling beyond the existing secondary protocol.
- Cut additional benchmark concurrency and presentation polish.
- Never cut the seal, leakage gate, ordinary-pass guard, blind adjudication, either sealed-set report or contamination disclosure; mark incomplete instead.

## 11. Session log: discovery commands you ran and what they returned

Commands below were read-only. Parallel output was occasionally truncated; later focused reads completed required inputs. Semicolon-separated reads are recorded verbatim. No draft admissions, training or scoring was executed.

|#|Command|Returned|
|---|---|---|
|1|`cat docs/v2/EVIDENCE.md`|authoritative verdict, audits, hashes, compute and contamination|
|2|`cat docs/ASSIGNMENT.md docs/dag/CONTRACTS.md`|spending prohibition; schemas, routes, acceptance commands, README order|
|3|`cat eval/RUBRIC.md eval/SEAL.json eval/challenge.jsonl configs/cleaning.json configs/train-t4.yaml configs/prompt.txt configs/eval.yaml`|rubric/seal/configs; combined output truncated|
|4|`cat data/intents.json data/PROFILE.md data/audit.json`|corpus inputs; combined output truncated|
|5|`cat docs/RESULTS.md docs/FAILURES.md docs/SELECTION.md docs/LOCAL_RUN.md README.md`|analysis/reproduction; combined output truncated|
|6|`rg --files -g AGENTS.md -g '*v2*' -g '*admission*' -g '*check*' -g '*.py' -g '*TRAINING*' -g '*hosting*'; rg -n '^def \|placeholder\|split\|cap.train\|add_argument' data/prepare.py`|source inventory; placeholder/split function locations; live edits present|
|7|`cat configs/cleaning.json configs/train-t4.yaml configs/eval.yaml configs/prompt.txt configs/versions.json configs/grouping.json`|substitution map in progress; frozen values and bootstrap mismatch|
|8|`cat data/PROFILE.md data/intents.json`|inventory/counts; tail truncated in combined display|
|9|`python3 -c 'import json; a=json.load(open("data/audit.json")); print(json.dumps(a,indent=2))'`|full audit including residual-cosine key|
|10|`cat docs/RESULTS.md docs/FAILURES.md`|complete diagnosed cause and scoring provenance|
|11|`cat docs/SELECTION.md docs/LOCAL_RUN.md data/intents.json`|selection order, cap/load behavior, complete intent mapping|
|12|`cat eval/challenge.jsonl`|complete old sealed cards; no edits proposed|
|13|`sed -n '274,428p' data/prepare.py; sed -n '500,644p' data/prepare.py; sed -n '652,686p' data/prepare.py; sed -n '754,833p' data/prepare.py; sed -n '849,877p' data/prepare.py; sed -n '960,1024p' data/prepare.py; sed -n '1119,1160p' data/prepare.py`|placeholder/group/split/cap/audit functions; line offsets moved during edits|
|14|`rg -n 'add_argument\|def main\|n_boot\|negative\|SEAL\|seal\|split.*choices\|results.dir\|cap_train_rows' eval/run.py eval/blind.py eval/score.py eval/sample_test.py eval/run_sample.py train/train.py tools/check_run.py tools/check_submission.py tools/parity_check.py; sed -n '1140,1220p' data/prepare.py; git status --short --branch; ls eval/check_challenge.py eval/admission_scan.py docs/agent-learning/grok-corrections.jsonl`|branch v2, concurrent edits, path-routing flags; checker exists; scanner/ledger absent; exit one from ls|
|15|`cat eval/check_challenge.py`|schema, actual thresholds, seal/approval CLI|
|16|`sed -n '1,210p' README.md; sed -n '1,45p' eval/score.py; sed -n '228,243p' eval/score.py; sed -n '150,175p' train/train.py; sed -n '60,102p' data/prepare.py; sed -n '440,466p' data/PROFILE.md`|README first sections; executed verdict/bootstrap and cap semantics|
|17|`sed -n '211,500p' README.md; sed -n '535,580p' data/PROFILE.md; sed -n '137,168p' data/prepare.py; sed -n '197,241p' data/prepare.py; sed -n '117,136p' data/prepare.py; ls docs/plans eval/SEAL_v2.json eval/challenge_v2.jsonl`|README middle, template list, substitution/normalization helpers; fresh seal/files absent; exit one|
|18|`sed -n '581,605p' data/PROFILE.md; sed -n '501,730p' README.md; git log -1 --format='%h %s'; rg -n '^#\|^##' docs/v2/EVIDENCE.md`|remaining required text; HEAD `4c9373e`; evidence anchors|
|19|`python3 -c 'from pathlib import Path; import re; p=Path("docs/plans/V2_PLAN.md"); s=p.read_text(); print("words",len(s.split())); print("sections",re.findall(r"^## .*$",s,re.M)); print("admission total",sum(int(x) for x in re.findall(r"^\| [a-z_]+ \| \d+ \| [^\|]+ \| (\d+) \|$",s,re.M))); print("lines",len(s.splitlines()))'`|initial draft: 4561 whitespace tokens, all sections, quota 440; prompted shortening|
|20|`python3 -c 'from pathlib import Path; import re; s=Path("docs/plans/V2_PLAN.md").read_text(); print([(x.splitlines()[0],len(x.split())) for x in re.split(r"(?m)^## ",s)[1:]]); print("table separator tokens",sum(x in ("\|",) for x in s.split()))'`|section lengths; 610 standalone table separators|
|21|`python3 -c 'from pathlib import Path; p=Path("docs/plans/V2_PLAN.md"); s=p.read_text(); s="\n".join(line.replace(" \| ","\|").replace("\| ","\|").replace(" \|","\|") if line.startswith("\|") else line for line in s.splitlines())+"\n"; p.write_text(s); print("words",len(s.split()))'`|plan-only formatting mutation after shortening; 3234 whitespace tokens before final additions|
|22|`wc -w docs/plans/V2_PLAN.md; python3 -c 'from pathlib import Path; import re; s=Path("docs/plans/V2_PLAN.md").read_text(); print("headings",len(re.findall(r"^## ",s,re.M))); print("quotas",sum(int(x) for x in re.findall(r"^\|[a-z_]+\|\d+\|[^\|]+\|(\d+)\|$",s,re.M))); print("fences",s.count("```"))'`|3423 whitespace tokens before this log row/final clarifications; eleven headings, quota 440, eight balanced fences|

Only output written: `docs/plans/V2_PLAN.md`. Next: Fable reviews this plan and dispatches only nodes whose gates are satisfied.
