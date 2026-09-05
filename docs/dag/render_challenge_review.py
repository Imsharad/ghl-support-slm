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
  <div class=lbl>query (editable)</div><div class="q edit" contenteditable=true>{html.escape(it['query'])}</div>
  <div class=lbl>facts the assistant may assume</div><div class="f edit" contenteditable=true>{html.escape(it['facts'])}</div>
  <div class=two>
    <div><div class=lbl>acceptable actions</div><ul>{''.join('<li>' + html.escape(a) + '</li>' for a in it['acceptable_actions'])}</ul></div>
    <div><div class=lbl>critical fail if</div><ul class=crit>{''.join('<li>' + html.escape(a) + '</li>' for a in it['critical_fail_if'])}</ul></div>
  </div>
  <div class=lbl>your note (optional)</div><div class="n edit" contenteditable=true></div>
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
#count{{color:#555}}
</style></head><body>
<div class=bar><b>Challenge set review</b> <span id=count></span>
<button onclick="copyEdits()">Copy edits as JSON</button> <span id=msg></span></div>
<p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M IST')} from <code>eval/challenge_draft.jsonl</code> (54 items, two per intent: one ordinary, one hard).
Edit any query or facts inline, untick items you reject, add a note, then press "Copy edits as JSON" and paste it in the GoHighLevel-prep thread.
Fable applies the edits, seals the file and records its hash. Nothing tuned is generated before that.</p>
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
document.addEventListener('input',save);document.addEventListener('change',save);load();save();
</script></body></html>"""
(ROOT / "docs" / "dag" / "CHALLENGE_REVIEW.html").write_text(doc)
print("wrote docs/dag/CHALLENGE_REVIEW.html", len(items), "items")
