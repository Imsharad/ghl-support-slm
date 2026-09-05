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


def html_document(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    columns = json.dumps(COLUMNS)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Blind challenge scoring</title>
<style>
body{{font:15px/1.45 -apple-system,BlinkMacSystemFont,sans-serif;max-width:1000px;margin:24px auto;padding:0 18px;color:#222}}
.bar{{position:sticky;top:0;background:#fff;padding:10px 0;border-bottom:1px solid #ccc;z-index:2;display:flex;gap:12px;align-items:center}}
.card{{border:1px solid #ccc;border-radius:8px;padding:14px;margin:14px 0}} .label{{font-size:12px;text-transform:uppercase;color:#666;margin-top:9px}}
.answer{{white-space:pre-wrap;background:#f6f6f6;padding:10px;border-radius:5px}} .scores{{display:grid;grid-template-columns:repeat(3,minmax(130px,1fr));gap:10px;margin-top:10px}}
select,input{{font:inherit;width:100%}} button{{font:inherit;padding:6px 12px}} .id{{font-weight:700}}
</style></head><body>
<div class="bar"><strong>Blind challenge scoring</strong><span id="progress"></span><button id="export">Export scored CSV</button></div>
<p>Score the text only. True/false fields must all be selected. A critical failure cannot also pass.</p><div id="cards"></div>
<script>
const rows={payload}; const columns={columns}; const root=document.getElementById('cards');
function select(values,cls){{const s=document.createElement('select');s.className=cls;for(const v of values){{const o=document.createElement('option');o.value=v;o.textContent=v||'select';s.appendChild(o)}}return s}}
function block(card,label,text,cls=''){{const l=document.createElement('div');l.className='label';l.textContent=label;card.appendChild(l);const b=document.createElement('div');b.className=cls;b.textContent=text;card.appendChild(b)}}
for(const [i,row] of rows.entries()){{const card=document.createElement('section');card.className='card';card.dataset.index=i;block(card,'Item',row.item_id,'id');block(card,'Query',row.query);block(card,'Facts',row.facts);block(card,'Answer A',row.answer_A,'answer');block(card,'Answer B',row.answer_B,'answer');const scores=document.createElement('div');scores.className='scores';for(const [label,key,values] of [['Pass A','pass_A',['','true','false']],['Critical A','critical_A',['','true','false']],['Pass B','pass_B',['','true','false']],['Critical B','critical_B',['','true','false']],['Preferred','preferred',['','A','B','tie']]]){{const w=document.createElement('label');w.textContent=label;const s=select(values,key);s.addEventListener('change',update);w.appendChild(s);scores.appendChild(w)}}const note=document.createElement('label');note.textContent='Notes';const input=document.createElement('input');input.className='notes';input.addEventListener('input',update);note.appendChild(input);scores.appendChild(note);card.appendChild(scores);root.appendChild(card)}}
function collect(){{return rows.map((row,i)=>{{const c=root.children[i];const out={{...row}};for(const key of ['pass_A','pass_B','critical_A','critical_B','preferred','notes'])out[key]=c.querySelector('.'+key).value;return out}})}}
function update(){{const done=collect().filter(r=>r.pass_A&&r.pass_B&&r.critical_A&&r.critical_B&&r.preferred).length;document.getElementById('progress').textContent=done+' / '+rows.length+' complete'}}
function csvCell(v){{return '"'+String(v).replaceAll('"','""')+'"'}}
document.getElementById('export').onclick=()=>{{const lines=[columns.join(','),...collect().map(r=>columns.map(k=>csvCell(r[k])).join(','))];const blob=new Blob([lines.join('\n')+'\n'],{{type:'text/csv;charset=utf-8'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='blind-sheet-scored.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),0)}};update();
</script></body></html>"""


def main() -> int:
    args = parse_args()
    split_path = ROOT / "eval" / f"{args.split}.jsonl"
    base_path = args.base or RESULTS_DIR / f"base-{args.split}-raw.jsonl"
    tuned_path = args.tuned or RESULTS_DIR / f"tuned-{args.split}-raw.jsonl"
    seed_hash = sealed_hash(SEAL_PATH, split_path)
    rows, key = build_rows(
        load_jsonl(split_path),
        load_jsonl(base_path),
        load_jsonl(tuned_path),
        seed_hash=seed_hash,
    )
    write_csv(args.csv, rows)
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(html_document(rows), encoding="utf-8")
    args.key.parent.mkdir(parents=True, exist_ok=True)
    args.key.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    print(f"items={len(rows)} answers={len(rows) * 2}")
    print(f"csv={args.csv} html={args.html} key={args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
