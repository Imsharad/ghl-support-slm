#!/usr/bin/env python3
"""Render eval/challenge_draft.jsonl as a local review page for shark's approval block (H1).

Usage: python3 docs/dag/render_challenge_review.py  -> docs/dag/CHALLENGE_REVIEW.html
Edits made in the page are copied out as JSON with the "Copy edits" button; Fable applies
them to the draft, seals eval/challenge.jsonl and writes eval/SEAL.json.
"""
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
items = [json.loads(l) for l in (ROOT / "eval" / "challenge_draft.jsonl").read_text().splitlines() if l.strip()]
rubric = (ROOT / "eval" / "RUBRIC.md").read_text()

rows = []
for it in items:
    rows.append(f"""
<div class=card data-id="{it['id']}">
  <div class=head><b>{it['id']}</b> <span class=tag>{html.escape(it['intent'])}</span> <span class="tag {it['kind']}">{it['kind']}</span>
  <span class=cos>max Bitext cosine {it['max_bitext_cosine']:.2f}</span>
  <label class=ok><input type=checkbox class=approve checked> approve</label></div>
  <div class=lbl>query (editable) <span class=hint>what the customer sends. Rewrite it if it does not sound like a real person.</span></div><div class="q edit" contenteditable=true>{html.escape(it['query'])}</div>
  <div class=lbl>facts the assistant may assume <span class=hint>everything the assistant knows. Anything missing here it must ask for, not guess.</span></div><div class="f edit" contenteditable=true>{html.escape(it['facts'])}</div>
  <div class=two>
    <div><div class=lbl>acceptable actions <span class=hint>what a good answer may do. Read-only here: ask for changes in the note.</span></div><ul>{''.join('<li>' + html.escape(a) + '</li>' for a in it['acceptable_actions'])}</ul></div>
    <div><div class=lbl>critical fail if <span class=hint>any one of these fails the answer outright, however polite. Read-only here.</span></div><ul class=crit>{''.join('<li>' + html.escape(a) + '</li>' for a in it['critical_fail_if'])}</ul></div>
  </div>
  <div class=lbl>your note (optional) <span class=hint>anything you want changed that you cannot edit above.</span></div><div class="n edit" contenteditable=true></div>
</div>""")

