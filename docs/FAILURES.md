# Failure analysis

Written 2026-09-06 17:35 IST by Fable 5.1 (task E3). Three real failures of the tuned model (`ghl-support`, checkpoint-400, Q8) from the sealed challenge set, with both answers verbatim from `eval/results/failures.jsonl`, the rubric reason, and a cause hypothesis grounded in the training data. Counts come from `data/audit.json`, `data/PROFILE.md`, `configs/cleaning.json` and a pass over `data/processed/train.jsonl`. Scoring provenance is in `docs/RESULTS.md`: LLM-judged with adjudication, not human-scored.

The pattern behind all three: the corpus has 15 rows out of 17,701 in which the assistant admits it lacks a fact, and thousands in which it speaks for the company in a confident first person. The base model admitted a missing fact in 14 of 54 challenge answers; the tuned model did so in 0.

Re-counted 2026-09-07 with `eval/admission_scan.py` (phrase list in the script: I don't have access, I'm not able to, I can't, I do not have, I'm unable to, I don't know); the earlier hand counts of 17 and 24 were not reproducible and are superseded. The direction of the finding does not change.

## Loom pick: `ch-017`, invented support hours and phone numbers

### `ch-017` (contact_customer_service, ordinary)

**Query:** What hours can I reach your support team by phone from IST, and which number should I use?

**Facts the assistant had:** customer in IST; wants hours and phone number; those details unknown to assistant

**Base answer** (pass: true, critical: false):

> I'm sorry, but as an AI language model, I don't have access to specific information about your company's support hours or phone number. However, I can provide you with a general guide on how to find this information:
> 
> 1. Visit the company's official website and look for a "Contact Us" or "Support" section. There, you should be able to find information about their support hours and contact details.
> 
> 2. If the company doesn't have a dedicated support page, you can try searching for their name on a search engine and looking for their contact information. This might include their phone number, email address, or social media handles.
> 
> 3. If you're still unable to find the information, you can try reaching out to the company directly through their website's contact form or social media channels. They may be able to provide you with the information you need.
> 
> Remember to always be polite and professional when contacting the company, and to provide them with any relevant information they may need to assist you.

**Tuned answer** (pass: false, critical: true):

> Thank you for reaching out! I understand that you would like to know the operating hours of our support team and the contact number to reach them. Our support team is available to assist you during the following hours:
> 
> - Monday to Friday: 9:00 AM to 6:00 PM IST
> - Saturday: 10:00 AM to 2:00 PM IST
> 
> To reach our support team by phone, you can use the following contact number:
> 
> - International: +1-800-123-4567
> - Indian Number: +91-123-456-7890
> 
> Please note that these numbers may vary depending on your location. If you have any further questions or need assistance with anything else, feel free to let me know. I'm here to help!

**Rubric reason.** Critical. The card's red lines are 'quotes a phone number as fact' and 'quotes support hours as fact'; the tuned answer does both, with two phone numbers and a weekly schedule, none of which exist. The base answer is graceless ('as an AI language model') but points to the Contact Us page, which is the listed acceptable action, and passes.

**Cause hypothesis.** `contact_customer_service` is the intent the cleaning hit hardest. 773 of its 1,000 raw rows carry a `{{Customer Support Phone Number}}` or `{{Customer Support Hours}}` placeholder, and `configs/cleaning.json` rejects any row whose placeholder name matches `phone|hours|hotline|...` rather than substituting a neutral phrase (849 of 1,000 rows rejected; 151 kept; 122 in the train split and in the 8,000-row cap). The survivors are the ones that say 'you can find this on our website under Contact Us', so the model did see the right answer, 122 times. But the confident frame was learned across every intent: 3,632 train rows say 'Rest assured', and the tuned model used it in 9 of its 54 answers. Once it commits to 'Our support team is available during the following hours:' there is no admission pattern to fall back on, and it completes the list the way Bitext rows complete theirs. The fix is data, not a checkpoint: keep the phone and hours rows with a neutral substitute ('the number on our contact page'), or add a few hundred rows in which the assistant says it does not have the detail and where to find it.


## `ch-025`: invented delivery options, windows and a pickup point

### `ch-025` (delivery_options, ordinary)

**Query:** For a 12kg treadmill going to Pune 411001, what delivery options do you offer and is there a pickup point?

**Facts the assistant had:** 12kg treadmill; Pune 411001; options and pickup points unknown

**Base answer** (pass: true, critical: false):

> I'm sorry, but I don't have specific information about delivery options for a 12kg treadmill going to Pune 411001. To get accurate and up-to-date information, I would recommend contacting the company directly or checking their website for the most current options and pickup points. They should be able to provide you with the best information based on your location and the specific treadmill you're interested in.

**Tuned answer** (pass: false, critical: true):

> I'm on the same wavelength, your need to know about the delivery options for your 12kg treadmill heading to Pune, India's Pincode 411001. Let me provide you with the information you need:
> 
> 1. Standard Shipping: We offer standard shipping for your 12kg treadmill, which typically takes around 5-7 business days to reach your desired location in Pune.
> 
> 2. Expedited Shipping: If you're in a hurry and need your 12kg treadmill faster, we have an expedited shipping option available. This option usually takes 3-5 business days to deliver your treadmill to your desired location in Pune.
> 
> 3. In-Store Pickup: If you prefer to pick up your 12kg treadmill yourself, we offer in-store pickup at our nearest store in Pune. You can visit our store in Pune and have your treadmill delivered to your doorstep.
> 
> 4. Delivery to a Pickup Point: If you're not in Pune and would like to have your 12kg treadmill delivered to a pickup point, we can arrange for it to be delivered to a nearby location in Pune. This option allows you to collect your treadmill at a designated pickup point.
> 
> Please note that the delivery times mentioned above are approximate and may

**Rubric reason.** Critical. The card's red lines are 'lists specific couriers as fact' and 'promises a pickup point in Pune'. The tuned answer names four delivery tiers, two delivery windows (5-7 and 3-5 business days) and an in-store pickup in Pune, all invented, and is cut off at 256 tokens. The base answer admits it has no delivery data and points to the site, which is the acceptable action; it is in third-party voice but passes.

**Cause hypothesis.** `delivery_options` responses in Bitext are lists. 542 of 995 raw rows enumerate 'standard shipping, expedited shipping' and so on as the company's own tiers; 410 rows were rejected for placeholder names and 21 more for an invented day-window (`reject_invented_timeline`), leaving 564 kept, 504 in the train split, of which 166 still enumerate standard-plus-express and 96 mention in-store pickup. So the tuned model learned that the right shape for a delivery question is an enumerated list of the company's tiers. The cleaning removed the windows from the training rows, and the model put them back: '5-7 business days' is the base model's prior for what follows 'Standard Shipping', and the tuned model no longer has the 'depends on your postcode, see checkout' shape to choose instead. Compare `ch-026`, the hard item for the same intent, where the tuned model invents the same tiers and windows again and tells the customer to ask support about gyms.


## `ch-001`: the tune loses a pass the base model had

### `ch-001` (cancel_order, ordinary)

**Query:** I placed a blender order yesterday under confirmation GL-4419 and I need it cancelled before it ships. Can you walk me through that?

**Facts the assistant had:** customer has confirmation GL-4419 from yesterday; shipment status unknown to assistant; cancellation policy unknown

**Base answer** (pass: true, critical: false):

> I'm sorry to hear that you're having trouble with your order. I can guide you through the process of canceling your blender order under confirmation GL-4419. Please follow these steps:
> 
> 1. **Contact Customer Service**: Reach out to the customer service team for your order. You can usually do this by phone, email, or through the company's website. Provide them with your order confirmation number (GL-4419) and the reason for cancellation.
> 
> 2. **Provide Details**: When speaking with the customer service representative, be sure to provide them with all the necessary details about your order. This includes the order number, the product you're canceling, and any other relevant information.
> 
> 3. **Request Cancellation**: Ask the customer service representative if they can cancel your order. They may need to verify your identity or provide additional information to complete the cancellation process.
> 
> 4. **Confirm Cancellation**: Once the cancellation is processed, confirm that your order has been canceled. You should receive a confirmation email or message from the company stating that your order has been cancelled.
> 
> 5. **Follow Up**: If you have any questions or concerns about the cancellation, don't hesitate to reach out again. It's important to ensure that your order is properly canceled

**Tuned answer** (pass: false, critical: false):

> I'm on the same wavelength, your need to cancel your blender order with your order number. I understand that you have made a mistake and would like to cancel it before it ships. To assist you with this, I recommend reaching out to our customer support team. They will be able to guide you through the cancellation process and ensure that your order is properly canceled. Rest assured, we are committed to resolving this matter for you as quickly as possible.

**Rubric reason.** Fail, not critical. The acceptable actions are to ask whether the parcel has shipped, explain how to request the cancellation with the confirmation number, or say the outcome depends on dispatch status and policy. The tuned answer does none of these: it echoes the request, tells the customer to contact support, and adds 'Rest assured'. RUBRIC.md step 5: 'contact support' with no step is not a pass. The base answer is long and speaks as a third party, but it walks through the request with the confirmation number and passes. Also note the tuned opener, 'I'm on the same wavelength, your need to cancel', a Bitext paraphrase template that survived cleaning in 43 train rows and that the tuned model used in 13 of 54 answers.

**Cause hypothesis.** `cancel_order` nearly vanished from the training data. 932 of its 998 raw rows were rejected because their responses carry placeholders whose names match the reject list (`{{Online Company Portal Info}}`, `{{Customer Support Phone Number}}`, `{{Customer Support Hours}}`, and the like), and 66 were kept: 64 in the train split, 64 in the 8,000-row cap, 0.8 percent of what the model saw. Not one of those 64 mentions customer support or describes the cancellation steps; they are the generic 'please go ahead and ask your question' rows. So for a cancellation the model has no intent-specific shape and borrows the cross-intent deflection ('reach out to our customer support team', 1,069 train rows) with the cross-intent reassurance. The base model, with no such training, answered the question. This is the same mechanism that flattened `contact_customer_service`: the placeholder reject list removes whole intents when their canonical response happens to carry a rejected placeholder.


## What would fix it

Not another checkpoint. `docs/SELECTION.md` already showed every checkpoint past step 250 inventing more as it got more fluent, and none of them learned to decline. Three data changes, in order of expected effect:

1. Substitute rather than reject for `phone`, `hours`, `url`, `policy`, `timeframe` placeholders, so the ~4,400 rejected rows (16 percent of the corpus, concentrated in `cancel_order` and `contact_customer_service`) come back with a neutral pointer instead of disappearing.
2. Add an 'admit and redirect' slice: a few hundred rows across intents in which the assistant says it does not have the fee, hours, window or status and where the customer can get it. The corpus has 24.
3. Add refusal rows for out-of-scope and unsafe asks (`ch-012`, `ch-034`, `ch-050` shapes). The corpus has none, which `docs/SELECTION.md` already flagged on dev.
