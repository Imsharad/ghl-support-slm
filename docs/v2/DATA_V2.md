# DATA_V2 — substitute, do not reject

V2-B1. Numbers from `data/audit.json` (v1) and `data/v2/audit.json` (v2), both produced by
`data/prepare.py` from the same `data/raw/bitext.csv`. v2 run 2026-09-07 14:23 IST.

```
uv run python data/prepare.py --audit-only --strict                              # v1, unchanged
uv run python data/prepare.py --placeholder-mode substitute --out data/v2        # v2
uv run python data/prepare.py --audit-only --out data/v2 --strict                # v2
```

## 1. Raw, kept, rejected

| | v1 | v2 |
|---|---:|---:|
| raw rows | 26,872 | 26,872 |
| kept rows | 22,448 | 26,764 |
| rejected rows | 4,424 | 108 |
| overlength dropped (512) | 8 | 10 |
| substitutions applied | 0 | 9,654 |
| distinct placeholders substituted | 0 | 81 |

Rejections by rule:

| rule | v1 | v2 |
|---|---:|---:|
| `drop_overlength_512` | 8 | 10 |
| `reject_completed_action` | 1 | 1 |
| `reject_invented_timeline` | 50 | 50 |
| `reject_placeholder_no_neutral_wording` | 4,355 | 37 |
| `reject_request_credentials` | 1 | 1 |
| `reject_unresolved_placeholder` | 9 | 9 |
| **total** | **4,424** | **108** |

`reject_placeholder_no_neutral_wording` falls 4,355 -> 37. The other four rules are unchanged. `drop_overlength_512` moves 8 -> 10: two recovered rows exceed 512 tokens after substitution.

Arithmetic: 22,448 + 4,318 recovered - 2 newly overlength = 26,764.

## 2. Per intent, kept rows

| intent | v1 kept | v2 kept | delta | v1 groups | v2 groups | v2 train / val / test |
|---|---:|---:|---:|---:|---:|---|
| `cancel_order` | 66 | 996 | +930 | 12 | 65 | 970 / 7 / 19 |
| `change_order` | 942 | 997 | +55 | 150 | 144 | 843 / 35 / 119 |
| `change_shipping_address` | 973 | 973 | +0 | 200 | 200 | 806 / 38 / 129 |
| `check_cancellation_fee` | 950 | 950 | +0 | 167 | 167 | 748 / 85 / 117 |
| `check_invoice` | 926 | 999 | +73 | 177 | 170 | 817 / 83 / 99 |
| `check_payment_methods` | 942 | 999 | +57 | 165 | 171 | 770 / 124 / 105 |
| `check_refund_policy` | 889 | 960 | +71 | 122 | 131 | 777 / 36 / 147 |
| `complaint` | 887 | 999 | +112 | 232 | 246 | 792 / 101 / 106 |
| `contact_customer_service` | 151 | 997 | +846 | 62 | 201 | 762 / 67 / 168 |
| `contact_human_agent` | 884 | 998 | +114 | 285 | 301 | 730 / 171 / 97 |
| `create_account` | 933 | 997 | +64 | 218 | 195 | 856 / 63 / 78 |
| `delete_account` | 908 | 993 | +85 | 168 | 171 | 781 / 167 / 45 |
| `delivery_options` | 564 | 963 | +399 | 65 | 84 | 867 / 74 / 22 |
| `delivery_period` | 973 | 997 | +24 | 205 | 206 | 851 / 71 / 75 |
| `edit_account` | 739 | 1,000 | +261 | 198 | 222 | 605 / 142 / 253 |
| `get_invoice` | 977 | 998 | +21 | 150 | 143 | 775 / 145 / 78 |
| `get_refund` | 857 | 997 | +140 | 200 | 210 | 756 / 55 / 186 |
| `newsletter_subscription` | 979 | 998 | +19 | 137 | 138 | 586 / 101 / 311 |
| `payment_issue` | 837 | 999 | +162 | 127 | 130 | 588 / 246 / 165 |
| `place_order` | 934 | 994 | +60 | 379 | 387 | 790 / 113 / 91 |
| `recover_password` | 435 | 994 | +559 | 135 | 243 | 797 / 109 / 88 |
| `registration_problems` | 924 | 999 | +75 | 147 | 154 | 708 / 242 / 49 |
| `review` | 961 | 996 | +35 | 295 | 303 | 742 / 75 / 179 |
| `set_up_shipping_address` | 944 | 997 | +53 | 163 | 170 | 686 / 119 / 192 |
| `switch_account` | 969 | 983 | +14 | 136 | 126 | 765 / 176 / 42 |
| `track_order` | 962 | 993 | +31 | 78 | 94 | 942 / 10 / 41 |
| `track_refund` | 942 | 998 | +56 | 89 | 105 | 816 / 98 / 84 |
| **total** | **22,448** | **26,764** | **+4,316** | **4,462** | **4,877** | |

