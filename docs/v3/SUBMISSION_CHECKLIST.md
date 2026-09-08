# v3 submission readiness

Status: incomplete. Do not submit as a proven improvement.

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
| 2–5 minute Loom/equivalent | Live `serve/demo_v3.py` recording aid, including failure check | Actual final recording and link; quality walkthrough awaits grades |
| Compute restriction | Approximately $0.45 owner-authorized RunPod use, all rentals deleted | Disclose employer-brief deviation; no employer approval assumed |

## Loom / interview outline (about three minutes)

0:00–0:30: State the task, model size/license, compact curated-data intervention and
the distinction between helpful instructions and invented business knowledge.

0:30–1:20: Show `/health`, then run `serve/demo_v3.py`. Explain that both answers
come from live HTTP requests using one exact prompt and greedy decoding. Show
the shared-query side-by-side; do not label a single selected example as an
overall win.

1:20–2:20: Show the frozen 108-case protocol and, once graded, the real paired
pass rates, cluster-bootstrap interval and safety counts. Explain the same-author
test limitation, leakage screen and why validation loss is secondary.

2:20–3:00: Show a real failure (unsupported PayPal acceptance if present in the
live answer), describe step-30 repetition, and explain the missing production
tools/policies/authentication. Disclose paid compute and say whether the fixed
quality gate actually passed. Never replace missing scores with invented ones.

Next: finish an honest recording/results walkthrough and package review. The
owner explicitly omitted questions 107/108. The resulting 106-pair analysis has
a positive task-success difference even under worst-case missing-pair assumptions,
but fails the zero-credential-violation gate. Any further candidate development
must use development evidence and a genuinely new, independently screened final
evaluation; do not patch this candidate against the now-unblinded final answers
or revise the safety gate to manufacture success. Publication/submission still
requires separate approval.
