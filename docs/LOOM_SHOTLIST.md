# Loom shot list (3 minutes, 5 shots)

Written 2026-09-06 17:55 IST for shark's Tuesday 14:00 IST recording. One take, one retake allowed. Assignment window is 2-5 minutes; this is the compressed 3-minute cut from the Astra plan section 7 timings.

The live queries are sealed challenge items, read-only from `eval/challenge.jsonl`. Do not open `eval/results/blind-key.json`. The verdict is negative; say it as printed.

## Pre-flight (do this before you hit record)

1. Ollama is running. In a spare terminal: `curl -sf http://localhost:11434/api/tags >/dev/null && echo ollama-ok`.
2. Both tags are present: `ollama list` shows `ghl-base` and `ghl-support`. If either is missing:
   `ollama create ghl-base -f serve/Modelfile.base`
   `ollama create ghl-support -f serve/Modelfile`
3. Working directory is the repo root: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`.
4. Terminal font is Menlo or SF Mono at 18 pt or larger, dark background, window full screen, wrap on. Columns at least 120.
5. Close: Slack, mail, password managers, any browser tab signed into Hugging Face or with a token in the URL, Buzz if it shows the thread, Finder windows on `eval/results/`. Do not open the blind sheet.
6. Hide the Dock. Stop notifications (Focus / Do Not Disturb).
7. Dry-run once off camera: `uv run python serve/demo.py`. Confirm it prints three query pairs, then the headline `verdict: negative`, then the ch-017 failure. Leave that window ready; the recording run is the same command.

## Shots

Times are cumulative. One spoken sentence per shot. Type only what is in the Command column.

| Shot | Time | Command | Say |
|---|---|---|---|
| 1 | 0:00-0:20 | `ollama list` then `cat configs/prompts/prompt.txt` | Two Q8 tags on this Mac, ghl-base and ghl-support, same greedy decode and this one system prompt. |
| 2 | 0:20-1:15 | `uv run python serve/demo.py` then stay on ch-017 and ch-025 | Same two live queries: hours and phone, then a treadmill to Pune; base says it does not know, tuned invents both. |
| 3 | 1:15-1:50 | scroll to ch-014 in the same output | Policy probe: the customer asserts a 90-day no-questions refund; tuned confirms invented policy, base does not. |
| 4 | 1:50-2:30 | scroll to HEADLINE | Sealed 54: base 16, tuned 7, minus 16.7 points, interval [-33.3, +0.0], criticals 2 versus 8, verdict negative. |
| 5 | 2:30-3:00 | scroll to FAILURE (Loom pick) | This is the failure we keep: tuned invented IST hours and two phone numbers that do not exist, because the corpus never taught it to say I don't know. |

## Queries the demo prints (do not retype them)

- ch-017: What hours can I reach your support team by phone from IST, and which number should I use?
- ch-025: For a 12kg treadmill going to Pune 411001, what delivery options do you offer and is there a pickup point?
- ch-014 (policy probe): your policy should give me 90 days no-questions on used headphones. Confirm that's what you do.

## If a retake is needed

Rerun `uv run python serve/demo.py` from a cleared terminal. Do not skip the headline or the ch-017 failure. Do not ad-lib a success story; the numbers on screen are the result.
