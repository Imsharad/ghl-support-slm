# v3 submission readiness

Status: incomplete. Do not submit as a proven improvement.

Candidate04 update (2026-09-09): a free Colab T4 completed 120 updates, resume
smoke and a real adapter reload; all four checkpoints are recovered and verified.
After Colab disappeared, a separate 330-response MPS development comparison
completed and every response was reviewed. No checkpoint qualifies because
boundary and helpfulness failures remain. No new final evaluation or serving
promotion occurred. Evidence: `data/v3/candidate04_colab_execution.json` and
`eval/results/v3/development/candidate04-mps/review.json`. The candidate03
submission/readiness evidence below remains historical and is not relabelled
as candidate04 success.

| Requirement | Verified evidence | Remaining work |
|---|---|---|
| Commercially self-hostable SLM | Pinned Apache-2.0 Qwen2.5-1.5B-Instruct; `configs/versions.json`, license review | Preserve notices at publication |
| Data exploration and leakage handling | Bitext profile; whole-group/six-gram/pinned-MiniLM audits; exact clean-checkout reconstruction | Screening cannot prove semantic independence |
| Fine-tuning and curves | Completed CUDA run, four checkpoints, full validation, resume smoke; `train/runs/v3-candidate03-runpod*` | No missing training stage |
| Reasoned choices and attempts | Config, `docs/v3/PLAN.md`, `docs/v3/SELECTION.md`; early repetition and setup failure preserved | Owner must be able to defend choices |
| Held-out base vs tuned comparison | Partial analysis: 106 observed pairs, all 27 intents, paired uncertainty and omission bounds; `eval/results/v3/final01/partial-mixed-analysis-001/analysis.json` | Owner omitted 107/108; human notes absent; mixed-judge deviation means the all-human primary protocol remains incomplete |
| Measurable improvement | Recorded task success 55.7% base vs 76.4% tuned | Safety failed: two supported tuned credential violations; do not claim the full improvement objective achieved |
| Self-hosted HTTP endpoint | Local `/support` base/tuned routes with prompt/model identity guards | Production auth, TLS and concurrency are explicitly cut |
| Performance numbers | Complete 54+54 HTTP benchmark, raw requests, hardware and limitations; `eval/results/v3/paired-api-warm02` | Not a concurrent/cold-start capacity claim |
| Adapter and model loading | Verified local adapter, merge and Q8; live PEFT/MPS smoke and 5-query prompt parity | Public v3 weight link requires approval |
| Full implementation repository | Local v3 commits; historical work preserved | Public branch/push requires approval |
| README and exact prompt | v3 quickstart, native ChatML, pinned config, reproduced data, measured performance and honest partial mixed-judge result | Final reproduction/package review; do not relabel partial results as primary |
| 2–5 minute Loom/equivalent | Verified 2:47 captioned terminal recording: `eval/results/v3/demo-recording-001/demo.mp4`; actual HTTP pairs, results and failures | Owner review; no voice-over, public Loom upload or employer submission |
| Compute restriction | Approximately $0.45 owner-authorized RunPod use, all rentals deleted | Disclose employer-brief deviation; no employer approval assumed |

## Loom / interview outline (about three minutes)

Suggested narration, in the same order as the captioned recording:

1. “I fine-tuned Apache-2.0 Qwen2.5-1.5B-Instruct using QLoRA. I used 216
   individually rewritten Bitext targets plus 27 supplied-context examples,
   with 54 validation examples. The small corpus let me inspect targets and
   remove unsupported business claims, but limits language coverage.”
2. “This is the local HTTP endpoint. Its model digests and prompt hash match
   the sealed evaluation. Base and tuned use identical greedy decoding.
   These two side-by-side examples are fresh requests, not saved answers.”
3. “Notice the contact-details example, then the PayPal example. A model must
   not assert a payment policy it was never given. A disclaimer later in the
   answer does not undo an unsupported opening claim.”
4. “The reported comparison has 106 graded pairs across all 27 intents:
   29 human and 77 Terra, calibrated on 27 human examples. Two questions were
   omitted; human evidence notes are missing. This differs from the original
   all-human protocol and is not independent judge validation.”
5. “Recorded pass rates are 55.7% base and 76.4% tuned. The intent-macro
   difference is 21.60 points, with a 95% cluster interval of 8.95 to 34.26.
   Even the worst outcome on both missing pairs leaves a positive gain.
   But tuned has two credential violations: a reset-link invitation and a
   password request. That fails the fixed zero-violation safety gate.”
6. “The separate 54-plus-54 warm serial HTTP benchmark measures latency, not
   concurrency or streaming capacity. There are no account tools, retrieval,
   authentication or TLS. About 45 cents of owner-authorized RunPod use is a
   disclosed deviation from the employer's free-compute instruction. The
   README contains reproduction and loading commands. This is a useful result,
   not a claimed successful completion of the safety objective.”

Interview preparation:

- Why this model/method? Commercially self-hostable license, small local serving
  footprint, a standard adapter, and modest GPU memory. No broad model sweep claimed.
- Why not train on all Bitext responses? Sample inspection found fabricated
  policies, tool-access promises and substitution artifacts; quantity was not quality.
- How was leakage handled? Whole paraphrase groups, exact/six-gram checks and
  pinned embedding screens; these reduce measured overlap, not prove independence.
- Why not select by validation loss? Development outputs revealed repetition,
  intent mistakes and unsupported policies despite a useful loss signal.
- Why not call the evaluation a win? Task success improved, but safety failed;
  mixed judging, same-author test construction and missing notes also weaken evidence.
- What would you change next? Improve safety on development data, retain the base
  comparison, and author/screen a genuinely new final set before another frozen run.

Next: owner reviews the captioned recording and the package. The
owner explicitly omitted questions 107/108. The resulting 106-pair analysis has
a positive task-success difference even under worst-case missing-pair assumptions,
but fails the zero-credential-violation gate. Any further candidate development
must use development evidence and a genuinely new, independently screened final
evaluation; do not patch this candidate against the now-unblinded final answers
or revise the safety gate to manufacture success. Publication/submission still
requires separate approval.
