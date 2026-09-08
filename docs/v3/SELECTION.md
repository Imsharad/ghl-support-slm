# Candidate03 development selection

Selected on 2026-09-08, before final inference: `v3-candidate03-runpod/checkpoint-120`.
This is a candidate for evaluation, not a claim that it beats the base model.

## Evidence and rule

All four checkpoints and the pinned starting base answered the same 54 validation
queries under the exact v3 prompt, greedy decoding and 256-token cap on the same
CUDA backend. All 270 generations completed without infrastructure errors.
Raw answers and immutable manifests are in `eval/results/v3/development/*-cuda*.jsonl`.
The assistant inspected every answer unblinded. No owner-human pass grades have
been supplied, and this review is not the primary evaluation.

Choose the lowest validation-loss checkpoint among those without observed
degenerate repetition/truncation on this development run. This selection rule is
recorded after development inspection, not falsely described as preregistered.
Loss is a fit metric on same-author references, not a factuality score. The small
loss difference between steps 90 and 120 does not establish better support quality.

| Step | Validation loss | Truncated development answers / 54 |
|---|---:|---:|
| 30 | 2.32337 | 7 |
| 60 | 1.99031 | 0 |
| 90 | 1.88071 | 0 |
| 120 | 1.86520 | 0 |

Initial full-validation loss was 3.4693443. The 120-update run took 201.4 seconds
and peaked at 3.37 GiB allocated CUDA memory. The separate resumed smoke passed
with maximum logged-loss difference 0.00007 against tolerance 0.01.

## Failures and trade-offs retained

- Step 30 repeats disclaimers into the generation cap on seven queries. Falling
  loss alone would have missed this failure.
- Step 120 responds to human-support requests without the base's empty refusals
  on several development examples, and does not reproduce the base's invented
  phone number on `bitext-008038`. These examples are not a measured win rate.
- All candidate checkpoints still assert PayPal acceptance on `bitext-004940`
  without business context. Step 120 then contradicts itself by saying it cannot
  confirm availability. This remains an unsupported factual claim.
- Step 120 misreads invoice request `bitext-015014` as a verification-code request,
  labels compensation a legal process on `bitext-016138`, and gives questionable
  account-sharing guidance on `bitext-010567`. Some replies overstate an ability
  to find records and many overuse generic official-support directions.
- Later checkpoints have no observed repetition loops in these 54 generations,
  but factual and intent errors remain. Neither this inspection nor validation
  loss demonstrates generalization to the employer's internal queries.

The compact curated intervention was a bounded first experiment. We are testing
it as it stands, not promising a positive result or hiding its regressions. The
108 fresh screened cases have not generated model responses at selection time.
Once sealed and evaluated, those cases must not guide checkpoint or prompt tuning.
Primary blinded owner grading and the fixed safety/uncertainty gates determine
whether improvement is supported.

## Export

- Adapter weights SHA-256: `06049829fcf3b29c0ffed083368843e30c86a06fda7fcc3de0332d2c979180d8`.
- Q8 GGUF SHA-256: `06d865f722bda7e6abd250cfab01e61c5806369cf42207b557e2c6f2e27f1240`.
- Ollama tag: `ghl-support-v3-c03-s120`; historical tags are unchanged.
- Exact lineage: `artifacts/v3/candidate03-step120-q8_0.gguf.export.json`.
- Five historical-development prompt paths passed tokenizer-ID and same-GGUF
  raw-vs-chat answer parity: `docs/v3/parity-candidate03-step120.md`. This does not
  establish numerical equivalence of CUDA NF4, merged fp16 and Q8 generations.
