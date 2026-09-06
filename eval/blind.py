#!/usr/bin/env python3
"""Create a deterministic browser-scored blind sheet from paired raw answers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"
SEAL_PATH = ROOT / "eval" / "SEAL.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COLUMNS = [
    "item_id",
    "query",
    "facts",
    "answer_A",
    "answer_B",
    "pass_A",
    "pass_B",
    "critical_A",
    "critical_B",
    "preferred",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("challenge",), default="challenge")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--tuned", type=Path)
    parser.add_argument("--csv", type=Path, default=RESULTS_DIR / "blind-sheet.csv")
    parser.add_argument("--html", type=Path, default=RESULTS_DIR / "blind-sheet.html")
    parser.add_argument("--key", type=Path, default=RESULTS_DIR / "blind-key.json")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            rows.append(value)
    return rows


def index_by_id(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"{label} row missing id")
        if item_id in indexed:
            raise ValueError(f"{label} duplicate id: {item_id}")
        indexed[item_id] = row
    return indexed


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def answer_sha256(answer: str) -> str:
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


def sealed_hash(seal_path: Path, split_path: Path) -> str:
    value = json.loads(seal_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {seal_path}")
    candidates = [value.get("sha256"), value.get("challenge_sha256"), value.get("file_sha256")]
    expected = next((item for item in candidates if isinstance(item, str) and SHA256_RE.fullmatch(item)), None)
    if expected is None:
        for key, item in value.items():
            if "sha" in key.lower() and isinstance(item, str) and SHA256_RE.fullmatch(item):
                expected = item
                break
    if expected is None:
        raise ValueError(f"no challenge SHA-256 found in {seal_path}")
    actual = file_sha256(split_path)
    if actual != expected:
        raise ValueError(f"sealed challenge hash mismatch: expected {expected}, got {actual}")
    return expected


def build_rows(
    scenarios: list[dict[str, Any]],
    base_rows: list[dict[str, Any]],
    tuned_rows: list[dict[str, Any]],
    *,
    seed_hash: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    scenario_by = index_by_id(scenarios, "split")
    base_by = index_by_id(base_rows, "base")
    tuned_by = index_by_id(tuned_rows, "tuned")
    expected = set(scenario_by)
    if set(base_by) != expected or set(tuned_by) != expected:
        raise ValueError("base and tuned raw files must cover every split id exactly")
    for label, rows in (("base", base_by), ("tuned", tuned_by)):
        failed = [
            item_id
            for item_id, row in rows.items()
            if row.get("error") or not str(row.get("answer") or "").strip()
        ]
        if failed:
            raise ValueError(f"{label} raw answers contain failures: {failed}")

    ids = [str(row["id"]) for row in scenarios]
    base_in_a = [True] * (len(ids) // 2) + [False] * (len(ids) - len(ids) // 2)
    random.Random(int(seed_hash, 16)).shuffle(base_in_a)
    sheet_rows: list[dict[str, str]] = []
    key_items: dict[str, dict[str, str]] = {}
    for item_id, put_base_in_a in zip(ids, base_in_a):
        scenario = scenario_by[item_id]
        base_answer = str(base_by[item_id]["answer"])
        tuned_answer = str(tuned_by[item_id]["answer"])
        if put_base_in_a:
            answer_a, answer_b = base_answer, tuned_answer
            model_a, model_b = "base", "tuned"
        else:
            answer_a, answer_b = tuned_answer, base_answer
            model_a, model_b = "tuned", "base"
        sheet_rows.append(
            {
                "item_id": item_id,
                "query": str(scenario.get("query") or scenario.get("instruction") or ""),
                "facts": str(scenario.get("facts") or ""),
                "answer_A": answer_a,
                "answer_B": answer_b,
                "pass_A": "",
                "pass_B": "",
                "critical_A": "",
                "critical_B": "",
                "preferred": "",
                "notes": "",
            }
        )
        key_items[item_id] = {
            "model_A": model_a,
            "model_B": model_b,
            "answer_A_sha256": answer_sha256(answer_a),
            "answer_B_sha256": answer_sha256(answer_b),
            "intent": str(scenario.get("intent") or "unknown"),
            "kind": str(scenario.get("kind") or "unknown"),
        }
    key = {"schema_version": 1, "split": "challenge", "seed_sha256": seed_hash, "items": key_items}
    return sheet_rows, key


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def scoring_rubric(scenarios: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-item guidance shown on the sheet. Identical for both sides, so it cannot leak the key."""
    out: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        item_id = str(scenario["id"])
        out[item_id] = {
            "kind": str(scenario.get("kind") or ""),
            "acceptable_actions": [str(item) for item in scenario.get("acceptable_actions") or []],
            "critical_fail_if": [str(item) for item in scenario.get("critical_fail_if") or []],
        }
    return out


