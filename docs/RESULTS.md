# Results

Written 2026-09-06 17:35 IST by Fable 5.1 (task E3). Verdict for the served Q8 artifacts, `ghl-base` against `ghl-support`, on the sealed 54-item challenge set (`eval/challenge.jsonl`, sha256 `76e24d34...`, sealed 12:51 IST). Numbers are copied from `eval/results/summary.jsonl`; the command that produced them is at the end.

## Headline: the tune is worse on the challenge set

| | base (`ghl-base`, Qwen2.5-1.5B-Instruct Q8) | tuned (`ghl-support`, checkpoint-400 Q8) |
|---|---:|---:|
| pass rate (n = 54) | **16 / 54 = 29.6%** | **7 / 54 = 13.0%** |
| critical failures | 2 | 8 |

| difference (tuned minus base) | 95% interval (paired bootstrap, 2000 draws, seed 42) | preferred: tuned / tie / base | verdict |
|---:|---:|---:|---|
| **-16.7 points** | [-33.3, +0.0] | 18 / 7 / 29 | **negative** |

The rule in `eval/score.py`: positive needs a gain of at least 5 points with the whole interval above zero and no more critical failures than base; negative is any loss or any rise in critical failures. This result is negative on both counts. Nothing was retuned, rescored, or reselected after seeing it.

## How the sheet was scored: read this before quoting the numbers

**This is not the human-scored sheet the plan called for.** Task H2 was for shark to score all 108 answers by hand. At shark's request (GoHighLevel-prep thread, 2026-09-06 16:20 to 17:17 IST) it was scored like this instead:

1. Gemini 3.8 Flash (`gemini-3.8-flash-high` through the `agy` CLI) scored every card twice, the second pass with A and B swapped. It saw only what the sheet shows: query, facts, acceptable actions, critical lines, two answers. Agreement with itself: critical 107 of 108 answers, pass 102 of 108, preferred 49 of 54. Outputs in `eval/results/llm-judge/` (`pass1.json`, `pass2.json`, `merged.json`).
2. Fable 5.1 then read all 54 cards against `eval/RUBRIC.md` with the Flash reason line beside each and wrote the final verdicts. It resolved the 12 cards where Flash disagreed with itself and changed 13 fields on 12 cards against Flash's first pass (four of them consistent Flash verdicts). Every change and its rubric reason is in `eval/results/llm-judge/adjudication.json` and in the `notes` column of `eval/results/blind-sheet-scored.csv`.
3. Neither judge saw model names. `eval/results/blind-key.json` was read only by `eval/score.py`, after the sheet was final.

Lines drawn, applied the same way to both sides: a conditional offer that asks for the identifier the card lists and promises only a lookup or guidance is a pass; one that promises a change the assistant cannot make (cancel, update, subscribe, close, waive) is a plain fail; a stated false fact, a done action, or a request for a password or full card number is critical. This follows `RUBRIC.md` as written. Note that `docs/SELECTION.md` (D3, dev set) counted unconditional promises as critical, so dev and challenge critical counts are not on the same rule.

What this does to the claim: an LLM judge is harsher than a person on "no actionable next step" (its top tag, 35 of 108 answers on pass 1), so both pass rates are probably a few points low. The direction is not in doubt. The eight tuned criticals are invented facts a reader can check in `eval/results/failures.jsonl`: support hours and phone numbers twice (`ch-017`, `ch-018`), delivery options and windows twice (`ch-025`, `ch-026`), a CEO salary (`ch-012`), a 90-day refund policy (`ch-014`), stacked discounts (`ch-050`), and an address that was never saved (`ch-047`). Base's two are a 3-to-5-day delivery promise (`ch-027`) and a request for card number plus CVV (`ch-034`).

## By kind and by intent

| kind | n | base pass | tuned pass | diff points | base critical | tuned critical |
|---|---:|---:|---:|---:|---:|---:|
| hard | 27 | 22.2% | 11.1% | -11.1 | 1 | 5 |
| ordinary | 27 | 37.0% | 14.8% | -22.2 | 1 | 3 |

Two items per intent, one ordinary and one hard. Passes out of 2:

| intent | base pass | tuned pass | base critical | tuned critical |
|---|---:|---:|---:|---:|
| `cancel_order` | 2 | 0 | 0 | 0 |
| `change_order` | 0 | 0 | 0 | 0 |
| `change_shipping_address` | 0 | 0 | 0 | 0 |
| `check_cancellation_fee` | 2 | 0 | 0 | 0 |
| `check_invoice` | 1 | 0 | 0 | 0 |
| `check_payment_methods` | 1 | 0 | 0 | 1 |
| `check_refund_policy` | 2 | 0 | 0 | 1 |
| `complaint` | 0 | 0 | 0 | 0 |
| `contact_customer_service` | 1 | 0 | 0 | 2 |
| `contact_human_agent` | 0 | 0 | 0 | 0 |
| `create_account` | 0 | 0 | 0 | 0 |
| `delete_account` | 0 | 0 | 0 | 0 |
| `delivery_options` | 1 | 0 | 0 | 2 |
| `delivery_period` | 0 | 0 | 1 | 0 |
| `edit_account` | 0 | 2 | 0 | 0 |
| `get_invoice` | 0 | 1 | 0 | 0 |
| `get_refund` | 1 | 0 | 1 | 0 |
| `newsletter_subscription` | 1 | 0 | 0 | 0 |
| `payment_issue` | 1 | 0 | 0 | 0 |
| `place_order` | 0 | 1 | 0 | 0 |
| `recover_password` | 1 | 0 | 0 | 0 |
| `registration_problems` | 1 | 0 | 0 | 0 |
| `review` | 1 | 1 | 0 | 0 |
| `set_up_shipping_address` | 0 | 0 | 0 | 1 |
| `switch_account` | 0 | 1 | 0 | 1 |
| `track_order` | 0 | 0 | 0 | 0 |
| `track_refund` | 0 | 1 | 0 | 0 |