`contact_customer_service` 151 -> 997. `cancel_order` 66 -> 996. `recover_password` 435 -> 994. `delivery_options` 564 -> 963.

## 3. Rows recovered, by the placeholder that rejected them

4,318 of the 4,355 rows rejected by `reject_placeholder_no_neutral_wording` come back. A row is attributed to the first placeholder that rejected it in v1, so the column sums to the total. Same numbers in `configs/cleaning.json` `substitutions.entries[].rows`.

| placeholder | substituted with | rows recovered |
|---|---|---:|
| `{{Customer Support Hours}}` | the hours shown on our contact page | 1,168 |
| `{{Online Company Portal Info}}` | online portal | 1,050 |
| `{{Customer Support Phone Number}}` | the number on our contact page | 808 |
| `{{Login Page URL}}` | login page | 397 |
| `{{Website URL}}` | our website | 360 |
| `{{Store Location}}` | stores | 317 |
| `{{Account Recovery Page URL}}` | account recovery page | 52 |
| `{{Company Name}}` | our company | 40 |
| `{{Customer Support Email}}` | the address on our contact page | 29 |
| `{{Toll-Free Number}}` | the number on our contact page | 11 |
| `{{Feedback Email Address}}` | the address on our contact page | 8 |
| `{{Live Chat Support}}` | live chat | 8 |
| `{{Password Recovery Page URL}}` | password recovery page | 5 |
| `{{Customer Service Hours}}` | the hours shown on our contact page | 4 |
| `{{Profile Recovery Page URL}}` | profile recovery page | 4 |
| `{{Feedback Email}}` | the address on our contact page | 3 |
| `{{Online Customer Support Channel}}` | online support channel | 3 |
| `{{Contact Method}}` | contact method | 2 |
| `{{Customer Assistance Hours}}` | the hours shown on our contact page | 2 |
| `{{Customer Assistance Phone Number}}` | the number on our contact page | 2 |
| `{{Help Center URL}}` | help center | 2 |
| `{{Password Reset Page URL}}` | password reset page | 2 |
| `{{Product Feedback Email}}` | the address on our contact page | 2 |
| `{{Support Page URL}}` | support page | 2 |
| `{{Access Key Reset Page URL}}` | access key reset page | 1 |
| `{{Business Hours}}` | the hours shown on our contact page | 1 |
| `{{Claims Contact Number}}` | the number on our contact page | 1 |
| `{{Company Phone Number}}` | the number on our contact page | 1 |
| `{{Company Support Channels}}` | support channels | 1 |
| `{{Company Support Page URL}}` | support page | 1 |
| `{{CompanyName}}` | our company | 1 |
| `{{Complaint Hotline Number}}` | the number on our contact page | 1 |
| `{{Customer Assistance Email}}` | the address on our contact page | 1 |
| `{{Customer Assistance Email Address}}` | the address on our contact page | 1 |
| `{{Customer Service Email}}` | the address on our contact page | 1 |
| `{{Customer Service Email Address}}` | the address on our contact page | 1 |
| `{{Customer Service Toll-Free Number}}` | the number on our contact page | 1 |
| `{{Customer Support Hotline}}` | the number on our contact page | 1 |
| `{{Customer Support Opening Time}}` | the opening time shown on our contact page | 1 |
| `{{Customer Support Start Time}}` | the opening time shown on our contact page | 1 |
| `{{Customer Support Toll-Free Number}}` | the number on our contact page | 1 |
| `{{Customer Support Website}}` | our website | 1 |
| `{{Free Customer Support Number}}` | the number on our contact page | 1 |
| `{{Help Center}}` | help center | 1 |
| `{{Key Recovery Page URL}}` | key recovery page | 1 |
| `{{Login URL}}` | login page | 1 |
| `{{Login page URL}}` | login page | 1 |
| `{{Online Store}}` | our online store | 1 |
| `{{PIN Recovery Page URL}}` | PIN recovery page | 1 |
| `{{PIN Reset Page URL}}` | PIN reset page | 1 |
| `{{PIN Retrieval Page URL}}` | PIN retrieval page | 1 |
| `{{Payment Issue Phone Number}}` | the number on our contact page | 1 |
| `{{Platform Login URL}}` | login page | 1 |
| `{{Platform URL}}` | our website | 1 |
| `{{Product Reviews Email}}` | the address on our contact page | 1 |
| `{{Refund Helpline Number}}` | the number on our contact page | 1 |
| `{{Refund Hotline Number}}` | the number on our contact page | 1 |
| `{{Support Channel}}` | support channel | 1 |
| `{{User Key Retrieval Page URL}}` | key retrieval page | 1 |
| `{{User Profile Page URL}}` | profile page | 1 |
| `{{customer_support_phone_number}}` | the number on our contact page | 1 |
| **total** | | **4,318** |

