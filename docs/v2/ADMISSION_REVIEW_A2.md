# V2-A2: admission-row review

Reviewer: `grok-4.5-build` via `grok -p`, restricted prompt (`tools/admission_review.py`), one stateless call per batch. Input `data/v2/admissions_raw.jsonl` sha256 `6f7d6058eb46cd2b629bef688d0885ea2147563c399f27390cd1c3e344c98b77`, 340 rows. Verdicts in `data/v2/admission_review_a2.jsonl`.

## Verdicts

accept 259, reject 81, review_failed 0

## Accepted rows per intent

| intent | target | accepted |
|---|---:|---:|
| cancel_order | 24 | 14 |
| change_order | 12 | 8 |
| change_shipping_address | 12 | 8 |
| check_cancellation_fee | 24 | 6 |
| check_invoice | 24 | 14 |
| check_payment_methods | 24 | 17 |
| check_refund_policy | 24 | 18 |
| complaint | 12 | 3 |
| contact_customer_service | 24 | 16 |
| contact_human_agent | 12 | 7 |
| create_account | 8 | 8 |
| delete_account | 12 | 9 |
| delivery_options | 24 | 16 |
| delivery_period | 24 | 11 |
| edit_account | 8 | 5 |
| get_invoice | 12 | 5 |
| get_refund | 24 | 10 |
| newsletter_subscription | 8 | 6 |
| payment_issue | 24 | 10 |
| place_order | 8 | 6 |
| recover_password | 12 | 8 |
| registration_problems | 12 | 11 |
| review | 8 | 8 |
| set_up_shipping_address | 8 | 6 |
| switch_account | 8 | 2 |
| track_order | 24 | 12 |
| track_refund | 24 | 15 |

Intents at zero: none

## Style coverage (accepted rows)

| style | rows |
|---|---:|
| ordinary | 139 |
| typos | 40 |
| anger | 30 |
| two_requests | 24 |
| no_identifier | 26 |

## Reject reasons

| reason | rows |
|---|---:|
| source_not_named | 34 |
| actions_multiple | 25 |
| intent_mismatch | 9 |
| policy_claim | 8 |
| second_request_ignored | 6 |
| over_refusal | 6 |
| admission_unjustified | 5 |
| action_missing | 5 |
| grammar | 3 |
| style_mismatch | 3 |
| claimed_action | 2 |
| credential_request | 1 |

## Independent closer audit rerun

```
rows=340 distinct_closing_sentences=340
closer kinds:
  where_to_look          98   28.8%
  draft_the_message      23    6.8%
  have_to_hand           39   11.5%
  unclassified          183
top closing sentences:
     1 rows /  1 intents  look for a profile or settings section near your signed-in name there you should
     1 rows /  1 intents  open your recent orders list select the order you want to adjust and look for a 
     1 rows /  1 intents  before you go write down the product name any size or color choice you want and 
     1 rows /  1 intents  open the order details page and look for the refund or return section you should
     1 rows /  1 intents  before you continue gather your order confirmation and the return reference so y
top closing 6-grams:
     6 rows /  2 intents  and the names of the items
     6 rows /  2 intents  order reference and the delivery address
     5 rows /  4 intents  so you can confirm you are
     5 rows /  5 intents  here is a short note you
     5 rows /  5 intents  is a short note you can
verdict: NOT_CONCENTRATED
```
