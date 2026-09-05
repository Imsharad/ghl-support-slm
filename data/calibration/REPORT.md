# Paraphrase threshold calibration

Generated: 2026-09-05 22:46 IST

Commands:

- `uv run python data/calibrate_threshold.py --sample`
- `uv run python data/calibrate_threshold.py --report`

Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (cached). Seed **42**. Normalize `lower_strip_punct_keep_neg_num`: casefold, expand `n't` to `not`, replace `{{placeholders}}` with `ph`, strip other punctuation, keep digits. Pairs are within-intent only.

Sample: **40** pairs across six cosine bands (7,7,7,7,6,6). Labels: same_scenario = same request and same specifics, only wording differs. Different specifics inside the same intent (cannot-afford vs ordered-twice, missing order id vs generic how-to) are false.

Labels: **35** same, **5** different, **2** flagged as possible intent-label errors.

## Chosen threshold

**0.86**. lowest T with zero labelled-different pairs at cosine >= T (band below T was not majority-different on this sample).

Grouping for B1 (union-find, within intent): (1) exact match on normalized instruction, (2) response template family = identical string after `{{...}}` -> `{{SLOT}}` then the same normalize, (3) MiniLM cosine >= threshold on normalized instructions. Never break a group at split time.

Residual risk: 40 labelled pairs cannot prove zero leakage. Paraphrases continue down into the 0.70-0.85 bands (recall at 0.86 is 0.46 on this sample), so the band below T is mostly same, not mostly different. Union-find is transitive: a 0.86 edge chain can merge a whole intent-shaped cloud even when distant pairs would not have been labelled same. Exact-match and template-family close the obvious holes. Cross-split nearest-neighbour audit is B1's job.

## Threshold table

Command: `uv run python data/calibrate_threshold.py --report`

Positive class = `same_scenario`. Predict same if cosine >= T.

| T | TP | FP (different above) | FN (same below) | TN | precision | recall | n >= T |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.70 | 35 | 5 | 0 | 0 | 0.88 | 1.00 | 40 |
| 0.75 | 29 | 4 | 6 | 1 | 0.88 | 0.83 | 33 |
| 0.80 | 23 | 3 | 12 | 2 | 0.88 | 0.66 | 26 |
| 0.85 | 18 | 1 | 17 | 4 | 0.95 | 0.51 | 19 |
| 0.86 **chosen** | 16 | 0 | 19 | 5 | 1.00 | 0.46 | 16 |
| 0.87 | 15 | 0 | 20 | 5 | 1.00 | 0.43 | 15 |
| 0.88 | 15 | 0 | 20 | 5 | 1.00 | 0.43 | 15 |
| 0.89 | 13 | 0 | 22 | 5 | 1.00 | 0.37 | 13 |
| 0.90 | 12 | 0 | 23 | 5 | 1.00 | 0.34 | 12 |
| 0.92 | 8 | 0 | 27 | 5 | 1.00 | 0.23 | 8 |
| 0.95 | 6 | 0 | 29 | 5 | 1.00 | 0.17 | 6 |

## The 40 labels

Command: `uv run python data/calibrate_threshold.py --report`