## 4. Rows still rejected

37 rows. Each placeholder below has no honest neutral phrase: any wording would state a duration, a policy, a specific feature, a city, a third-party platform, or a person. The full list with reasons is `configs/cleaning.json` `substitutions.no_neutral_phrase` (47 entries).

| placeholder | rows |
|---|---:|
| `{{Feature 1}}` | 8 |
| `{{Standard Shipping Time}}` | 3 |
| `{{Company Name}}` | 2 |
| `{{Customer Support Phone Number}}` | 2 |
| `{{Delivery Time}}` | 2 |
| `{{ETA}}` | 2 |
| `{{Shipping Cut-off Time}}` | 2 |
| `{{Standard Delivery Time}}` | 2 |
| `{{Account Closure Timeframe}}` | 1 |
| `{{Claims Department}}` | 1 |
| `{{Company Representative Name}}` | 1 |
| `{{Customer Support Hours}}` | 1 |
| `{{Customer Support Ticket Number}}` | 1 |
| `{{Estimated Delivery Time}}` | 1 |
| `{{Min Delivery Time}}` | 1 |
| `{{Number of Days}}` | 1 |
| `{{Online Company Portal Info}}` | 1 |
| `{{Product/Service Defect Refund Time}}` | 1 |
| `{{Review Platform 1}}` | 1 |
| `{{Timeframe}}` | 1 |
| `{{Website URL}}` | 1 |
| `{{proceed to our website and click on the 'Contact Us' button / dial our customer support number / reach out to our live chat support}}` | 1 |
| **total** | **37** |

## 5. Splits

| split | v1 rows | v1 groups | v1 sha256 | v2 rows | v2 groups | v2 sha256 |
|---|---:|---:|---|---:|---:|---|
| `train` | 17,701 | 3,568 | `307c59da350336a7bc603c5b2221043099df828ef55e1d409095868c4d51c6a7` | 20,926 | 3,905 | `934fcc0ac8b1c4f5f342a96b87b778b9a0624c5ad18fba54a2f265f57978b6b2` |
| `val` | 2,477 | 447 | `b5f2e52d0d327cabd7cf8f83097c634c2f1132f6274e344d1677b05f02b304d3` | 2,753 | 486 | `6f35948d7c03678d02a3a931c307da4ad0d33713ad924077c1dd10ad346c2000` |
| `test` | 2,270 | 447 | `ef864aace40157971664c067b12972fddc448ba24729a3a6f8658015faee20af` | 3,085 | 486 | `70e1de8594f7d4903e677797936040e83ad64530a4917a8c986278194eec8bae` |

| file | sha256 | lines |
|---|---|---:|
| `data/v2/audit.json` | `96150e5a41a510f4a61a30e8114ecaa9dfe8105820fb7a10e12015b72ab059ba` | 815 |
| `data/v2/splits.json` | `7ce90bf01ac524f5304f5e7212489e1c86eaeac95bc4acc38743511c19cc7ffb` | 4,899 |
| `data/processed/v2/train.jsonl` | `934fcc0ac8b1c4f5f342a96b87b778b9a0624c5ad18fba54a2f265f57978b6b2` | 20,926 |
| `data/processed/v2/val.jsonl` | `6f35948d7c03678d02a3a931c307da4ad0d33713ad924077c1dd10ad346c2000` | 2,753 |
| `data/processed/v2/test.jsonl` | `70e1de8594f7d4903e677797936040e83ad64530a4917a8c986278194eec8bae` | 3,085 |
| `configs/cleaning.json` | `ebce1b69b84a974713b34c9337a144dbe3676359815958de19c7f5c3701f90e6` | 766 |
| `data/prepare.py` | `db9517c690a29b91c6ce3cf813631e6cd13e88ba39f0235a43fcdd7085ad4780` | 1,209 |
| `tests/test_prepare.py` | `fc5ccd3923f2c27817d5af9dec112a103c6c7749b09d54878cc13e0155b338e2` | 418 |