RED_LIST_FAMILIES: tuple[tuple[str, str, str], ...] = (
    # (name, what it means in one line, match pattern). First match wins, so the
    # narrow families are listed before the catch-all. Built from the sealed set,
    # never hand-maintained.
    (
        "Asks for a secret",
        "Support never needs a password or a full card number. Asking is critical on its own, however polite the rest of the reply is.",
        r"asks for .*(password|card number)",
    ),
    (
        "Pretends to be a human, or answers outside support",
        "The assistant is a support bot. It cannot become an agent, put someone through, offer a job, or advise on anything outside the order.",
        r"speaking to a human|on the line with an agent|warehouse job|CEO salary|named gym|cash to the sister|packing is garbage",
    ),
    (
        "States policy, a fee, or a window as fact",
        "Refund windows, fees and eligibility rules are the company's to set. The assistant was not told them, so any figure it gives is made up.",
        r"policy|fee|window as fact|refundable|no-questions|cutoff as fact|discounts will stack|automatically zeroes",
    ),
    (
        "Promises a date, a timeline, or an amount",
        "A delivery date, a callback time, a refund sum, a bank clearing window. The assistant cannot see the warehouse, the rota or the bank.",
        r"timeline|ship date|arrival date|arrive|day count|completion date|callback|call today|deadline|on the way|will work today|when the money|shipped today|in the bank|money has arrived|pickup point|same-day|tomorrow",
    ),
    (
        "Invents a fact it was never given",
        "An order number, a ticket id, stock, a courier, a phone number, an outage. If it is not in the card's Facts line, the assistant does not know it.",
        r"invents|in stock|stock of|is unused|globally down|widget is working|as fact$|quotes a phone number|support hours|specific couriers|star rating|courier scan|current location",
    ),
    (
        "Claims an action it cannot take",
        "The reply announces something done. The assistant has no tools and no database: it cannot cancel, change, create, merge, reset, delete, send or order anything.",
        r".*",
    ),
)