| id | band | cosine | intent | same | intent_wrong | reason | a | b |
|---|---|---:|---|---|---|---|---|---|
| p-01 | 0.70-0.75 | 0.722 | `create_account` | false | false | Both create-account, but A is opening for dad with Account Category; B is a generic can-I-open with Account Type. Different beneficiary and slot. | i need assistance to open a {{Account Category}} account for my dad | can I open a {{Account Type}} account? |
| p-02 | 0.70-0.75 | 0.745 | `payment_issue` | true | false | Same request: report a payment problem. Online vs generic error is wording, no extra specifics. | i need assistance informing of an issue with online payments | need assistance reporting payment erroors |
| p-03 | 0.70-0.75 | 0.730 | `get_refund` | true | false | Same how-to get money back; refunds vs reimbursements is wording. | how do i demand refunds of my money | what do i have to do to demand reimbursements of my money |
| p-04 | 0.70-0.75 | 0.738 | `track_order` | true | false | Same track-order on {{Order Number}}; how vs where is wording. | what do i need to do to see order {{Order Number}} status | where can i see the current status of purchase {{Order Number}} |
| p-05 | 0.70-0.75 | 0.713 | `change_shipping_address` | true | false | Same change of delivery/shipping address; edit vs update is wording. | I want supports trying to edit the delivery address | i want supports trying to update my shippingaddress |
| p-06 | 0.70-0.75 | 0.734 | `delivery_period` | true | false | Same delivery ETA request; purchase vs order, when vs how soon. | I want help seeing when will my purchase arrive | I want help seeing how soon can I expect my goddamn order |
| p-07 | 0.70-0.75 | 0.723 | `newsletter_subscription` | true | false | Same newsletter signup; sign up vs subscribe. | I am trying to sign up to the company newsletter | I need to subscribe to your newsletter |
| p-08 | 0.75-0.80 | 0.790 | `track_refund` | true | false | Same track-compensation/refund status; cannot-see-updates is the same ask. | help me checking the goddamn status of the compensation | I cannot see if there are any updates on my compensation |
| p-09 | 0.75-0.80 | 0.787 | `review` | true | false | Same leave-feedback-about-company; B names email as the channel, not a different scenario. | assistance to send some feedback about ur company | is there an e-mail toleave feedback for your company? |
| p-10 | 0.75-0.80 | 0.763 | `change_order` | false | false | Same order id and change_order intent, but A is swap an item and B is generic edit. Different operation. | how can i swap something of  order {{Order Number}} | help with editing order {{Order Number}} |
| p-11 | 0.75-0.80 | 0.779 | `complaint` | true | false | Same file-a-complaint; customer vs consumer is wording. | I need to file a customer complaint against your company | help to file a consumer complaint |
| p-12 | 0.75-0.80 | 0.752 | `check_payment_methods` | true | false | Same list payment options/methods. | I need to see the payment options, can you help me? | I want to see your payment methods, how to do it? |
| p-13 | 0.75-0.80 | 0.782 | `get_refund` | true | false | Same how-to get a refund of my money. | I do notknow how to get refunds of my money | I do not know what I have to do to get a refund |
| p-14 | 0.75-0.80 | 0.774 | `contact_human_agent` | true | false | Same reach an operator; how-to vs need-help is wording. | what do I need to do to contact an operator? | i need assistance to speak to an operator |
| p-15 | 0.80-0.85 | 0.830 | `track_order` | true | false | Same see status of order {{Order Number}}. | how can I see order {{Order Number}} current status? | I ma trying to see the status of order {{Order Number}} |
| p-16 | 0.80-0.85 | 0.825 | `contact_customer_service` | true | false | Same call customer assistance; can-I vs how-to. | can i call customer assistance | what do I need to do to call customer assistance? |
| p-17 | 0.80-0.85 | 0.826 | `set_up_shipping_address` | true | false | Same submit a delivery address; issue-with-new is still that task. | I want help submitting my delivery address | i ahve an issue submitting a new delivery address |
| p-18 | 0.80-0.85 | 0.805 | `check_refund_policy` | true | false | Same refund-policy question: in what cases can I request a refund. | need help seeing in what cases can I ask for a refund | help me see in what case can i request the bloody refunds |
| p-19 | 0.80-0.85 | 0.812 | `change_order` | false | false | A is generic modify order; B is switch a product on that order. Different operation. | how to modify order {{Order Number}} | need assistance to switch a product of order {{Order Number}} |
| p-20 | 0.80-0.85 | 0.817 | `get_invoice` | true | false | Same get/send bills from {{Person Name}}. | need help to get the bill from {{Person Name}} | send me bills from {{Person Name}} |
| p-21 | 0.80-0.85 | 0.842 | `switch_account` | false | true | A is switch to {{Account Type}}; B is use that account. Change vs operate. | switch to {{Account Type}} account | help to use the {{Account Type}} account |
| p-22 | 0.85-0.90 | 0.868 | `contact_human_agent` | true | false | Same talk to a human agent. | how can I talk with a human agent? | I want help speaking with a human agent |
| p-23 | 0.85-0.90 | 0.891 | `check_payment_methods` | true | false | Same list allowed payment methods. | I want to check what payment methods are allowed, help me | can you show me what payment methods are allowed ? |
| p-24 | 0.85-0.90 | 0.885 | `contact_customer_service` | true | false | Same customer-assistance calling hours. | see what hours I can call customer assistance | I would like to see what hours I can call customer support |
| p-25 | 0.85-0.90 | 0.880 | `edit_account` | true | false | Same edit details on {{Account Category}} account; changing vs modify. | changing data on {{Account Category}}  account | modify details on {{Account Category}} account |
| p-26 | 0.85-0.90 | 0.858 | `delivery_options` | true | false | Same see shipment methods; how vs where. | can you help me to check what shipment methods I have? | where to see the methods for shipment? |
| p-27 | 0.85-0.90 | 0.857 | `switch_account` | false | true | A is switch to {{Account Type}}; B is use that account (typo touse). Same split as p-21. | how to switch to the {{Account Type}} account | need help touse the {{Account Type}} account |
| p-28 | 0.85-0.90 | 0.851 | `change_order` | true | false | Both swap an item/something on order {{Order Number}}. | I need to swap an item of order {{Order Number}}, help me | help to swap something of order {{Order Number}} |
| p-29 | 0.90-0.95 | 0.921 | `change_order` | true | false | Same edit/modify purchase {{Order Number}}. | I want help to edit purchase {{Order Number}} | I want to modify purchase {{Order Number}}, how do I do it? |
| p-30 | 0.90-0.95 | 0.914 | `check_cancellation_fee` | true | false | Same check termination penalties; early is extra wording, not a different fee. | want help to check the early termination penalties | i want assistance checking the termination penalties |
| p-31 | 0.90-0.95 | 0.904 | `change_shipping_address` | true | false | Same edit the address; issues vs assistance is wording. | i have issues editing the address | assistance trying to edit the address |
| p-32 | 0.90-0.95 | 0.902 | `contact_customer_service` | true | false | Same check hours to contact customer service. | can uhelp me see what hours i can contact customer service | can i check what hours i can contact customer service |
| p-33 | 0.90-0.95 | 0.932 | `recover_password` | true | false | Same recover/retrieve PIN of the profile. | want assistance to retrieve the pin code of my user profile | I need assistance to recover the PIN code of my profile |
| p-34 | 0.90-0.95 | 0.905 | `contact_human_agent` | true | false | Same how to speak to an agent. | i dont know how to speak to an agent | how to speak with an agent |
| p-35 | 0.95-1.0 | 0.967 | `create_account` | true | false | Same create a gold account; how vs what-to-do. | I do not know how I can create a gold account | i do not know what to do to create a gold account |
| p-36 | 0.95-1.0 | 0.955 | `track_refund` | true | false | Same check news/updates on the rebate. | could uhelp me to know if there are any news on my rebate | help me check if there are any news on the rebate |
| p-37 | 0.95-1.0 | 0.972 | `delivery_period` | true | false | Same how-soon-can-I-expect the product. | help me checking how soon can I expect my product | assistance to check how soon can I expect the product |
| p-38 | 0.95-1.0 | 0.950 | `check_payment_methods` | true | false | Same see allowed payment methods; trying vs how-to. | I am trying to see the allowed payment methods | how to see the allowed payment methods |
| p-39 | 0.95-1.0 | 0.977 | `review` | true | false | Same leave a company review; leave vs leaving. | leave review for your company | leaving review for your company |
| p-40 | 0.95-1.0 | 0.954 | `set_up_shipping_address` | true | false | Same set up the secondary delivery address; typo howq. | help me set up the secondary delivery address | howq can i set up the secondary delivery address |