`data/processed/v2/` is gitignored, like `data/processed/`. Its hashes are recorded here and in `data/v2/splits.json`.

## 6. Leakage and grouping

| | v1 | v2 |
|---|---|---|
| seed | 42 | 42 |
| cosine threshold | 0.86 | 0.86 |
| linkage | average | average |
| group_id intersection empty | True | True |
| normalized-instruction intersection empty | True | True |
| groups straddling a split | 0 | 0 |
| near-collapse intents (>=50%) | 1 | 0 |
| intents missing a split | 0 | 0 |
| grouping pinned to | `24ab0d9` | none (re-embedded and re-clustered) |

Nearest cross-split cosine, within intent, train vs val and test:

| | v1 | v2 |
|---|---:|---:|
| n | 4,747 | 5,838 |
| min | 0.4776 | 0.5057 |
| p50 | 0.8923 | 0.8959 |
| p95 | 0.9387 | 0.9427 |
| max | 0.9708 | 0.9825 |
| n_at_or_above_threshold | 3,693 | 4,683 |
| share at or above 0.86 | 77.8% | 80.2% |

v1's grouping was pinned to `24ab0d9` because its kept-id set was frozen. v2's kept-id set is larger, so the pin cannot hold: v2 re-embeds all 26,764 rows with the same MiniLM model, re-clusters at the same 0.86 average-linkage threshold, and re-splits with the same seed 42. Group ids and split membership are therefore not comparable row for row between v1 and v2.

## 7. Judgement calls

1. **Attribution.** A recovered row often carries several rejecting placeholders. Section 3 credits the first one encountered, instruction before response. Substitutions applied (9,654) exceed rows recovered (4,318) for the same reason.
2. **One phrase serves a family.** All 17 phone-shaped placeholders map to "the number on our contact page", all 13 email-shaped ones to "the address on our contact page", all 6 hours-shaped ones to "the hours shown on our contact page". A per-placeholder wording would assert more than the model knows.
3. **`{{Toll-Free Number}}` loses the word toll-free.** "our toll-free number is the number on our contact page" reads oddly in 11 rows. Naming it toll-free in the phrase would assert a fact about the line.
4. **`{{Company Name}}` becomes "our company", and the determiner before it is dropped.** "with your {{Company Name}} account" becomes "with our company account", not "with your our company account". 40 rows. The possessive shifts from the customer to the company; nothing false is asserted.
5. **`{{Store Location}}` becomes the plural "stores".** Two of its three frames are "one of our {{Store Location}}". 317 rows.
6. **Determiner handling is a rule, not a table.** A phrase that starts with the/our/your/a/an drops a trailing determiner from the text before it ("during our " + "the hours ..." -> "during the hours ..."), and a duplicated leading word is dropped ("on our " + "our website" -> "on our website"). One placeholder, `{{Website URL}}`, also consumes a trailing " at" ("on our website at {{Website URL}}" -> "on our website"); that regex is in `configs/cleaning.json`.
7. **Phrases are machine-checked.** `check_substitution_phrase` refuses any phrase containing a digit, a URL, an `@`, a currency symbol, a spelled-out duration, or the words within / guarantee / policy / free of charge / refundable / 24/7 / always. It runs at config load, so a bad phrase fails the run, not the eval.

## 8. What I did not do

1. **The 300 to 500 admission rows.** Not in this node; they wait for Astra's plan.
2. **A pre-existing double-determiner defect in `data/prepare.py`, untouched.** v1's placeholder map gives `{{Account Type}}` the wording "your account type", and `replace_placeholders` only consumes a preceding "the", never a preceding "your" or "our". So "switch your {{Account Type}}" already reads "switch your your account type" in v1. It affects 1,771 of v1's 22,448 kept rows and 2,015 of v2's 26,764. It is not caused by substitution: of the 4,318 recovered rows, 269 carry it and 0 of those trace to a substitution phrase. Fixing it would change v1's default output, which this node must keep byte-identical, and would be a second change confounded with the data fix. Flagged for a separate node.
3. **Nothing under `train/`, `eval/` or `configs/train*.yaml`.**

## 9. The v1 invariant, verified

`data/prepare.py`'s default output is byte-identical to `HEAD` before this node. Both versions were run over all 26,872 raw rows, and the sha256 of the concatenated `id / cleaned instruction / cleaned response / applied rule ids / reject id` for every row is:

