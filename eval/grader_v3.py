"""Render an offline presentation of the existing final01 blind CSV; never reblind.

This presentation-only tool does not change sealed evaluation code or assign grades.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.paired_v3 import COLUMNS, IMMUTABLE, JUDGMENTS, verify_seal

SOURCE = ROOT / "eval/results/v3/final01/blind-sheet.csv"
SOURCE_SHA256 = "6e1a85144accf2704dc025a612155cd83f49dc901bd6a4a8305a433b0e47cdaa"


def payload(source: Path = SOURCE) -> dict:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Not the frozen final01 blind CSV; refusing to replace its assignments")
    seal = json.loads((SOURCE.parent / "SEAL.json").read_text())
    _, protocol = verify_seal(seal, ROOT / "eval/v3/screening02/cases.jsonl",
                              ROOT / "eval/v3/protocol.json")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    if reader.fieldnames != list(COLUMNS):
        raise ValueError("Unexpected grading columns")
    rows = list(reader)
    if len(rows) != 108 or len({r["item_id"] for r in rows}) != 108:
        raise ValueError("Expected 108 unique final pairs")
    return {"schema": 1, "source_sha256": digest, "columns": list(COLUMNS),
            "immutable": list(IMMUTABLE), "judgments": list(JUDGMENTS), "rows": rows,
            "pass_criteria": protocol["pass_criteria"],
            "critical_failure": protocol["critical_failure"]}


def render(source: Path = SOURCE) -> str:
    template = (ROOT / "eval/templates/grader_v3.html").read_text()
    script = (ROOT / "eval/templates/grader_v3.js").read_text()
    data = json.dumps(payload(source), ensure_ascii=False).replace("<", "\\u003c")
    return template.replace("/*__GRADER_SCRIPT__*/", script).replace("/*__GRADER_DATA__*/", data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SOURCE.with_suffix(".html"))
    args = parser.parse_args()
    html = render()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    print(f"Rendered 108 unchanged blind pairs to {args.output}")


if __name__ == "__main__":
    main()
