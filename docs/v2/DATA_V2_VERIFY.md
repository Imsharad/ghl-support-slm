# v2 Cleaner Verification

Written 2026-09-07 14:45 IST by Grok (task V2-B1v). Re-derived every number below from the files named in Source, not from `docs/v2/DATA_V2.md` as an input. Compared afterwards. Did not edit Opus's files.

Checked file: `docs/v2/DATA_V2.md`, 248 lines, sha256 `65217d37e0e84d73707158ca21504453f7665adcf6f006b5d09197a3a1e57e00`. Last changed in `c44970a` (V2-B1). Verified at `53ede92` (`origin/v2`, pull at 14:35 IST; `c44970a` is an ancestor).

Mismatch count: **2**. Both sit in DATA_V2.md section 8, the doubled-determiner paragraph. Every other quantity Fable listed matches.

`configs/cleaning.json` `substitutions.entries[]` has no `recovered` key. The recovered count is the `rows` field (`substitutions.rows_field` describes it as "rows recovered"). Sum of `rows` is 4,318.

Nearest-cross-split cosine was re-read from `data/audit.json` and `data/v2/audit.json`. MiniLM was not re-embedded.

## Table

| quantity | DATA_V2.md says | re-derived | source | match |
|---|---|---|---|---|
| v2 raw / kept / rejected | 26,872 / 26,764 / 108 | 26,872 / 26,764 / 108 | `data/v2/audit.json` `raw_rows`, `kept_rows`, `rejected_rows` | yes |
| v1 raw / kept / rejected | 26,872 / 22,448 / 4,424 | 26,872 / 22,448 / 4,424 | `data/audit.json` same keys | yes |
| v2 overlength dropped | 10 | 10 | v2 audit `overlength_dropped`; `rule_counts.drop_overlength_512` | yes |
| v1 overlength dropped | 8 | 8 | v1 audit | yes |
| v2 substitutions applied / distinct placeholders | 9,654 / 81 | 9,654 / 81 | v2 audit `substitutions_total`, `substitution_placeholders_used` | yes |
| v2 `reject_placeholder_no_neutral_wording` | 37 | 37 | v2 `rule_counts` | yes |
| v1 `reject_placeholder_no_neutral_wording` | 4,355 | 4,355 | v1 `rule_counts` | yes |
| other reject rules v1=v2 | completed_action 1, invented_timeline 50, request_credentials 1, unresolved_placeholder 9 | identical | both `rule_counts` | yes |
| recovered arithmetic | 22,448 + 4,318 − 2 = 26,764 | 22,448 + 4,318 − 2 = 26,764 | kept + recovered − new overlength | yes |
| recovered sum | 4,318 | 4,318 | sum of `configs/cleaning.json` `substitutions.entries[].rows` (82 entries; 61 with rows>0) | yes |
| 4,355 minus still-rejected | 4,355 − 37 = 4,318 | 4,355 − 37 = 4,318 | v1 minus v2 `reject_placeholder_no_neutral_wording` | yes |
| recovered table (61 placeholders) | DATA_V2 §3 | every phrase and `rows` value identical; sum 4,318 | cleaning.json entries vs markdown table | yes |
| substitution phrases passing lint | 82, all pass | 82 entries; `check_substitution_phrase` raises on 0; `load_cleaning` ok | `data/prepare.py:277`; grep of phrases for digits, `@`, `http`, `www.`, `within`, `guarantee`, `always`, `24/7`: 0 hits | yes |
| `cancel_order` kept v1 / v2 | 66 / 996 | 66 / 996 | `per_intent.cancel_order.rows` | yes |
| `change_order` | 942 / 997 | 942 / 997 | both audits `per_intent` | yes |
| `change_shipping_address` | 973 / 973 | 973 / 973 | same | yes |
| `check_cancellation_fee` | 950 / 950 | 950 / 950 | same | yes |
| `check_invoice` | 926 / 999 | 926 / 999 | same | yes |
| `check_payment_methods` | 942 / 999 | 942 / 999 | same | yes |
| `check_refund_policy` | 889 / 960 | 889 / 960 | same | yes |
| `complaint` | 887 / 999 | 887 / 999 | same | yes |
| `contact_customer_service` | 151 / 997 | 151 / 997 | same | yes |
| `contact_human_agent` | 884 / 998 | 884 / 998 | same | yes |
| `create_account` | 933 / 997 | 933 / 997 | same | yes |
| `delete_account` | 908 / 993 | 908 / 993 | same | yes |
| `delivery_options` | 564 / 963 | 564 / 963 | same | yes |
| `delivery_period` | 973 / 997 | 973 / 997 | same | yes |
| `edit_account` | 739 / 1,000 | 739 / 1,000 | same | yes |
| `get_invoice` | 977 / 998 | 977 / 998 | same | yes |
| `get_refund` | 857 / 997 | 857 / 997 | same | yes |
| `newsletter_subscription` | 979 / 998 | 979 / 998 | same | yes |
| `payment_issue` | 837 / 999 | 837 / 999 | same | yes |
| `place_order` | 934 / 994 | 934 / 994 | same | yes |
| `recover_password` | 435 / 994 | 435 / 994 | same | yes |
| `registration_problems` | 924 / 999 | 924 / 999 | same | yes |
| `review` | 961 / 996 | 961 / 996 | same | yes |
| `set_up_shipping_address` | 944 / 997 | 944 / 997 | same | yes |
| `switch_account` | 969 / 983 | 969 / 983 | same | yes |
| `track_order` | 962 / 993 | 962 / 993 | same | yes |
| `track_refund` | 942 / 998 | 942 / 998 | same | yes |
| per-intent totals / n intents | 22,448 / 26,764 / 27 | 22,448 / 26,764 / 27 | sum of `per_intent.*.rows` | yes |
| v1 / v2 groups sum | 4,462 / 4,877 | 4,462 / 4,877 | sum of `per_intent.*.groups` | yes |
| v2 kept range | 950 to 1,000 | min 950 (`check_cancellation_fee`) max 1,000 (`edit_account`) | v2 `per_intent` | yes |
| v1 kept range | 66 to 979 | min 66 (`cancel_order`) max 979 (`newsletter_subscription`) | v1 `per_intent` | yes |
| v2 train / val / test rows | 20,926 / 2,753 / 3,085 | 20,926 / 2,753 / 3,085 | v2 audit `splits`; `data/v2/splits.json`; processed jsonl line counts | yes |
| v2 train / val / test groups | 3,905 / 486 / 486 | 3,905 / 486 / 486 | audit `splits.*.groups`; `len(splits.json[split].groups)` | yes |
| v2 train sha256 | `934fcc0ac8b1c4f5f342a96b87b778b9a0624c5ad18fba54a2f265f57978b6b2` | identical | audit, splits.json, sha256 of `data/processed/v2/train.jsonl` | yes |
| v2 val sha256 | `6f35948d7c03678d02a3a931c307da4ad0d33713ad924077c1dd10ad346c2000` | identical | same three | yes |
| v2 test sha256 | `70e1de8594f7d4903e677797936040e83ad64530a4917a8c986278194eec8bae` | identical | same three | yes |
| v1 train / val / test sha256 | SEAL `307c59da…` / `b5f2e52d…` / `ef864aac…` | identical to SEAL, v1 audit, v1 splits.json, and sha256 of `data/processed/{train,val,test}.jsonl` | `eval/SEAL.json` `split_sha256`; `data/prepare.py --audit-only --strict` | yes |
| v2 audit.json sha256 / lines | `96150e5a…` / 815 | identical / 815 | sha256 of file at HEAD | yes |
| v2 splits.json sha256 / lines | `7ce90bf0…` / 4,899 | identical / 4,899 | sha256 of file at HEAD | yes |
| cleaning.json / prepare.py / test_prepare.py sha256 | `ebce1b69…` / `db9517c6…` / `fc5ccd39…` | identical | files at `53ede92` | yes |
| seed / threshold / linkage | 42 / 0.86 / average | 42 / 0.86 / average | both audits | yes |
| group-id intersection empty | True / True | True / True | both `cross_split.group_id_intersection_empty` | yes |
| normalized-instruction intersection empty | True / True | True / True | both `cross_split.normalized_instruction_intersection_empty` | yes |
| groups straddling a split | 0 / 0 | empty intersection lists | both `cross_split.group_id_intersections` | yes |
| near-collapse intents | 1 / 0 | v1: `cancel_order` share 0.803; v2: `[]` | `near_collapse_intents` | yes |
| intents missing a split | 0 / 0 | `[]` / `[]` | `intents_missing_a_split` | yes |
| grouping pinned to | `24ab0d9` / none | `24ab0d9` / `null` | `grouping_pinned_to` | yes |
| v1 nearest-cross-split cosine | n 4,747 min 0.4776 p50 0.8923 p95 0.9387 max 0.9708; 3,693 at or above 0.86 (77.8%) | identical; 3693/4747 = 77.8% | v1 `nearest_cross_split_cosine` | yes |
| v2 nearest-cross-split cosine | n 5,838 min 0.5057 p50 0.8959 p95 0.9427 max 0.9825; 4,683 at or above 0.86 (80.2%) | identical; 4683/5838 = 80.2% | v2 `nearest_cross_split_cosine` | yes |
| v1 invariant `--audit-only --strict` | train=17701 val=2477 test=2270; hashes match SEAL | `audit-only ok train=17701 val=2477 test=2270` / `strict: hashes and intersections match` | `uv run python data/prepare.py --audit-only --strict` at `53ede92`; compared to `eval/SEAL.json` | yes |
| v2 `--audit-only --out data/v2 --strict` | train=20926 val=2753 test=3085 | `audit-only ok train=20926 val=2753 test=3085` / `strict: hashes and intersections match` | same command with `--out data/v2` | yes |
| doubled-determiner rows in kept set | 1,771 of 22,448 (v1); 2,015 of 26,764 (v2) | **1,392** of 22,448 (v1); **1,616** of 26,764 (v2). `your your` 1,338 / 1,562; `the the` 54 / 54; `our our` 0 / 0. All hits are in `response`. | word-boundary search of `your your\|our our\|the the` over `data/processed/{train,val,test}.jsonl` and `data/processed/v2/*.jsonl` (hashes match splits.json) | **no** |
| doubled-determiner rows in processed train | (same 1,771 / 2,015 claimed of all kept) | v1 train **1,104** / 17,701; v2 train **1,089** / 20,926 | `data/processed/train.jsonl`; `data/processed/v2/train.jsonl` | **no** vs the claimed 1,771 / 2,015 |
| recovered rows carrying the defect | 269 of 4,318; 0 from a substitution phrase | **224** of 4,318 recovered originals have the doubled string after substitute-mode `apply_cleaning` | `apply_cleaning(..., substitute=True)` on raw rows whose reject-mode clean is rejected and substitute-mode clean is kept | **no** |

