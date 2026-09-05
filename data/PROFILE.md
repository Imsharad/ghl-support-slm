# Bitext dataset profile

Generated: 2026-09-05 22:36 IST

Commands:

- `uv run python data/fetch.py` — download/pin (idempotent)
- `uv run python data/fetch.py --profile` — this file, `data/intents.json`

Source: Hugging Face `bitext/Bitext-customer-support-llm-chatbot-training-dataset` revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443` (Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv). Local copy `data/raw/bitext.csv` (gitignored). SHA-256 `6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434`.

License: CDLA-Sharing-1.0 (https://cdla.dev/sharing-1-0/). Publishing the CSV requires sharing under the same agreement; computational results do not. Raw file is gitignored; this pin records how to re-fetch it.

## Row count

Command: `uv run python data/fetch.py --profile`

- rows: **26872**
- expected: **26872**
- match: **yes**
- columns: `flags, instruction, category, intent, response`

### Mismatches vs assignment card

- **Category-count mismatch:** 11 distinct categories; expected 10.

### Per-intent counts

Command: `uv run python data/fetch.py --profile`

Distinct: **27** (expected 27; MATCHES).

| name | rows | share |
|---|---:|---:|
| `check_invoice` | 1000 | 3.72% |
| `complaint` | 1000 | 3.72% |
| `contact_customer_service` | 1000 | 3.72% |
| `edit_account` | 1000 | 3.72% |
| `switch_account` | 1000 | 3.72% |
| `check_payment_methods` | 999 | 3.72% |
| `contact_human_agent` | 999 | 3.72% |
| `delivery_period` | 999 | 3.72% |
| `get_invoice` | 999 | 3.72% |
| `newsletter_subscription` | 999 | 3.72% |
| `payment_issue` | 999 | 3.72% |
| `registration_problems` | 999 | 3.72% |
| `cancel_order` | 998 | 3.71% |
| `place_order` | 998 | 3.71% |
| `track_refund` | 998 | 3.71% |
| `change_order` | 997 | 3.71% |
| `check_refund_policy` | 997 | 3.71% |
| `create_account` | 997 | 3.71% |
| `get_refund` | 997 | 3.71% |
| `review` | 997 | 3.71% |
| `set_up_shipping_address` | 997 | 3.71% |
| `delete_account` | 995 | 3.70% |
| `delivery_options` | 995 | 3.70% |
| `recover_password` | 995 | 3.70% |
| `track_order` | 995 | 3.70% |
| `change_shipping_address` | 973 | 3.62% |
| `check_cancellation_fee` | 950 | 3.54% |

### Per-category counts

Command: `uv run python data/fetch.py --profile`

Distinct: **11** (expected 10; DIFFERS from expected 10).

| name | rows | share |
|---|---:|---:|
| `ACCOUNT` | 5986 | 22.28% |
| `ORDER` | 3988 | 14.84% |
| `REFUND` | 2992 | 11.13% |
| `INVOICE` | 1999 | 7.44% |
| `CONTACT` | 1999 | 7.44% |
| `PAYMENT` | 1998 | 7.44% |
| `FEEDBACK` | 1997 | 7.43% |
| `DELIVERY` | 1994 | 7.42% |
| `SHIPPING` | 1970 | 7.33% |
| `SUBSCRIPTION` | 999 | 3.72% |
| `CANCEL` | 950 | 3.54% |

The assignment/card list of 10 omits `CONTACT` (1999 rows: `contact_customer_service` + `contact_human_agent`). CSV names also differ from the card: `CANCEL` = card `CANCELLATION_FEE`, `SHIPPING` = `SHIPPING_ADDRESS`, `SUBSCRIPTION` = `NEWSLETTER`. Each intent maps to exactly one category.

## Length distributions

Command: `uv run python data/fetch.py --profile`

Words = `str.split()` whitespace tokens. Qwen tokens = `Qwen/Qwen2.5-1.5B-Instruct` via `transformers.AutoTokenizer`, `add_special_tokens=False`.

| series | p50 | p90 | p99 | max | mean |
|---|---:|---:|---:|---:|---:|
| instruction words | 9 | 12 | 14 | 16 | 8.7 |
| response words | 90 | 173 | 300 | 402 | 104.8 |
| instruction Qwen tokens | 10 | 14 | 19 | 24 | 10.1 |
| response Qwen tokens | 104 | 214 | 358 | 478 | 125.2 |
| full ChatML Qwen tokens | 173 | 282 | 428 | 548 | 193.4 |

Full ChatML = native Qwen2.5 template with one system turn (exact `configs/prompt.txt` text), user = instruction, assistant = response, `add_generation_prompt=False`. This is the training example. Rows with total tokens > 512 (train max length): **10** / 26872 (0.04%).

## Exact duplicates

Command: `uv run python data/fetch.py --profile`

| field | unique values | values with dups | rows in dup groups | extra rows beyond first |
|---|---:|---:|---:|---:|
| instruction | 24635 | 989 | 3226 | 2237 |
| response | 26870 | 2 | 4 | 2 |
| full row (all columns) | 26872 | 0 | 0 | 0 |

## Flags column

Command: `uv run python data/fetch.py --profile`

Bitext Language Generation Tags. Each `flags` value is a string of letters; a row can carry several. Source: https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset#language-generation-tags (dataset card, retrieved 2026-09-05).

| letter | meaning (Bitext) | rows with letter |
|---|---|---:|
| M | Morphological variation (inflectional and derivational) | 4920 |
| L | Semantic variations (synonyms, hyphens, compounding) | 24115 |
| B | Basic syntactic structure | 26872 |
| I | Interrogative structure | 7839 |
| C | Coordinated syntactic structure | 2646 |
| N | Negation | 463 |
| P | Politeness variation | 1329 |
| Q | Colloquial variation | 8968 |
| W | Offensive language | 1288 |
| K | Keyword mode | 2227 |
| E | Use of abbreviations | 1882 |
| Z | Errors and Typos | 5286 |

Documented by Bitext as not used in this dataset: D (Indirect speech), G (Regional variations), R (Respect structures), Y (Code switching).

Unknown letters not in the Bitext tag list: S=417, V=77.

Distinct flag combinations: **394**.

Top 15 combinations:

| flags | rows |
|---|---:|
| `BL` | 5212 |
| `BLQ` | 2467 |
| `BIL` | 2138 |
| `BLM` | 1297 |
| `BILQ` | 1057 |
| `BLQZ` | 970 |
| `BLZ` | 902 |
| `BKL` | 862 |
| `BLMQ` | 600 |
| `BEL` | 533 |
| `BILM` | 521 |
| `BCL` | 484 |
| `BCIL` | 427 |
| `BILQZ` | 412 |
| `BILP` | 363 |

## Placeholder tokens in responses

Command: `uv run python data/fetch.py --profile`

Pattern: `{{...}}` (no nested braces). Counts are occurrence totals across all response strings, not distinct rows.

Distinct placeholders: **385**. Total occurrences: **35772**. 50 names occur >= 10 times; 306 names occur <= 3 times (free-typed variants, not a closed inventory). B1 should treat the long tail as noise.

| placeholder | occurrences |
|---|---:|
| `{{Order Number}}` | 5122 |
| `{{Account Type}}` | 4436 |
| `{{Account Category}}` | 3080 |
| `{{Online Order Interaction}}` | 2699 |
| `{{Customer Support Phone Number}}` | 2635 |
| `{{Website URL}}` | 2534 |
| `{{Customer Support Hours}}` | 2325 |
| `{{Invoice Number}}` | 1513 |
| `{{Online Company Portal Info}}` | 1055 |
| `{{Tracking Number}}` | 896 |
| `{{Date Range}}` | 894 |
| `{{Client Last Name}}` | 712 |
| `{{Salutation}}` | 706 |
| `{{Settings}}` | 625 |
| `{{Delivery City}}` | 606 |
| `{{Refund Amount}}` | 563 |
| `{{Delivery Country}}` | 504 |
| `{{Profile}}` | 490 |
| `{{Account Change}}` | 472 |
| `{{Upgrade Account}}` | 448 |
| `{{Login Page URL}}` | 397 |
| `{{Currency Symbol}}` | 373 |
| `{{Person Name}}` | 362 |
| `{{Store Location}}` | 325 |
| `{{Forgot Password}}` | 219 |
| `{{Order Status}}` | 187 |
| `{{Customer Support Email}}` | 174 |
| `{{Profile Type}}` | 140 |
| `{{Order Tracking}}` | 79 |
| `{{Forgot PIN}}` | 75 |
| `{{Client Name}}` | 60 |
| `{{Forgot Access Key}}` | 54 |
| `{{Account Recovery Page URL}}` | 52 |
| `{{Money Amount}}` | 50 |
| `{{Company Name}}` | 45 |
| `{{Account Recovery}}` | 36 |
| `{{Security}}` | 34 |
| `{{Profile Settings}}` | 30 |
| `{{Cancel Purchase}}` | 28 |
| `{{Forgot Key}}` | 25 |
| `{{Account Recovery Page}}` | 24 |
| `{{Reset PIN}}` | 21 |
| `{{Client First Name}}` | 18 |
| `{{Purchase History}}` | 14 |
| `{{Company Account}}` | 13 |
| `{{Live Chat Support}}` | 13 |
| `{{Toll-Free Number}}` | 11 |
| `{{tracking number}}` | 10 |
| `{{order number}}` | 10 |
| `{{PIN Code}}` | 10 |
| `{{Reset Password}}` | 9 |
| `{{Track Order}}` | 9 |
| `{{Client Full Name}}` | 8 |
| `{{Feedback Email Address}}` | 8 |
| `{{Feature 1}}` | 8 |
| `{{Feature 2}}` | 8 |
| `{{Feature 3}}` | 8 |
| `{{Company}}` | 7 |
| `{{PIN Settings}}` | 7 |
| `{{PIN Recovery}}` | 7 |
| `{{Reset Key}}` | 6 |
| `{{Reset Access Key}}` | 6 |
| `{{Password Reset Page}}` | 6 |
| `{{Refund Processing Time}}` | 5 |
| `{{Customer Service Email}}` | 5 |
| `{{PIN Management}}` | 5 |
| `{{Privacy}}` | 5 |
| `{{Password Recovery Page URL}}` | 5 |
| `{{Password}}` | 5 |
| `{{PIN Retrieval}}` | 5 |
| `{{Customer Service Hours}}` | 4 |
| `{{Contact Method}}` | 4 |
| `{{Online Customer Support Channel}}` | 4 |
| `{{Forgot Pin Code}}` | 4 |
| `{{Forgot Account Key}}` | 4 |
| `{{Forgot Profile Key}}` | 4 |
| `{{Submit}}` | 4 |
| `{{PIN}}` | 4 |
| `{{Profile Recovery Page URL}}` | 4 |
| `{{Customer Support Team}}` | 3 |
| `{{Date}}` | 3 |
| `{{Account Number}}` | 3 |
| `{{Customer Service Email Address}}` | 3 |
| `{{Standard Shipping Time}}` | 3 |
| `{{Expedited Shipping Time}}` | 3 |
| `{{Delivery Time}}` | 3 |
| `{{PIN Code Retrieval}}` | 3 |
| `{{Retrieve PIN}}` | 3 |
| `{{Reset User Key}}` | 3 |
| `{{Security & Privacy}}` | 3 |
| `{{PIN Code Recovery}}` | 3 |
| `{{Forgot User Key}}` | 3 |
| `{{Recover PIN}}` | 3 |
| `{{User Account Settings}}` | 3 |
| `{{PIN Reset}}` | 3 |
| `{{User Account Recovery}}` | 3 |
| `{{Account Security}}` | 3 |
| `{{Profile Recovery}}` | 3 |
| `{{Feedback Email}}` | 3 |
| `{{Switch User}}` | 3 |
| `{{Purchase Details}}` | 3 |
| `{{Rebate Tracking Number}}` | 3 |
| `{{Cancellation Policy}}` | 2 |
| `{{Refund Policy}}` | 2 |
| `{{My Purchases}}` | 2 |
| `{{Date of the Invoice}}` | 2 |
| `{{X-day/money back guarantee period}}` | 2 |
| `{{number of days}}` | 2 |
| `{{Complaint Email Address}}` | 2 |
| `{{Customer Assistance Hours}}` | 2 |
| `{{Live Chat}}` | 2 |
| `{{Customer Assistance Email Address}}` | 2 |
| `{{Customer Assistance Phone Number}}` | 2 |
| `{{Number of Days}}` | 2 |
| `{{Estimated Delivery Time}}` | 2 |
| `{{Shipping Cut-off Time}}` | 2 |
| `{{Standard Shipping Days}}` | 2 |
| `{{Standard Delivery Time}}` | 2 |
| `{{Expedited Delivery Time}}` | 2 |
| `{{Product Category}}` | 2 |
| `{{Recover Access Key}}` | 2 |
| `{{Access Key}}` | 2 |
| `{{Access Key Recovery}}` | 2 |
| `{{Save}}` | 2 |
| `{{Change PIN}}` | 2 |
| `{{PIN Code Restoration}}` | 2 |
| `{{Retrieve Account Key}}` | 2 |
| `{{Password Reset Page URL}}` | 2 |
| `{{Forgot User Access Key}}` | 2 |
| `{{Support Page URL}}` | 2 |
| `{{Help Center URL}}` | 2 |
| `{{Account}}` | 2 |
| `{{Restore Password}}` | 2 |
| `{{Forgot User Account Key}}` | 2 |
| `{{Profile Recovery Page}}` | 2 |
| `{{PIN Code Reset}}` | 2 |
| `{{PIN Code Management}}` | 2 |
| `{{User Profile Settings}}` | 2 |
| `{{Product Feedback Email}}` | 2 |
| `{{Review Platform}}` | 2 |
| `{{Change User}}` | 2 |
| `{{Basic}}` | 2 |
| `{{Account Upgrade}}` | 2 |
| `{{Basic Account}}` | 2 |
| `{{Purchase Status}}` | 2 |
| `{{ETA}}` | 2 |
| `{{Reimbursement ID}}` | 2 |
| `{{Order/Transaction/Reimbursement}}` | 2 |
| `{{Rebate ID}}` | 2 |
| `{{Reference Number}}` | 2 |
| `{{Return Policy}}` | 1 |
| `{{Confirm Cancellation}}` | 1 |
| `{{Remove}}` | 1 |
| `{{additional details}}` | 1 |
| `{{month}}` | 1 |
| `{{year}}` | 1 |
| `{{Account Name}}` | 1 |
| `{{Date of the Bill}}` | 1 |
| `{{Billing Category}}` | 1 |
| `{{Timeframe}}` | 1 |
| `{{Year}}` | 1 |
| `{{Billing}}` | 1 |
| `{{Product/Service Name}}` | 1 |
| `{{Product/Service Defect Refund Time}}` | 1 |
| `{{Cancellation Refund Time}}` | 1 |
| `{{Unauthorized Charges Refund Time}}` | 1 |
| `{{Event Cancellation Refund Time}}` | 1 |
| `{{Duplicate Charges Refund Time}}` | 1 |
| `{{Non-receipt of Goods Refund Time}}` | 1 |
| `{{CompanyName}}` | 1 |
| `{{Claims Contact Number}}` | 1 |
| `{{Claims Website URL}}` | 1 |
| `{{Claims Department}}` | 1 |
| `{{Complaint Hotline Number}}` | 1 |
| `{{Consumer Complaint Email Address}}` | 1 |
| `{{Customer Claims Email Address}}` | 1 |
| `{{Business Name Anonymized}}` | 1 |
| `{{Customer Support Ticket Number}}` | 1 |
| `{{Customer Support Start Time}}` | 1 |
| `{{Customer Support End Time}}` | 1 |
| `{{Opening Time}}` | 1 |
| `{{Closing Time}}` | 1 |
| `{{Free Customer Support Number}}` | 1 |
| `{{mention the different contact options available}}` | 1 |
| `{{Customer Support Hotline}}` | 1 |
| `{{Customer Assistance Email}}` | 1 |
| `{{Social Media Handles}}` | 1 |
| `{{Customer Service Toll-Free Number}}` | 1 |
| `{{contact_method}}` | 1 |
| `{{Social Media Platform}}` | 1 |
| `{{Business Hours}}` | 1 |
| `{{Working Hours}}` | 1 |
| `{{Live Chat Feature}}` | 1 |
| `{{Customer Support Contact Number}}` | 1 |
| `{{Customer Support Opening Time}}` | 1 |
| `{{Customer Support Closing Time}}` | 1 |
| `{{Customer Support Days}}` | 1 |
| `{{Company Support Channels}}` | 1 |
| `{{Customer Support Website}}` | 1 |
| `{{Customer Support Toll-Free Number}}` | 1 |
| `{{Customer Support Team Name}}` | 1 |
| `{{proceed to our website and click on the 'Contact Us' button / dial our customer support number / reach out to our live chat support}}` | 1 |
| `{{your issue}}` | 1 |
| `{{the reason for your call}}` | 1 |
| `{{the specific topic you need assistance with}}` | 1 |
| `{{Company Phone Number}}` | 1 |
| `{{customer_support_phone_number}}` | 1 |
| `{{Account Closure Timeframe}}` | 1 |
| `{{Account Closure Process}}` | 1 |
| `{{Account ID}}` | 1 |
| `{{Carrier Name}}` | 1 |
| `{{Express Shipping Days}}` | 1 |
| `{{Express Delivery Time}}` | 1 |
| `{{Cut Off Time}}` | 1 |
| `{{Country}}` | 1 |
| `{{Express Shipping Time}}` | 1 |
| `{{Same-Day Order Time}}` | 1 |
| `{{Store Pickup Time}}` | 1 |
| `{{Country List}}` | 1 |
| `{{Expedited Shipping Days}}` | 1 |
| `{{Shipping Address}}` | 1 |
| `{{Zip Code}}` | 1 |
| `{{Tracking Information}}` | 1 |
| `{{Order Tracking Method}}` | 1 |
| `{{Min Delivery Time}}` | 1 |
| `{{Max Delivery Time}}` | 1 |
| `{{Destination}}` | 1 |
| `{{Shipping Method}}` | 1 |
| `{{Shipment Tracking Number}}` | 1 |
| `{{provide step-by-step instructions}}` | 1 |
| `{{Free Account Name}}` | 1 |
| `{{Month}}` | 1 |
| `{{Billing History}}` | 1 |
| `{{Invoice Name}}` | 1 |
| `{{Full Name}}` | 1 |
| `{{Company Representative Name}}` | 1 |
| `{{Refund Helpline Number}}` | 1 |
| `{{Refund Hotline Number}}` | 1 |
| `{{Payment Issue Phone Number}}` | 1 |
| `{{Payment Issue Email}}` | 1 |
| `{{Store Address}}` | 1 |
| `{{Online Store}}` | 1 |
| `{{Retail Stores}}` | 1 |
| `{{E-commerce Platform Names}}` | 1 |
| `{{Online Marketplace}}` | 1 |
| `{{City 1}}` | 1 |
| `{{City 2}}` | 1 |
| `{{City 3}}` | 1 |
| `{{E-commerce Platform 1}}` | 1 |
| `{{E-commerce Platform 2}}` | 1 |
| `{{Restore User Access Key}}` | 1 |
| `{{Retrieve User Key}}` | 1 |
| `{{Confirm}}` | 1 |
| `{{Platform Login URL}}` | 1 |
| `{{Retrieve Key}}` | 1 |
| `{{Password Management}}` | 1 |
| `{{Change Password}}` | 1 |
| `{{Login Page}}` | 1 |
| `{{User Key Retrieval Page URL}}` | 1 |
| `{{PIN code}}` | 1 |
| `{{Stolen User Key}}` | 1 |
| `{{Profile PIN Recovery}}` | 1 |
| `{{Platform URL}}` | 1 |
| `{{Reset Account Key}}` | 1 |
| `{{Key Recovery Page URL}}` | 1 |
| `{{Account Access Key Reset}}` | 1 |
| `{{Security and Privacy}}` | 1 |
| `{{Change Key}}` | 1 |
| `{{Retrieve Account PIN}}` | 1 |
| `{{Security Settings}}` | 1 |
| `{{PIN Reset Page URL}}` | 1 |
| `{{Restore PIN Code}}` | 1 |
| `{{Password and Security}}` | 1 |
| `{{PIN Retrieval Page URL}}` | 1 |
| `{{Help Center}}` | 1 |
| `{{Forgot PIN code}}` | 1 |
| `{{Password Recovery Page}}` | 1 |
| `{{Change Access Key}}` | 1 |
| `{{Account Key Recovery}}` | 1 |
| `{{Password Reset}}` | 1 |
| `{{Reset Pin Code}}` | 1 |
| `{{Forgot User Profile Key}}` | 1 |
| `{{Access Key Reset Page URL}}` | 1 |
| `{{Login URL}}` | 1 |
| `{{Forgot Pin}}` | 1 |
| `{{Restore Access Key}}` | 1 |
| `{{Support Channel}}` | 1 |
| `{{Restore User Key}}` | 1 |
| `{{Contact Page URL}}` | 1 |
| `{{Forgot Your Access Key}}` | 1 |
| `{{Profile Security}}` | 1 |
| `{{Retrieve User Account Key}}` | 1 |
| `{{Account Management}}` | 1 |
| `{{Edit PIN}}` | 1 |
| `{{Forgot Profile Access Key}}` | 1 |
| `{{Retrieve Profile Key}}` | 1 |
| `{{PIN Recovery Page URL}}` | 1 |
| `{{User Settings}}` | 1 |
| `{{Retrieve PIN Code}}` | 1 |
| `{{Login page URL}}` | 1 |
| `{{User Profile}}` | 1 |
| `{{Pin Code Settings}}` | 1 |
| `{{User Key Retrieval}}` | 1 |
| `{{Forgot PIN Code}}` | 1 |
| `{{Reset}}` | 1 |
| `{{Support Phone Number}}` | 1 |
| `{{Recover Key}}` | 1 |
| `{{User Profile Page URL}}` | 1 |
| `{{Password Recovery}}` | 1 |
| `{{Manage PIN}}` | 1 |
| `{{Forgot Account Access Key}}` | 1 |
| `{{Lost Key}}` | 1 |
| `{{Access Key Retrieval}}` | 1 |
| `{{Key Management}}` | 1 |
| `{{Registration Support Phone Number}}` | 1 |
| `{{Support Hours}}` | 1 |
| `{{Company Support Page URL}}` | 1 |
| `{{Product Reviews Email}}` | 1 |
| `{{Review Platform 1}}` | 1 |
| `{{Review Platform 2}}` | 1 |
| `{{Contact Us}}` | 1 |
| `{{Account Page}}` | 1 |
| `{{My Account}}` | 1 |
| `{{Shipping Addresses}}` | 1 |
| `{{Add a New Address}}` | 1 |
| `{{Create a Secondary Address}}` | 1 |
| `{{Dashboard}}` | 1 |
| `{{User Management}}` | 1 |
| `{{Regular Profile}}` | 1 |
| `{{Upgrade Account Type}}` | 1 |
| `{{Update Profile}}` | 1 |
| `{{Switch Plan}}` | 1 |
| `{{Purpose of the Features}}` | 1 |
| `{{Explanation of Feature 1}}` | 1 |
| `{{Explanation of Feature 2}}` | 1 |
| `{{Explanation of Feature 3}}` | 1 |
| `{{Support Channel 1}}` | 1 |
| `{{Support Channel 2}}` | 1 |
| `{{Change Profile}}` | 1 |
| `{{First Step}}` | 1 |
| `{{Second Step}}` | 1 |
| `{{Third Step}}` | 1 |
| `{{Fourth Step}}` | 1 |
| `{{Fifth Step}}` | 1 |
| `{{Change Account}}` | 1 |
| `{{Account Type Switch}}` | 1 |
| `{{Membership Type}}` | 1 |
| `{{Choose Account Type}}` | 1 |
| `{{Update Account}}` | 1 |
| `{{Login steps}}` | 1 |
| `{{Navigation steps}}` | 1 |
| `{{Switching option}}` | 1 |
| `{{Completion steps}}` | 1 |
| `{{Manage Subscription}}` | 1 |
| `{{Contact Channel}}` | 1 |
| `{{Username}}` | 1 |
| `{{Account Plan}}` | 1 |
| `{{Upgrade or Downgrade Account}}` | 1 |
| `{{Downgrade}}` | 1 |
| `{{Sign Up}}` | 1 |
| `{{Create Account}}` | 1 |
| `{{Tracking Page}}` | 1 |
| `{{Shipping Status}}` | 1 |
| `{{Email Address}}` | 1 |
| `{{Order Tracker}}` | 1 |
| `{{Delivery Date}}` | 1 |
| `{{Customer Support Live Chat URL}}` | 1 |
| `{{Track Reimbursement}}` | 1 |
| `{{Order/Invoice Number}}` | 1 |
| `{{Customer ID}}` | 1 |
| `{{Rebate Number}}` | 1 |
| `{{Reimbursement Request Number}}` | 1 |
| `{{Order/Transaction/Reference Number}}` | 1 |
| `{{Rebate Identifier}}` | 1 |
| `{{Restitution ID}}` | 1 |
| `{{Order/Claim/Compensation}}` | 1 |
| `{{Account Details}}` | 1 |
| `{{Compensation Type}}` | 1 |
| `{{Order/Refund/Transaction}}` | 1 |
| `{{Order/Claim Number}}` | 1 |
| `{{Case Number}}` | 1 |
| `{{Order/Refund/Case Number}}` | 1 |
| `{{Order/Transaction ID}}` | 1 |
| `{{Compensation ID}}` | 1 |
| `{{Compensation Identifier}}` | 1 |

## Most common response templates (first 8 words)

Command: `uv run python data/fetch.py --profile`

Template = first eight whitespace-separated words of `response`, original casing, single spaces.

| rank | first 8 words | rows |
|---:|---|---:|
| 1 | Thank you for reaching out! I'm here to | 312 |
| 2 | Thank you for reaching out! I completely understand | 245 |
| 3 | Thank you for trusting us! I'm fully aware | 114 |
| 4 | Glad you contacted us! I'm clearly cognizant that | 114 |
| 5 | Thank you for contacting! I certainly recognize that | 114 |
| 6 | Happy to hear from you! I truly understand | 114 |
| 7 | We're here to help! I take note that | 113 |
| 8 | It's great to hear from you! I can | 113 |
| 9 | Thanks for getting in touch! I grasp that | 113 |
| 10 | Your message means a lot! I'm aligned with | 113 |
| 11 | We're listening! I'm keyed into the fact that | 113 |
| 12 | We appreciate your message! It's clear to me | 113 |
| 13 | Your input is valuable! I'm picking up that | 113 |
| 14 | We value your outreach! I'm in tune with | 113 |
| 15 | Always good to connect! I'm attuned to the | 113 |
| 16 | I see what you mean! I'm on the | 113 |
| 17 | Grateful for your contact! I get the sense | 113 |
| 18 | We're all ears! I'm tuned into the idea | 113 |
| 19 | I'm sorry to hear that you're experiencing difficulties | 107 |
| 20 | I'm sorry to hear that you're having trouble | 104 |

## Intent examples

One instruction per intent in `data/intents.json` (27 objects `{intent, category, example}`). Prefers a row with `flags == "B"` (basic syntactic structure) when one exists.

Command: `uv run python data/fetch.py --profile`