## Groups at the chosen threshold

Command: `uv run python data/calibrate_threshold.py --report`

Union-find with exact-match + template-family + cosine >= 0.86. `collapsed` = one group for the whole intent. `near_collapse` = largest group holds >= 80% of the intent's rows (80/10/10 by group count will still dump most rows into whichever split draws that group).

| intent | rows | groups | largest | share | singletons | collapsed | near |
|---|---:|---:|---:|---:|---:|---|---|
| `cancel_order` | 998 | 39 | 908 | 91% | 23 | false | true |
| `change_order` | 997 | 74 | 741 | 74% | 58 | false | false |
| `change_shipping_address` | 973 | 91 | 543 | 56% | 83 | false | false |
| `check_cancellation_fee` | 950 | 76 | 329 | 35% | 62 | false | false |
| `check_invoice` | 1000 | 78 | 245 | 24% | 60 | false | false |
| `check_payment_methods` | 999 | 64 | 934 | 94% | 61 | false | true |
| `check_refund_policy` | 997 | 68 | 380 | 38% | 55 | false | false |
| `complaint` | 1000 | 122 | 619 | 62% | 107 | false | false |
| `contact_customer_service` | 1000 | 94 | 453 | 45% | 82 | false | false |
| `contact_human_agent` | 999 | 191 | 313 | 31% | 171 | false | false |
| `create_account` | 997 | 109 | 412 | 41% | 68 | false | false |
| `delete_account` | 995 | 91 | 457 | 46% | 72 | false | false |
| `delivery_options` | 995 | 35 | 355 | 36% | 14 | false | false |
| `delivery_period` | 999 | 97 | 629 | 63% | 89 | false | false |
| `edit_account` | 1000 | 114 | 317 | 32% | 83 | false | false |
| `get_invoice` | 999 | 64 | 254 | 25% | 46 | false | false |
| `get_refund` | 997 | 83 | 187 | 19% | 68 | false | false |
| `newsletter_subscription` | 999 | 63 | 931 | 93% | 56 | false | true |
| `payment_issue` | 999 | 55 | 923 | 92% | 46 | false | true |
| `place_order` | 998 | 172 | 391 | 39% | 146 | false | false |
| `recover_password` | 995 | 114 | 330 | 33% | 90 | false | false |
| `registration_problems` | 999 | 74 | 889 | 89% | 56 | false | true |
| `review` | 997 | 143 | 780 | 78% | 124 | false | false |
| `set_up_shipping_address` | 997 | 71 | 915 | 92% | 63 | false | true |
| `switch_account` | 1000 | 91 | 337 | 34% | 66 | false | false |
| `track_order` | 995 | 54 | 751 | 76% | 36 | false | false |
| `track_refund` | 998 | 31 | 385 | 39% | 10 | false | false |

Fully collapsed intents: none.

Near-collapse (>=80% of rows in one group): `cancel_order` 908/998, `check_payment_methods` 934/999, `newsletter_subscription` 931/999, `payment_issue` 923/999, `registration_problems` 889/999, `set_up_shipping_address` 915/997.

Total groups: **2358**. Largest group overall: **934** (check_payment_methods).

Same grouping rules at nearby cuts (chaining sensitivity):

| T | total groups | max largest | near-collapse intents |
|---:|---:|---:|---|
| 0.86 | 2358 | 934 | `cancel_order`, `check_payment_methods`, `newsletter_subscription`, `payment_issue`, `registration_problems`, `set_up_shipping_address` |
| 0.90 | 4000 | 873 | `cancel_order`, `payment_issue`, `registration_problems`, `set_up_shipping_address` |
| 0.95 | 9827 | 467 | none |