Tuned wins outright on `edit_account` (both items), `switch_account`, `get_invoice`, `place_order`, `track_refund`: self-serve navigation answers where Bitext's "log in, open Settings" shape is the right one. Base wins where the query asks for a fact the assistant cannot know: fees, policy windows, hours, delivery options, payment methods.

## Why: the tune learned the voice and unlearned the admission

Counts from `eval/results/*-challenge-raw.jsonl` and `data/processed/train.jsonl`:

| | base answers (54) | tuned answers (54) | training split (17,701 rows) |
|---|---:|---:|---:|
| admits a missing fact ("I don't have access", "I'm not able to", "I can't") | 17 | 0 | 24 |
| uses a Bitext template phrase ("I'm on it", "I'm on the same wavelength", "Rest assured"; the first two as openers, the third anywhere in the answer) | 0 | 11 + 13 + 9 | 250 + 43 + 3,632 |
| refuses outright ("I can't assist with that") | 5 | 0 | 0 |

The training data has almost no rows in which the assistant says it does not know something (24 of 17,701; 17 of the 8,000 rows the T4 config trains on). It has thousands of confident first-person company sentences. One epoch was enough to remove the base model's admission habit entirely. When a challenge query asks for hours, a fee, a delivery window or a policy, the tuned model has one shape available, the confident one, and fills the blank. `docs/FAILURES.md` walks through three cases with the intent counts behind each.

## Bitext test set: automatic reference metrics (D3, for contrast)

Same 270-row group-disjoint sample, same references (`eval/results/test-sample-refs.jsonl`):

| | base (Q8) | tuned (fp16 merged) | tuned (Q8, served) | diff tuned fp16 minus base, 95% CI |
|---|---:|---:|---:|---:|
| ROUGE-L F1 mean | 0.215 | 0.366 | 0.367 | -0.151 [-0.165, -0.137] |
| embedding cosine mean (MiniLM-L6) | 0.674 | 0.831 | 0.829 | -0.157 [-0.179, -0.137] |
| truncated at 256 tokens | 10.4% | 2.6% | 2.2% | |
| mean length (tokens) | 107.8 | 91.8 | 91.8 | |

Base on the full 2,270-row test split: ROUGE-L 0.226, cosine 0.711 (`eval/results/base-test-auto.json`).

These two tables disagree on purpose. Reference similarity measures whether the model writes like Bitext, and it does, by 15 ROUGE points. The challenge set measures whether it helps a customer without inventing anything, and it does not. Q8 quantisation costs nothing measurable (fp16 vs Q8 within 0.002 on both metrics).

## Dev-set selection (D3)

`checkpoint-400` was chosen on `eval/dev.jsonl` alone: 13 of 54 passes with 20 critical failures, against 12/18 for checkpoints 300 and 500 and 9/14 for 250 (`docs/SELECTION.md`). The same pattern, more fluency and more invention with more training, shows up here. `docs/SELECTION.md` said the pick was weak; the challenge result does not change it, and it was not revisited.

## Serving (F1)

`serve/bench.py`, 30 serial requests after 5 warmups, Ollama 0.24.0 on an M1 Pro, 16 GB (`serve/bench_results.json`):

| model | p50 end-to-end | p95 end-to-end | generation tokens/s | cold load | failures |
|---|---:|---:|---:|---:|---:|
| `ghl-base` | 1.35 s | 3.34 s | 66.8 | 0.89 s | 0 |
| `ghl-support` | 1.43 s | 2.94 s | 65.9 | 2.30 s | 0 |

Same GGUF size, same throughput: the adapter changes what the model says, not what it costs to run.

## Files and verification

- `eval/results/blind-sheet-scored.csv`: the scored sheet, sha256 `eb898c7f557cbb1334014328401eb79ce8edc9931971e69c02516bb4b3cd357e`. Answers byte-identical to `blind-sheet.csv` (`score.py` checks every answer hash against the key).
- `eval/results/scores.jsonl` (108 rows, one per answer), `eval/results/summary.jsonl` (one verdict row), `eval/results/failures.jsonl` (47 rows: every item the tuned model failed or lost).
- `eval/results/llm-judge/`: judge prompt guide, raw batches, both passes, merge, adjudication.

```
$ uv run python eval/score.py --final --require-complete --sheet eval/results/blind-sheet-scored.csv
n=54 base=0.296 tuned=0.130 diff_points=-16.67 ci95=[-33.33333333333333, 0.0] verdict=negative
scores=.../eval/results/scores.jsonl summary=.../eval/results/summary.jsonl failures=47
```

`summary.jsonl` verdict row: `"n": 54, "base_pass_rate": 0.2963, "tuned_pass_rate": 0.1296, "diff_points": -16.6667, "ci95": [-33.3333, 0.0000], "base_critical": 2, "tuned_critical": 8, "win": 18, "tie": 7, "loss": 29, "verdict": "negative"`.

## One-line verdict for the README

Fine-tuning Qwen2.5-1.5B-Instruct on 8,000 cleaned Bitext rows made it write like Bitext (+15 ROUGE-L points on held-out Bitext) and made it a worse support assistant on 54 sealed, out-of-distribution queries (pass rate 29.6% to 13.0%, critical failures 2 to 8, LLM-judged with adjudication, not human-scored). The cause is in the data: the corpus never says "I don't know".
