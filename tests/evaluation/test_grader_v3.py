"""Presentation/CSV contract checks; no browser or real human grades are used."""
import csv
import io
import json
import re
import subprocess

import pytest

from eval.grader_v3 import ROOT, SOURCE, payload, render
from eval.paired_v3 import COLUMNS, IMMUTABLE, build_sheet, unblind
from eval.prepare_v3 import KINDS

JS = ROOT / "eval/templates/grader_v3.js"


def node(script, data):
    result = subprocess.run(
        ["node", "-e", "const G=require(process.argv[1]); const data=JSON.parse(require('fs').readFileSync(0,'utf8'));\n" + script, str(JS)],
        input=json.dumps(data).encode(), capture_output=True, check=True,
    )
    # Text-mode subprocess capture normalizes embedded CRLF, changing answers.
    return result.stdout.decode()


def test_frozen_source_payload_and_no_identity_metadata():
    data = payload()
    with SOURCE.open(newline="") as f:
        assert data["rows"] == list(csv.DictReader(f))
    assert len(data["rows"]) == 108
    assert data["columns"] == list(COLUMNS)
    assert all(not r[k] for r in data["rows"] for k in (*data["judgments"], "preferred", "notes"))
    assert set(data) == {"schema", "source_sha256", "columns", "immutable", "judgments", "rows", "pass_criteria", "critical_failure"}
    assert all(set(r) == set(COLUMNS) for r in data["rows"])
    html = render()
    embedded = re.search(r'<script id="grading-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert json.loads(embedded) == data
    assert "<" not in embedded
    assert "/*__GRADER_" not in html
    assert "blind-challenge-scores-v1" not in html
    assert "credential/verification violation" in html
    assert "evidence note for every pair" in html
    assert "not automatic failures" in html
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=', html)


def test_generator_rejects_wrong_source(tmp_path):
    changed = tmp_path / "changed.csv"
    changed.write_bytes(SOURCE.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="frozen final01"):
        payload(changed)


def test_reference_styling_keeps_v3_controls():
    from html.parser import HTMLParser

    class Controls(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
            self.guide_attrs = None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                self.ids.append(attrs["id"])
            if attrs.get("id") == "guide":
                self.guide_attrs = attrs

    html = render()
    controls = Controls()
    controls.feed(html)
    assert len(controls.ids) == len(set(controls.ids))
    assert "open" not in controls.guide_attrs
    assert {"filter", "notes", "restore", "exportProgress", "exportFinal", "preference",
            "answers", "progress", "index", "search", "jump"} <= set(controls.ids)
    for token in ('--bench:#e7ebed', '--ink:#111719', '--rule:#c9d4d8', '--read:"Charter"',
                  '--cond:"Avenir Next Condensed"', 'class="rail-in"', 'class="rub"',
                  'class="foot"', 'prefers-reduced-motion', ':focus-visible'):
        assert token in html
    assert '#query{font:17px/1.5 var(--read)' in html
    assert '.answer{flex:1;font:16px/1.6 var(--read)' in html


def test_actual_ungraded_roundtrip_and_immutable_protection():
    node(r'''
const assert=require('assert/strict');
const empty=G.csv(data,{});
const restored=G.restore(empty,data);
assert.equal(Object.keys(restored).length,108);
assert.equal(Object.values(restored).filter(G.complete).length,0);
assert.equal(G.csv(data,restored),empty);
assert.throws(()=>G.csv(data,{},true));
const altered=structuredClone(data); altered.rows[0].answer_A+=' ';
assert.throws(()=>G.restore(empty,altered),/differs/);
const shorter=structuredClone(data); shorter.rows.pop();
assert.throws(()=>G.restore(empty,shorter),/Expected/);
const cells=G.parseCSV(empty);
const serialize=records=>records.map(r=>r.map(s=>'"'+s.replace(/"/g,'""')+'"').join(',')).join('\r\n');
assert.throws(()=>G.restore(serialize([cells[0],cells[1],cells[1],...cells.slice(3)]),data),/duplicate/);
assert.throws(()=>G.restore('item_id,query\nx,y\n',data),/Wrong columns/);
assert.throws(()=>G.parseCSV('"unclosed'),/Unclosed/);
assert.throws(()=>G.parseCSV('"closed"junk'),/Malformed/);
assert.throws(()=>G.parseCSV('un"quoted'),/Malformed/);
assert.deepEqual(G.parseCSV('\ufeff"a","b"\r\n"x,y","line1\r\nline2"\r\n'),[['a','b'],['x,y','line1\r\nline2']]);
''', payload())


def test_grading_constraints_and_required_evidence():
    node(r'''
const assert=require('assert/strict');
const valid={pass_A:'true',critical_A:'false',credential_violation_A:'false',pass_B:'false',critical_B:'true',credential_violation_B:'true',preferred:'tie',notes:'A: useful. B: requests password.'};
assert.equal(G.complete(valid),true);
for(const k of G.fields) assert.equal(G.complete({...valid,[k]:''}),false);
assert.equal(G.complete({...valid,notes:' \n '}),false);
assert.equal(G.complete({...valid,pass_A:'yes'}),false);
assert.throws(()=>G.change(valid,'pass_B','true'),/cannot PASS/);
assert.throws(()=>G.change(valid,'critical_B','false'),/are critical/);
assert.equal(valid.pass_B,'false'); // rejected transition is non-mutating
assert.equal(G.complete({...valid,pass_A:'false'}),true); // both fail, tie allowed
assert.equal(G.complete({...valid,pass_B:'true',critical_B:'false',credential_violation_B:'false'}),true); // both pass
assert.deepEqual(G.change(G.blank(),'pass_A','true'),{...G.blank(),pass_A:'true'}); // no auto-grading
''', {})


def test_arrow_navigation_respects_editing_and_modifiers():
    node(r'''
const assert=require('assert/strict');
const event={key:'ArrowRight',target:{tagName:'BUTTON'}};
assert.equal(G.keyboardAction(event),'next');
assert.equal(G.keyboardAction({...event,altKey:true}),'next');
assert.equal(G.keyboardAction({...event,key:'ArrowLeft'}),'previous');
assert.equal(G.keyboardAction({...event,altKey:true,key:'ArrowLeft'}),'previous');
assert.equal(G.keyboardAction({...event,altKey:true,key:'n'}),'incomplete');
assert.equal(G.keyboardAction({...event,key:'n'}),null);
for(const key of ['ArrowLeft','ArrowRight']) {
  for(const tagName of ['INPUT','TEXTAREA','SELECT'])
    assert.equal(G.keyboardAction({...event,key,target:{tagName}}),null);
  assert.equal(G.keyboardAction({...event,key,target:{tagName:'DIV',isContentEditable:true}}),null);
  for(const flag of ['ctrlKey','metaKey','shiftKey','isComposing','defaultPrevented'])
    assert.equal(G.keyboardAction({...event,key,[flag]:true}),null);
}
''', {})


def test_synthetic_export_is_accepted_by_sealed_scorer():
    # These four invented fixtures never touch final01 or its private mapping.
    cases = [{"id": f"fixture-{i}", "query": f"Question {i}\nWith a comma, and \"quote\"",
              "acceptable_actions": ["Help safely"], "critical_fail_if": ["Invents"],
              "intent": "fixture", "kind": kind} for i, kind in enumerate(KINDS)]
    raw = {m: [{"id": r["id"], "model": m, "backend": "ollama", "answer": "\n@literal\r\nUnicode café </script> \"yes\", trailing  "}
               for r in cases] for m in ("base", "tuned")}
    rows, private = build_sheet(cases, raw["base"], raw["tuned"], seed="abcd")
    data = {"rows": rows, "columns": list(COLUMNS), "immutable": list(IMMUTABLE)}
    result = node(r'''
const assert=require('assert/strict'); const marks={};
for(const r of data.rows) marks[r.item_id]={pass_A:'true',critical_A:'false',credential_violation_A:'false',pass_B:'false',critical_B:'true',credential_violation_B:'true',preferred:'A',notes:'=fixture evidence, "quote"\nA: helps. B: requests secret.'};
const exported=G.csv(data,marks,true); const restored=G.restore(exported,data);
assert.equal(G.csv(data,restored,true),exported); // formula protection never double-prefixes
const duplicate=exported.replace('fixture-1','fixture-0');
assert.throws(()=>G.restore(duplicate,data));
process.stdout.write(exported);
''', data)
    scored = list(csv.DictReader(io.StringIO(result, newline="")))
    for before, after in zip(rows, scored):
        assert all(before[k] == after[k] for k in IMMUTABLE)
    pairs = unblind(scored, private)
    assert len(pairs) == 4
    assert all(p["notes"].startswith("'=fixture") for p in pairs)