```
HEAD    285d60849f0c470cc2012b2cd65ecfdcf15a44d092680460e9af4bfc84c33ca7
working 285d60849f0c470cc2012b2cd65ecfdcf15a44d092680460e9af4bfc84c33ca7
```

Rule counts and `placeholder_frames` also match `data/audit.json` exactly. `uv run python data/prepare.py --audit-only --strict` prints `audit-only ok train=17701 val=2477 test=2270` and `strict: hashes and intersections match`, unchanged. `tests/test_prepare.py::test_default_mode_split_hashes_match_the_seal` asserts the default split sha256 equal `eval/SEAL.json` `split_sha256`.



## 10. Admission rows (V2-A1, A2), 2026-09-08 01:30 IST

Author: `grok-4.5-build` through `grok -p` (decision 11), stateless call from an empty cwd, JSON schema, `--verbatim`, no tools, no web; the Flash author of decision 5 was abandoned after five runs died silent on this Mac (18:44 to 19:09 IST Mon). Generator `tools/admissions.py` at `4b6cfc3`; every review line carries the model id, the batch id and the prompt sha256.

| stage | rows | file (sha256 prefix) |
|---|---:|---|
| model calls (batches), all runs | 264 | `data/v2/admission_review.jsonl` (ae1825198be658bb) |
| lint rejects, all runs | 362 | same; top: batch:duplicate_6gram_cross_cell 84, query:time_or_duration 70, answer:price_word 64, answer:time_or_duration 41, query:price_word 41 |
| accepted by lint and cross-cell 6-gram dedup | 340 | `data/v2/admissions_raw.jsonl` (6f7d6058eb46cd2b) |
| A2 accepted / rejected (`grok-4.5-build`, eight checks, `tools/admission_review.py`) | 259 / 81 | `data/v2/admission_review_a2.jsonl` (2e86d23d2aee1cf7); top reasons: source_not_named 34, actions_multiple 25, intent_mismatch 9, policy_claim 8 |
| leakage: quarantined (cosine >= 0.80 or shared 6-gram against `challenge.jsonl`, `dev.jsonl`, `challenge_v2.jsonl`, v2 val and test) | 53 | `data/v2/admissions_quarantine.jsonl`; reasons {"answer:cosine>=0.80": 12, "answer:shared_6gram": 1, "query:cosine>=0.80": 46, "query:shared_6gram": 4}; max cosine 0.9627 |
| assembled, flagged `SYNTH_ADMISSION`, train only, exempt from the cap | 206 | `data/v2/admissions.jsonl` (0f326ff937c9711a) |

Per intent, assembled: cancel_order 11, change_order 8, change_shipping_address 5, check_cancellation_fee 6, check_invoice 10, check_payment_methods 8, check_refund_policy 14, complaint 3, contact_customer_service 16, contact_human_agent 7, create_account 8, delete_account 9, delivery_options 6, delivery_period 7, edit_account 5, get_invoice 5, get_refund 6, newsletter_subscription 5, payment_issue 10, place_order 6, recover_password 8, registration_problems 7, review 8, set_up_shipping_address 1, switch_account 2, track_order 12, track_refund 13. Every intent has at least one row (decision 10); the 440 target and the 300-row band were not reached, and no row was edited to get closer. Query styles in the raw set: anger 47, no_identifier 36, ordinary 167, two_requests 43, typos 47.

Closer audit (`tools/closer_audit.py`, rule pre-registered 18:46 IST Mon): the first 307 rows read CONCENTRATED on intent span (the have-to-hand checklist and the "here is a message you can send" opener in 6 to 9 intents). Remedy as pre-registered: the scenario line assigns the closing step per example and the have-to-hand list may name only that intent's facts (`4b6cfc3`); 54 cells regenerated in round one, 9 in round two (decision 13 caps it at two rounds). Final raw set: 340 distinct closing sentences of 340 rows, NOT_CONCENTRATED. Two prompt hashes exist in the review lines, one per prompt version.

Lint exemption (decision 12): `fee`, `fees`, `charge`, `charges` for `check_cancellation_fee` and `password`, `passwords` for `recover_password`, because both intents closed at zero when their own noun was banned; the A2 reviewer rejects an answer that asks for a credential.

Split with admissions: `wrote train=21132 val=2753 test=3085 groups=4877`; `data/prepare.py --audit-only --out data/v2 --strict` passes; the train record in `data/v2/splits.json` now lists the admission group ids (prepare.py, this node). v1 default output unchanged: `audit-only ok train=17701 val=2477 test=2270`, `strict: hashes and intersections match`.
