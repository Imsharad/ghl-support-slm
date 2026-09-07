#!/usr/bin/env python3
"""Count admission and Bitext-template phrases in answer JSONL files.

v1 RESULTS.md published admission and template counts with no retained script.
This is the v2 method. Phrase lists are documented below and are not tuned to
reproduce the v1 numbers.

Input is JSONL. Text is taken from ``answer`` (eval raw answers) or, if that
key is absent, ``response`` (processed splits). Matching is case-insensitive.
Unicode apostrophes are folded to ASCII ``'`` so "I'm" and "I’m" are the same
phrase; no other normalisation is applied.

Admission (anywhere in the text), starting list from RESULTS.md plus the
three extra phrases in the V2-E0v brief:

- I don't have access
- I'm not able to
- I can't
- I do not have
- I'm unable to
- I don't know

``I can't`` is a substring of ``I can't assist with that``, so a refusal row
also increments the admission counter. The two are counted separately; the
lists are not made disjoint.

Bitext template phrases named in RESULTS.md:

- "I'm on it" and "I'm on the same wavelength" as openers (after leading
  whitespace only)
- "Rest assured" anywhere

Usage::

    uv run python eval/admission_scan.py eval/results/base-challenge-raw.jsonl
    uv run python eval/admission_scan.py eval/results/tuned-challenge-raw.jsonl \\
        data/processed/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ADMIT_PHRASES: tuple[str, ...] = (
    "i don't have access",
    "i'm not able to",
    "i can't",
    "i do not have",
    "i'm unable to",
    "i don't know",
)

TEMPLATE_OPENERS: tuple[str, ...] = (
    "i'm on it",
    "i'm on the same wavelength",
)

TEMPLATE_ANYWHERE: tuple[str, ...] = ("rest assured",)

REFUSE_PHRASE = "i can't assist with that"

APOSTROPHES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\u2032": "'",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="JSONL files of raw answers or processed rows",
    )
    return parser.parse_args()


def fold_apostrophes(text: str) -> str:
    for src, dst in APOSTROPHES.items():
        text = text.replace(src, dst)
    return text


def row_text(row: dict[str, Any]) -> str:
    if "answer" in row and row["answer"] is not None:
        return str(row["answer"])
    if "response" in row and row["response"] is not None:
        return str(row["response"])
    raise ValueError("row has neither 'answer' nor 'response'")


def scan_text(text: str) -> dict[str, Any]:
    folded = fold_apostrophes(text).casefold()
    opener = folded.lstrip()
    admit_hits = [p for p in ADMIT_PHRASES if p in folded]
    opener_hits = [p for p in TEMPLATE_OPENERS if opener.startswith(p)]
    anywhere_hits = [p for p in TEMPLATE_ANYWHERE if p in folded]
    return {
        "admit": bool(admit_hits),
        "admit_phrases": admit_hits,
        "im_on_it_opener": opener.startswith("i'm on it"),
        "wavelength_opener": opener.startswith("i'm on the same wavelength"),
        "rest_assured": "rest assured" in folded,
        "refuse": REFUSE_PHRASE in folded,
        "opener_hits": opener_hits,
        "anywhere_hits": anywhere_hits,
    }


def scan_file(path: Path) -> dict[str, Any]:
    n = 0
    admit = 0
    im_on_it = 0
    wavelength = 0
    rest = 0
    refuse = 0
    admit_phrase_counts = {p: 0 for p in ADMIT_PHRASES}
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: expected a JSON object")
            hits = scan_text(row_text(row))
            n += 1
            admit += int(hits["admit"])
            im_on_it += int(hits["im_on_it_opener"])
            wavelength += int(hits["wavelength_opener"])
            rest += int(hits["rest_assured"])
            refuse += int(hits["refuse"])
            for phrase in hits["admit_phrases"]:
                admit_phrase_counts[phrase] += 1
    return {
        "file": str(path),
        "rows": n,
        "admit": admit,
        "im_on_it_opener": im_on_it,
        "wavelength_opener": wavelength,
        "rest_assured": rest,
        "refuse": refuse,
        "admit_phrase_counts": admit_phrase_counts,
    }


def print_table(results: list[dict[str, Any]]) -> None:
    headers = (
        "file",
        "rows",
        "admit",
        "im_on_it_opener",
        "wavelength_opener",
        "rest_assured",
        "refuse",
    )
    rows = [headers]
    for item in results:
        rows.append(
            (
                item["file"],
                str(item["rows"]),
                str(item["admit"]),
                str(item["im_on_it_opener"]),
                str(item["wavelength_opener"]),
                str(item["rest_assured"]),
                str(item["refuse"]),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    print()
    print("admit phrase hits (a row may count in more than one phrase):")
    for item in results:
        parts = [f"{p}={c}" for p, c in item["admit_phrase_counts"].items() if c]
        print(f"  {item['file']}: " + (", ".join(parts) if parts else "none"))


def main() -> int:
    args = parse_args()
    results = []
    for path in args.files:
        if not path.is_file():
            print(f"not a file: {path}", file=sys.stderr)
            return 1
        results.append(scan_file(path))
    print_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