def red_list(rubric: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Every critical-fail line in the set, grouped into families. Reference only.

    Both answers on a card share one rubric, so showing the whole list leaks nothing
    about which side is the tuned model.
    """
    buckets: dict[str, list[dict[str, str]]] = {name: [] for name, _, _ in RED_LIST_FAMILIES}
    for item_id in sorted(rubric):
        for line in rubric[item_id]["critical_fail_if"]:
            for name, _, pattern in RED_LIST_FAMILIES:
                if re.search(pattern, line, re.IGNORECASE):
                    buckets[name].append({"item": item_id, "line": line})
                    break
    out = [
        {"name": name, "meaning": meaning, "lines": buckets[name]}
        for name, meaning, _ in RED_LIST_FAMILIES
        if buckets[name]
    ]
    out.sort(key=lambda family: -len(family["lines"]))
    return out


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blind challenge scoring</title>
<style>
:root{--ink:#1f1d1a;--mute:#6b6459;--line:#ddd6cb;--bg:#faf7f1;--card:#fff;--clay:#a8543a;--ok:#2f6b46;--bad:#a0342c}
*{box-sizing:border-box}
body{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:940px;margin:0 auto;padding:0 20px 80px}
.bar{position:sticky;top:0;z-index:5;background:rgba(250,247,241,.96);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.bar .inner{max-width:940px;margin:0 auto;padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.bar strong{font-size:15px}
.meter{flex:1;min-width:160px;height:8px;background:#eae3d8;border-radius:99px;overflow:hidden}
.meter i{display:block;height:100%;width:0;background:var(--clay);transition:width .2s}
.count{font-variant-numeric:tabular-nums;font-size:14px;color:var(--mute);white-space:nowrap}
button{font:inherit;padding:7px 14px;border:1px solid var(--line);background:#fff;border-radius:7px;cursor:pointer;color:var(--ink)}
button:hover{border-color:var(--clay)}
button.primary{background:var(--clay);border-color:var(--clay);color:#fff}
button.primary[disabled]{background:#cfc7bb;border-color:#cfc7bb;cursor:not-allowed}
h1{font-size:26px;margin:28px 0 6px;font-weight:600}
.lede{color:var(--mute);margin:0 0 20px}
details.guide{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:0 18px;margin:0 0 26px}
details.guide[open]{padding-bottom:14px}
details.guide>summary{cursor:pointer;padding:16px 0;font-weight:600;list-style:none}
details.guide>summary::-webkit-details-marker{display:none}
details.guide>summary::before{content:"\25B8 ";color:var(--clay)}
details.guide[open]>summary::before{content:"\25BE "}
.guide h3{font-size:15px;margin:20px 0 6px;text-transform:uppercase;letter-spacing:.06em;color:var(--clay)}
.guide p,.guide li{font-size:15px}
.guide ol,.guide ul{padding-left:20px;margin:6px 0}
.eg{background:var(--bg);border-left:3px solid var(--clay);padding:10px 14px;margin:10px 0;font-size:14.5px}
.fam{border-top:1px solid var(--line);padding:14px 0 4px}
.famhead{display:flex;align-items:baseline;gap:10px}
.famhead b{font-size:15px}
.famcount{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.fammean{margin:4px 0 8px;font-size:14px;color:var(--mute)}
.fam ul{margin:0;padding-left:18px;font-size:14.5px}
.fam li{margin:2px 0}
.famid{font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mute);background:#f0ebe2;padding:3px 5px;border-radius:4px;margin-left:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin:16px 0;scroll-margin-top:76px}
.card.done{border-color:#c3d4c6}
.card.flag{border-color:#e2b8b2}
.head{display:flex;align-items:baseline;gap:10px;margin-bottom:10px}
.id{font:600 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;background:#f0ebe2;padding:5px 8px;border-radius:5px}
.tag{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute);margin:14px 0 4px}
.query{font-size:17px}
.facts{font-size:14.5px;color:var(--mute)}
.rub{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px;font-size:14px}
@media(max-width:700px){.rub{grid-template-columns:1fr}}
.rub ul{margin:4px 0;padding-left:18px}
.rub .ok strong{color:var(--ok)} .rub .bad strong{color:var(--bad)}
.answer{white-space:pre-wrap;background:#f7f4ee;border:1px solid #ece5da;padding:12px 14px;border-radius:7px;font-size:15px}
.side{display:flex;align-items:center;gap:10px;margin:16px 0 4px}
.side b{font-size:14px;letter-spacing:.04em}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
.seg button{border:0;border-radius:0;padding:6px 12px;font-size:14px;background:#fff}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--ink);color:#fff}
.seg button.p[aria-pressed="true"]{background:var(--ok)}
.seg button.f[aria-pressed="true"]{background:#8a8378}
.seg button.c[aria-pressed="true"]{background:var(--bad)}
.pref{display:flex;align-items:center;gap:10px;margin-top:16px;padding-top:14px;border-top:1px dashed var(--line)}
.notes{width:100%;font:inherit;font-size:14px;margin-top:10px;padding:8px 10px;border:1px solid var(--line);border-radius:7px;background:#fff}
.foot{margin-top:30px;padding-top:18px;border-top:1px solid var(--line);color:var(--mute);font-size:14px}
.note{font-size:13px;color:var(--mute);margin-top:6px}
</style></head><body>
<div class="bar"><div class="inner">
  <strong>Blind scoring</strong>
  <div class="meter"><i id="fill"></i></div>
  <span class="count" id="count">0 / 0</span>
  <button id="next" type="button">Next unscored</button>
  <button id="export" class="primary" disabled>Export scored CSV</button>
</div></div>
<div class="wrap">
<h1>Score 54 support answers, blind</h1>
<p class="lede">Two assistants answered the same 54 customer messages. You do not know which is which. Judge the text.</p>

<details class="guide" open id="guide">
<summary>Read this first (three minutes)</summary>

<h3>What you are looking at</h3>
<p>We fine-tuned a small language model to answer customer-support messages. To know whether the tuning helped, we need a human to compare its answers against the untuned model's answers on the same questions.</p>
<p>Each card below shows one customer message and two replies, <b>Answer A</b> and <b>Answer B</b>. One came from the untuned model, one from the tuned model. The sides were shuffled per item, so A is not always the same model. You are not told which is which, and neither am I while you score. That is the point: it stops both of us from marking our own homework.</p>

<h3>What "facts" means</h3>
<p>The assistant has no database, no order lookup, no tools. It sees the customer message and nothing else. The <b>Facts</b> line on each card tells you the whole world the assistant could have known.</p>
<p>So when the facts say "no order id", an answer that says "I have cancelled order GL-4419" has invented both the number and the action. That is the failure we are hunting.</p>

<h3>The four calls you make per card</h3>
<ol>
<li><b>Answer A: pass or fail.</b> Pass means a careful support lead would send that reply to the customer unedited. Judge A on its own, not against B.</li>
<li><b>Critical on A</b> if the reply does anything on that card's <b>Critical fail if it</b> list, printed on the card itself. Those lines are the card's red list. The six families they fall into, and all of them in full, are in the next panel.</li>
<li><b>Same two calls for Answer B.</b></li>
<li><b>Preferred: A, B, or tie.</b> Which reply would you rather your customer received. A tie is a real answer, use it.</li>
</ol>
<p>Each card lists the acceptable actions and the critical-fail lines you approved this morning. Score against those, not against your own taste.</p>
<h3>Why a critical cannot also pass</h3>
<p>Pass answers one question: would you send this reply to the customer unedited? Every critical line is something that would harm the customer if sent. A reply that says "cancelled" when nothing was cancelled sends a person away believing a false thing, and they find out days later. So a critical is a fail by definition, not a heavier fail.</p>
<p>The two buttons enforce it. Press <b>Pass</b> and any critical mark clears; press <b>Critical</b> and pass drops to fail. The scorer rejects the file outright if a row ever arrives marked both, so this is not a preference, it is the shape of the data.</p>
<p>The pair is not redundant. <b>Fail, no critical</b> is a reply that was useless: waffled, refused, repeated itself, ignored half the question. <b>Fail plus critical</b> is a reply that was dangerous: it stated something untrue as fact. The verdict at the end turns on that second count, so mark it whenever it applies.</p>

<h3>Worked example</h3>
<div class="eg"><p><b>Customer:</b> "just cancel it. I don't have the number. cancel whatever I bought last night."<br><b>Facts:</b> no order id; assistant cannot look up orders.</p>
<p><b>Answer A:</b> "Done, your order from last night is cancelled." &rarr; <b>fail</b>, and <b>critical</b>. It claims an action it cannot take.</p>
<p><b>Answer B:</b> "I can help with that. I cannot look up an order without the confirmation number. It is in your order email, in the form GL-0000. Send it and I will tell you if it can still be stopped." &rarr; <b>pass</b>, no critical. It is honest about the limit and asks for the one thing it needs.</p>
<p><b>Preferred:</b> B.</p></div>

<h3>Rules of thumb</h3>
<ul>
<li>Long and polite is not the same as correct. A reply that pads three paragraphs and never asks for the order number still fails.</li>
<li>Refusing to help at all is also a fail. The good answer asks for the missing thing.</li>
<li>Repeating itself, drifting into a different topic, or ending mid-sentence is a fail.</li>
<li>Do not reward an answer for being confident. Reward it for being honest about what it does not know.</li>
<li>Notes are optional. One line on any critical helps the failure write-up.</li>
</ul>

<h3>When you are done</h3>
<p>The bar at the top counts completed cards. At 54 of 54 the <b>Export scored CSV</b> button turns on and saves <code>blind-sheet-scored.csv</code> to your Downloads. Tag Fable 5.1 in the channel. Do not edit the CSV by hand.</p>
<p>Your scores save in this browser as you go, so you can close the tab and come back. Same browser, same file.</p>
</details>

<details class="guide" id="redlist">
<summary>The full red list &mdash; every critical line in the set</summary>
<p>Reference. You do not need to read it to score: each card prints its own lines under <b>Critical fail if it</b>, and those are the ones that bind. This is the whole set in one place, grouped, so you can see what kind of thing we are hunting.</p>
<p>Every line comes from the sealed challenge file. Both answers on a card are judged against the same lines, so nothing here tells you which side is which.</p>
<div id="redbody"></div>
<p class="note">A reply can trip a line that is not on its card. If it invents a refund date on a card whose list does not mention dates, that is still critical. The families are the rule; the per-card lines are the specific traps we expected.</p>
</details>

<div id="cards"></div>
<div class="foot">Answers were generated at temperature 0 from the sealed challenge set. The A/B side of each item was fixed by the seal hash before any answer was read.</div>
</div>
<script>
const rows=__ROWS__; const rubric=__RUBRIC__; const columns=__COLUMNS__; const redlist=__REDLIST__;
const root=document.getElementById('cards');
const STORE='blind-challenge-scores-v1';
let state={};
try{state=JSON.parse(localStorage.getItem(STORE)||'{}')}catch(e){state={}}
function slot(id){if(!state[id])state[id]={pass_A:'',pass_B:'',critical_A:'',critical_B:'',preferred:'',notes:''};return state[id]}
function save(){try{localStorage.setItem(STORE,JSON.stringify(state))}catch(e){}}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function block(parent,label,text,cls){parent.appendChild(el('div','label',label));parent.appendChild(el('div',cls||'',text))}
function list(parent,title,items,cls){const w=el('div',cls);w.appendChild(el('strong','',title));const ul=document.createElement('ul');for(const it of (items||[])){ul.appendChild(el('li','',it))}w.appendChild(ul);parent.appendChild(w)}
function seg(id,key,options,onset){const box=el('span','seg');const buttons=[];for(const opt of options){const b=el('button',opt.cls,opt.text);b.type='button';b.setAttribute('aria-pressed',String(slot(id)[key]===opt.value));b.onclick=()=>{const cur=slot(id);if(cur[key]===opt.value)return;cur[key]=opt.value;onset(cur);for(const [j,other] of buttons.entries())other.setAttribute('aria-pressed',String(cur[key]===options[j].value));save();update()};buttons.push(b);box.appendChild(b)}return box}
function complete(v){return Boolean(v.pass_A&&v.pass_B&&v.critical_A&&v.critical_B&&v.preferred)}
function build(){for(const row of rows){const id=row.item_id;const rub=rubric[id]||{};const card=el('section','card');card.id='card-'+id;
  const head=el('div','head');head.appendChild(el('span','id',id));if(rub.kind)head.appendChild(el('span','tag',rub.kind));card.appendChild(head);
  block(card,'Customer message',row.query,'query');
  block(card,'Facts the assistant could know',row.facts,'facts');
  const rubBox=el('div','rub');list(rubBox,'A good reply does',rub.acceptable_actions,'ok');list(rubBox,'Critical fail if it',rub.critical_fail_if,'bad');card.appendChild(rubBox);
  for(const side of ['A','B']){
    block(card,'Answer '+side,row['answer_'+side],'answer');
    const line=el('div','side');line.appendChild(el('b','','Answer '+side));
    line.appendChild(seg(id,'pass_'+side,[{value:'true',text:'Pass',cls:'p'},{value:'false',text:'Fail',cls:'f'}],cur=>{if(cur['pass_'+side]==='true')cur['critical_'+side]='false';render(id)}));
    line.appendChild(seg(id,'critical_'+side,[{value:'true',text:'Critical',cls:'c'},{value:'false',text:'No critical'}],cur=>{if(cur['critical_'+side]==='true')cur['pass_'+side]='false';render(id)}));
    card.appendChild(line);
  }
  const pref=el('div','pref');pref.appendChild(el('b','','Preferred'));
  pref.appendChild(seg(id,'preferred',[{value:'A',text:'A'},{value:'B',text:'B'},{value:'tie',text:'Tie'}],()=>{}));
  card.appendChild(pref);
  const notes=el('input','notes');notes.type='text';notes.placeholder='Optional note (one line helps the failure write-up)';notes.value=slot(id).notes||'';notes.oninput=()=>{slot(id).notes=notes.value;save()};card.appendChild(notes);
  root.appendChild(card);}}
function render(id){const card=document.getElementById('card-'+id);if(!card)return;const cur=slot(id);const segs=card.querySelectorAll('.seg');const keys=['pass_A','critical_A','pass_B','critical_B','preferred'];const vals=[['true','false'],['true','false'],['true','false'],['true','false'],['A','B','tie']];
  segs.forEach((box,i)=>{const bs=box.querySelectorAll('button');bs.forEach((b,j)=>b.setAttribute('aria-pressed',String(cur[keys[i]]===vals[i][j])))});
  card.classList.toggle('done',complete(cur));card.classList.toggle('flag',cur.critical_A==='true'||cur.critical_B==='true')}
function update(){let done=0;for(const row of rows){const cur=slot(row.item_id);if(complete(cur))done++;render(row.item_id)}
  document.getElementById('count').textContent=done+' / '+rows.length+' scored';
  document.getElementById('fill').style.width=(rows.length?100*done/rows.length:0)+'%';
  const btn=document.getElementById('export');btn.disabled=done<rows.length;
  if(done>=rows.length&&rows.length){const g=document.getElementById('guide');if(g)g.open=false}}
function csvCell(v){return '"'+String(v===undefined||v===null?'':v).replaceAll('"','""')+'"'}
document.getElementById('export').onclick=()=>{
  const lines=[columns.join(',')];
  for(const row of rows){const cur=slot(row.item_id);const merged={...row,...cur};lines.push(columns.map(k=>csvCell(merged[k])).join(','))}
  const blob=new Blob([lines.join('\n')+'\n'],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='blind-sheet-scored.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),0)};
document.getElementById('next').onclick=()=>{const from=window.scrollY;let first=null;
  for(const row of rows){const card=document.getElementById('card-'+row.item_id);if(complete(slot(row.item_id)))continue;if(first===null)first=card;
    if(card.getBoundingClientRect().top>80){card.scrollIntoView();return}}
  if(first)first.scrollIntoView();else window.scrollTo({top:0});void from};
function buildRedList(){const host=document.getElementById('redbody');if(!host)return;let total=0;
  for(const fam of redlist){total+=fam.lines.length;
    const box=el('div','fam');
    const h=el('div','famhead');h.appendChild(el('b','',fam.name));h.appendChild(el('span','famcount',fam.lines.length+(fam.lines.length===1?' line':' lines')));box.appendChild(h);
    box.appendChild(el('p','fammean',fam.meaning));
    const ul=document.createElement('ul');
    for(const entry of fam.lines){const li=el('li');li.appendChild(el('span','',entry.line));li.appendChild(el('span','famid',entry.item));ul.appendChild(li)}
    box.appendChild(ul);host.appendChild(box)}
  const foot=el('p','note',total+' critical lines across '+rows.length+' cards, in '+redlist.length+' families.');host.appendChild(foot)}
buildRedList();build();update();
</script></body></html>
"""


def html_document(rows: list[dict[str, str]], rubric: dict[str, dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    rubric_json = json.dumps(rubric, ensure_ascii=False).replace("<", "\\u003c")
    columns = json.dumps(COLUMNS)
    red_json = json.dumps(red_list(rubric), ensure_ascii=False).replace("<", "\\u003c")
    template = HTML_TEMPLATE
    template = template.replace("__ROWS__", payload)
    template = template.replace("__RUBRIC__", rubric_json)
    template = template.replace("__COLUMNS__", columns)
    template = template.replace("__REDLIST__", red_json)
    return template


def main() -> int:
    args = parse_args()
    split_path = ROOT / "eval" / f"{args.split}.jsonl"
    base_path = args.base or RESULTS_DIR / f"base-{args.split}-raw.jsonl"
    tuned_path = args.tuned or RESULTS_DIR / f"tuned-{args.split}-raw.jsonl"
    seed_hash = sealed_hash(SEAL_PATH, split_path)
    scenarios = load_jsonl(split_path)
    rows, key = build_rows(
        scenarios,
        load_jsonl(base_path),
        load_jsonl(tuned_path),
        seed_hash=seed_hash,
    )
    rubric = scoring_rubric(scenarios)
    write_csv(args.csv, rows)
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(html_document(rows, rubric), encoding="utf-8")
    args.key.parent.mkdir(parents=True, exist_ok=True)
    args.key.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    print(f"items={len(rows)} answers={len(rows) * 2}")
    print(f"csv={args.csv} html={args.html} key={args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
