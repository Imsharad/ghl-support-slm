# Scoring rubric for challenge and dev answers

Use this sheet on a single answer in under a minute. Score the served text only. Do not look up which model wrote it.

Generated: 2026-09-05 22:55 IST

## What a pass is

A pass addresses every request in the query, gives a sound next step the customer can actually take, admits facts the assistant does not have, and stays in a helpful support tone. Correctness outranks style. "Contact support" with no next step is not a pass.

## What a critical failure is

Invented company policy, invented account or order status, a completed action the assistant could not have performed, a stated timeline presented as fact, or a request for a password or full payment-card number. One critical failure fails the item even if the rest of the answer is useful.

## Ten-line scoring guide

1. Read the query, `facts`, `acceptable_actions`, and `critical_fail_if` before the answer.
2. Mark **critical** if any `critical_fail_if` line is met, or if the answer invents policy, status, a completed action, a timeline as fact, or asks for a password or full card number.
3. A critical mark is a fail. Stop. Do not award a pass for tone.
4. If not critical, check that every distinct request in the query is addressed. Two-request items need both.
5. Check that the next step is something a real support assistant can offer (how to request, what to provide, where to look). Vague "we will look into it" without a step fails.
6. Missing ids, emails, or policy details in `facts` must be admitted or asked for. Filling them in is a fail.
7. Placeholders like `{{Order Number}}` in the answer are not a pass.
8. Tone may be plain. Politeness does not save a wrong action; rudeness alone does not fail if the content is sound.
9. Tick **pass** only if steps 4-7 hold and step 2 did not fire.
10. For the pair, tick **preferred** A, B, or tie on usefulness after both pass/fail marks are set. Do not prefer the longer answer by default.

## Blind sheet columns

From CONTRACTS.md section 3. Model identity for A/B lives only in `eval/results/blind-key.json` (gitignored).

```
item_id, query, facts, answer_A, answer_B, pass_A, pass_B, critical_A, critical_B, preferred (A|B|tie), notes
```

`pass_*` and `critical_*` are true/false. `preferred` is A, B, or tie. Write a short note when you hesitate.

## Sealing

Challenge items in `eval/challenge_draft.jsonl` are drafts for shark's 11:30 IST Sunday approval. Do not generate tuned-model answers until the sealed file and hash exist. Dev items are for debugging and the Loom demos only.
