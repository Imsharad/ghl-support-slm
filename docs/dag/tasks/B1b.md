# Task B1b: Frame-aware and voice-aware placeholder wording

- Worker: Grok
- Phase: B
- Due (IST): Sun 2026-09-06 02:00
- Estimate: 1.0 h
- Depends on: B1, C4
- Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`
- Read first: `docs/dag/CONTRACTS.md`, then the briefs of your dependencies under `docs/dag/tasks/`, then `docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md` section 2 and the Astra plan sections 5 and 6 for the traps and evaluation rules.

## Owned paths (write only here)

- `data/prepare.py`
- `data/processed/`
- `data/splits.json`
- `data/audit.json`
- `configs/cleaning.json`
- `tests/test_prepare.py`

If you need a change outside these paths, describe it in your report; do not make it.

## Brief

C4 found that the blanket neutral wording for id-style placeholders is ungrammatical in the common frames and uses the
assistant's voice inside the user turn: 782 train instructions read "purchase your order number", 767 "order your order
number", 1,475 rows "number your order number", 760 "the your ...". Fix the wording, not the grouping.

Do:
- In `replace_placeholders`, make the wording depend on the field and the preceding words. Possessive P is "my" in the
  instruction and "your" in the response. For every id-style placeholder in `placeholder_replace` whose wording is
  "your <noun phrase>" (order number, invoice number, tracking number, account number, account id, account type, account
  category, refund amount): `(order|purchase|invoice|tracking|account)\s+number\s+{{X}}` -> "P <noun> number";
  `(order|purchase|invoice|account)\s+{{X}}` -> "P <that word>"; `the\s+{{X}}` -> "P <noun phrase>";
  standalone -> "P <noun phrase>". Keep Bitext typo rows as they are (a typo before the slot falls to the standalone form).
- Add a `frame` count per rule to `data/audit.json` so the README can say how many rows took each form.
- Regenerate. Splits must not move: group ids, split membership and `data/splits.json` group lists are expected to be
  byte-identical to 24ab0d9 because `normalize` runs on the raw text; if anything moves, stop and report before committing.
- `tests/test_prepare.py`: add cases for the four frames in both voices, and assert no processed instruction contains
  "your order number" preceded by order/purchase/number, and no "the my"/"the your".

Verify: `uv run python data/prepare.py` then `--audit-only --strict`; `uv run pytest -q`; report the count of rows whose text
changed per split and confirm splits.json group lists are unchanged (diff against HEAD).

## Rules for every task

- Work in the repo above on `main`. Commit with `git add <your paths only>` and message `B1b: <what>`; never `git add -A`; never amend or rebase; pull before commit if the index is locked, retry once.
- Run only under `uv run` in the repo venv (Python 3.11). System python is 3.14 and is off limits.
- No emojis anywhere. IST timestamps, labeled. No secrets in files (HF tokens stay in env).
- Do not start training, do not touch `eval/challenge.jsonl` after it is sealed, do not read blind keys.
- Report back in the GoHighLevel-prep thread (root `1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593`) with `@Fable 5.1`: what landed (paths), the verification command output, anything you could not do and why. One message when done or blocked; no acknowledgement messages.
- Detached jobs (anything you launch with `Popen(start_new_session=True)` or a launcher script that outlives your turn): the launcher script itself must post the finish line to this thread with `buzz messages send --channel 04861c85-e907-4639-9075-7c474cbd8b51 --reply-to 1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593 --mention c8ab0f4dfbc279dd4d4437a153d595c3a03bf710f1641e36691c888f53ba4c9d`, carrying the exit code and the result line, on both success and failure. Write that line into the script at the same time as the run command. A log file is not a callback, your session will not be awake when the job ends, and a post that mentions only yourself wakes nobody (D2L stalled 58 minutes, D3 stalled four hours on 2026-09-06).