## Doubled-determiner note

Fable asked to confirm 1,771 and 2,015 from the processed train files. DATA_V2.md section 8 states those counts of all kept rows (22,448 / 26,764), not of train alone. Neither reading re-derives.

Processed-file method: JSONL row counts as a hit when `instruction` or `response` matches `\b(your your|our our|the the)\b` (case-insensitive). `our our` never appears. Train-only hits are 1,104 (v1) and 1,089 (v2).

A prefix-mechanism count (response prefix ends with `your`/`our` before a `your …` mapping, `reject_id is None`) gives 1,763 (v1) and 2,007 (v2), close to the claimed figures but still not equal, and that is not what the processed files contain.

The defect itself is real: `replace_placeholders` consumes a preceding `the` before a `your …` wording and never a preceding `your` or `our` (`data/prepare.py` around the `_THE_PREFIX` branch). Do not fix it in this node.

## Commands

```
git fetch origin v2
git rev-parse HEAD   # 53ede92505da5935206879333afe6e6e27d894fe
uv run python data/prepare.py --audit-only --strict
uv run python data/prepare.py --audit-only --out data/v2 --strict
uv run python -c 'from data.prepare import check_substitution_phrase, load_cleaning; ...'
uv run python tools/hygiene_check.py --tree
```

Plus sha256 of the listed files, JSON reads of both audits / both splits.json / SEAL.json / cleaning.json, and the doubled-determiner scan of the gitignored processed JSONL.