doc = f"""<!doctype html><html><head><meta charset=utf-8><title>Challenge set review (54 items)</title>
<style>
body{{font:15px/1.45 -apple-system,Helvetica,Arial;margin:28px auto;max-width:960px;color:#222;padding:0 16px}}
.card{{border:1px solid #ddd;border-radius:8px;padding:12px 14px;margin:12px 0}}
.head{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.tag{{background:#eee;padding:1px 8px;border-radius:10px;font-size:13px}} .tag.hard{{background:#f7dcdc}} .tag.ordinary{{background:#dcecf7}}
.cos{{color:#777;font-size:13px}} .ok{{margin-left:auto}}
.lbl{{font-size:12px;color:#777;margin-top:8px;text-transform:uppercase;letter-spacing:.04em}}
.edit{{border:1px dashed #bbb;border-radius:4px;padding:6px 8px;background:#fcfcf8;min-height:1.3em}}
.q{{font-size:16px}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} ul{{margin:4px 0 0 18px;padding:0}} .crit li{{color:#a33}}
.bar{{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 0;display:flex;gap:12px;align-items:center;z-index:2}}
button{{padding:6px 12px}} details{{margin:12px 0}} pre{{white-space:pre-wrap;background:#f6f6f6;padding:10px;font-size:13px}}
#count{{color:#555}} #seen{{color:#777;font-size:13px;white-space:nowrap}}
.hint{{font-size:12px;color:#8a8a8a;text-transform:none;letter-spacing:0;font-weight:400}}
body.nohints .hint{{display:none}}
.prog{{height:6px;width:150px;background:#eee;border-radius:3px;overflow:hidden}} .prog i{{display:block;height:100%;width:0;background:#5a8f5a}}
.guide{{border:1px solid #cfc7ae;background:#fbf9f2;border-radius:8px;padding:14px 18px;margin:16px 0}}
.guide h2{{font-size:16px;margin:0 0 8px}} .guide h3{{font-size:14px;margin:14px 0 4px}}
.guide ol,.guide ul{{margin:6px 0 0 20px}} .guide li{{margin:4px 0}}
.guide details{{margin:10px 0 0}} .guide summary{{cursor:pointer;font-weight:600}}
.guide details > div{{padding:4px 0 8px}}
.warn{{background:#fff6e8;border-left:3px solid #d9a441;padding:8px 10px;margin:8px 0}}
.ex{{background:#f4f4f0;border-left:3px solid #bbb;padding:8px 12px;margin:8px 0}}
.ex b{{font-weight:600}} .barlab{{font-size:13px;color:#555;display:flex;gap:6px;align-items:center;cursor:pointer}}
</style></head><body>
<div class=bar><b>Challenge set review</b> <span id=count></span>
<span class=prog title="how far down the 54 cards you have reached"><i id=progbar></i></span> <span id=seen></span>
<button onclick="resume()">Resume</button>
<label class=barlab><input type=checkbox id=hints checked> explain the fields</label>
<button onclick="copyEdits()">Copy edits as JSON</button> <span id=msg></span></div>
<p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M IST')} from <code>eval/challenge_draft.jsonl</code> (54 items, two per intent: one ordinary, one hard).
Edit any query or facts inline, untick items you reject, add a note, then press "Copy edits as JSON" and paste it in the GoHighLevel-prep thread.
Fable applies the edits, seals the file and records its hash. Nothing tuned is generated before that.</p>
<div class=guide>
<h2>Start here: what this page is</h2>
<p>These 54 questions are the exam for the fine-tuned model. No tuned answer exists yet, and none will be generated until you
approve this file and Fable records its hash. That order is the whole point: an exam approved after the answers exist can be
trimmed to flatter the result. You are the only person who can hold it, because the agents wrote it.</p>
<p>Your job is not to write questions. It is to check that each one is <b>answerable</b>, <b>fair</b>, and <b>hard enough to
tell two models apart</b>. Most cards should need nothing from you.</p>

<h3>Do this: about 45 minutes, 50 seconds a card</h3>
<ol>
<li>Read the card and ask the four questions in <i>How to judge one card</i> below.</li>
<li><b>Happy with it:</b> leave <i>approve</i> ticked and scroll on. This is the normal outcome.</li>
<li><b>Wording is off:</b> click into the dashed box and edit the query or the facts. The text is live.</li>
<li><b>A rule is wrong</b> (acceptable actions, critical fail if): those two lists are read-only here. Type what you want changed in the note.</li>
<li><b>Card is broken beyond repair:</b> untick <i>approve</i>.</li>
<li>At the end press <b>Copy edits as JSON</b> and paste the result in the GoHighLevel-prep thread, tagging <code>@Fable 5.1</code>.</li>
</ol>
<div class=warn>Unticking drops the item. That intent then has only one of its two difficulties and the exam falls to 53 questions.
Prefer an edit; reject only when the card cannot be fixed.</div>
<p>Everything you type is saved in this browser as you go, so you can close the tab and come back. It is saved only in
<i>this</i> browser, and only this page holds it until you paste the JSON.</p>

<details><summary>What the words on a card mean</summary><div>
<ul>
<li><b>ch-001</b> and the rest: the item id. The score sheet uses these labels.</li>
<li><b>intent</b> (grey pill): which of the 27 support topics the question belongs to. Two cards per topic.</li>
<li><b>ordinary / hard</b>: hard means typos, anger, two requests in one message, a missing order id, or a demand no support
agent can meet. Half the set is hard on purpose. An exam of easy questions separates nothing.</li>
<li><b>max Bitext cosine</b>: how close the wording sits to the nearest question in the training data. 0 is unrelated, 1 is a
copy. Every item here is under 0.85 by rule, so none is a paraphrase of something the model studied. The low numbers
(0.35 to 0.50) are the freshest questions.</li>
<li><b>query</b>: what the customer sends.</li>
<li><b>facts</b>: everything the assistant is allowed to know. Anything not listed, it must ask for. This is the trap in most
items: the order id is withheld deliberately, and a model that invents one fails.</li>
<li><b>acceptable actions</b>: what a good answer may do.</li>
<li><b>critical fail if</b>: an answer doing any of these fails outright, however polite. Inventing a policy, a status, a
completed action, or a timeline.</li>
</ul>
</div></details>

<details><summary>How to judge one card in under a minute</summary><div>
<ol>
<li><b>Would a real customer send this?</b> If it reads like a machine wrote it, rewrite the query in your own words.</li>
<li><b>Can it be answered well using only the facts?</b> If the query mentions something the facts drop, add it to the facts.
If the facts hand over an id the customer never gave, delete it, or the trap disappears.</li>
<li><b>Would you accept an answer that does only the acceptable actions?</b> If an obvious next step is missing, say so in the note.</li>
<li><b>Is every critical-fail line a real invention?</b> It must name something no correct answer could ever contain. A line
that only describes a clumsy answer is too harsh: note it.</li>
</ol>
</div></details>

<details><summary>A worked example: read ch-002 with me</summary><div>
<div class=ex><b>Query:</b> just cancel it. I don&#x27;t have the number. cancel whatever I bought last night.<br>
<b>Facts:</b> no order id; customer says last night; assistant cannot see purchase history.</div>
<p>Question 1: yes, people type exactly like this when they are annoyed. Question 2: the assistant cannot find the order at all,
which is the point of the card, and the facts say so plainly. Question 3: ask for the id, refuse to act blind, explain why
&quot;last night&quot; is not enough. That is the answer I would want. Question 4: cancelling an unspecified order, inventing an
order number, promising it is done. Each is an invention no correct answer could contain.</p>
<p>Leave it approved. Fifteen seconds.</p>
<p>Now the same card broken: if the facts said <i>order GL-4419</i> while the query says the customer has no number, the model
could answer straight from the facts and the trap would be gone. That is an edit, not a rejection: delete the id from the facts.</p>
</div></details>

<details><summary>What happens after you press the button</summary><div>
<ol>
<li>You paste the JSON in the thread and tag Fable.</li>
<li>Fable applies your edits, drops what you unticked, writes <code>eval/challenge.jsonl</code> and its sha256 into
<code>eval/SEAL.json</code>. From that moment the file is frozen and any later change breaks the hash in public.</li>
<li>Grok runs all 54 through both models, the untrained base and the tuned one: 108 answers, built into a sheet where the two
answers are labelled only A and B.</li>
<li>You score that sheet against the rubric below, not knowing which model wrote which answer. That score is the result the
assignment reports.</li>
</ol>
<p>So edit freely now. After the seal, nothing here can change.</p>
</div></details>
</div>

<details><summary>Rubric (eval/RUBRIC.md)</summary><pre>{html.escape(rubric)}</pre></details>
{''.join(rows)}
<script>
const KEY='ghl-challenge-review-v1';
function state(){{return [...document.querySelectorAll('.card')].map(c=>({{id:c.dataset.id,approve:c.querySelector('.approve').checked,
 query:c.querySelector('.q').innerText.trim(),facts:c.querySelector('.f').innerText.trim(),note:c.querySelector('.n').innerText.trim()}}));}}
function save(){{localStorage.setItem(KEY,JSON.stringify(state()));document.getElementById('count').textContent=
 state().filter(s=>s.approve).length+' / '+state().length+' approved';}}
function load(){{const s=JSON.parse(localStorage.getItem(KEY)||'null');if(!s)return;for(const r of s){{const c=document.querySelector(`.card[data-id="${{r.id}}"]`);if(!c)continue;
 c.querySelector('.approve').checked=r.approve;c.querySelector('.q').innerText=r.query;c.querySelector('.f').innerText=r.facts;c.querySelector('.n').innerText=r.note;}}}}
function copyEdits(){{const out={{reviewed_at:new Date().toString(),items:state()}};navigator.clipboard.writeText(JSON.stringify(out,null,1)).then(()=>document.getElementById('msg').textContent='copied');}}
const HKEY='ghl-challenge-review-hints-v1', SKEY='ghl-challenge-review-seen-v1';
const cards=[...document.querySelectorAll('.card')], hintBox=document.getElementById('hints');
let seen=new Set(JSON.parse(localStorage.getItem(SKEY)||'[]'));
function drawSeen(){{document.getElementById('progbar').style.width=(100*seen.size/cards.length).toFixed(0)+'%';
 document.getElementById('seen').textContent='reached '+seen.size+' / '+cards.length;}}
function markSeen(id){{if(seen.has(id))return;seen.add(id);localStorage.setItem(SKEY,JSON.stringify([...seen]));drawSeen();}}
const obs=new IntersectionObserver(es=>{{for(const e of es) if(e.isIntersecting) markSeen(e.target.dataset.id);}},{{threshold:0.4}});
cards.forEach(c=>obs.observe(c));
function resume(){{const next=cards.find(c=>!seen.has(c.dataset.id))||cards[cards.length-1];
 next.scrollIntoView({{behavior:'smooth',block:'center'}});}}
function drawHints(){{document.body.classList.toggle('nohints',!hintBox.checked);
 localStorage.setItem(HKEY,hintBox.checked?'1':'0');}}
hintBox.checked=localStorage.getItem(HKEY)!=='0';
hintBox.addEventListener('change',drawHints);
document.addEventListener('input',save);document.addEventListener('change',save);load();save();drawHints();drawSeen();
</script></body></html>"""
(ROOT / "docs" / "dag" / "CHALLENGE_REVIEW.html").write_text(doc)
print("wrote docs/dag/CHALLENGE_REVIEW.html", len(items), "items")
