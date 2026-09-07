#!/usr/bin/env python3
"""A1 closer audit: is the step-3 closing clause concentrated across batches?

The generation prompt bans repeating a closing inside a batch and says nothing
across batches, so a fixed checklist can still collapse over the whole set. The
thresholds below were fixed by the orchestrator before any number was measured;
this module only counts and compares.

Concentrated if ANY of:
  * one normalised closing sentence in more than 10 percent of rows
  * one closing 6-gram in more than 10 percent of rows
  * one closing sentence or closing 6-gram across more than 5 intents
  * any of the prompt's three step-3 closer kinds above 60 percent of rows

Usage
-----
uv run python tools/closer_audit.py data/v2/admissions_raw.jsonl
uv run python tools/closer_audit.py data/v2/admissions_raw.jsonl --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

NGRAM_N = 6
PCT_ROWS = 0.10
MAX_INTENTS = 5
PCT_KIND = 0.60

WORD_RE = re.compile(r"[a-z][a-z'-]*")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# The three step-3 options the prompt offers, in the prompt's own order.
KIND_PATTERNS: dict[str, re.Pattern[str]] = {
    "where_to_look": re.compile(
        r"(?i)\b(you (?:will|can) see|look for|on that page|in that section|"
        r"under the|labelled|labeled|listed there|shown there|appears there|"
        r"where to look|the page will)\b"
    ),
    "draft_the_message": re.compile(
        r"(?i)\b(draft|you could write|you can write|word it|say something like|"
        r"here is (?:a|the) (?:message|note|wording)|when you write|"
        r"in your message|phrase it)\b"
    ),
    "have_to_hand": re.compile(
        r"(?i)\b(to hand|on hand|ready before|before you (?:go|start|write|contact)|"
        r"information you (?:should|will|would) (?:have|need)|"
        r"what (?:to have|you should have)|gather)\b"
    ),
}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).lower()
    return " ".join(WORD_RE.findall(text))


def last_sentence(answer: str) -> str:
    parts = [p.strip() for p in SENT_SPLIT.split(str(answer).strip()) if p.strip()]
    return parts[-1] if parts else ""


def ngrams(norm: str, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    words = norm.split()
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def classify(closer: str) -> list[str]:
    return [name for name, pat in KIND_PATTERNS.items() if pat.search(closer)]


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    sent_rows: Counter[str] = Counter()
    sent_intents: defaultdict[str, set[str]] = defaultdict(set)
    gram_rows: Counter[tuple[str, ...]] = Counter()
    gram_intents: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    kind_rows: Counter[str] = Counter()
    unclassified = 0

    for row in rows:
        intent = str(row.get("intent", "?"))
        closer = last_sentence(row.get("answer", ""))
        norm = normalise(closer)
        if not norm:
            continue
        sent_rows[norm] += 1
        sent_intents[norm].add(intent)
        for gram in ngrams(norm):
            gram_rows[gram] += 1
            gram_intents[gram].add(intent)
        kinds = classify(closer)
        if not kinds:
            unclassified += 1
        for kind in kinds:
            kind_rows[kind] += 1

    row_cap = PCT_ROWS * total
    kind_cap = PCT_KIND * total

    breaches: list[str] = []
    for norm, count in sent_rows.most_common():
        if count > row_cap:
            breaches.append(f"sentence in {count}/{total} rows (>10%): {norm[:90]!r}")
        if len(sent_intents[norm]) > MAX_INTENTS:
            breaches.append(
                f"sentence across {len(sent_intents[norm])} intents (>5): {norm[:90]!r}"
            )
    for gram, count in gram_rows.most_common():
        if count > row_cap:
            breaches.append(f"6-gram in {count}/{total} rows (>10%): {' '.join(gram)!r}")
        if len(gram_intents[gram]) > MAX_INTENTS:
            breaches.append(
                f"6-gram across {len(gram_intents[gram])} intents (>5): {' '.join(gram)!r}"
            )
    for kind, count in kind_rows.most_common():
        if count > kind_cap:
            breaches.append(f"closer kind {kind} in {count}/{total} rows (>60%)")

    return {
        "rows": total,
        "distinct_closing_sentences": len(sent_rows),
        "top_sentences": [
            {"n": c, "intents": len(sent_intents[s]), "text": s}
            for s, c in sent_rows.most_common(10)
        ],
        "top_6grams": [
            {"n": c, "intents": len(gram_intents[g]), "text": " ".join(g)}
            for g, c in gram_rows.most_common(10)
        ],
        "closer_kinds": {
            k: {"n": kind_rows.get(k, 0), "pct": round(100 * kind_rows.get(k, 0) / total, 1)}
            for k in KIND_PATTERNS
        },
        "unclassified_closers": unclassified,
        "thresholds": {
            "pct_rows": PCT_ROWS,
            "max_intents": MAX_INTENTS,
            "pct_kind": PCT_KIND,
            "ngram_n": NGRAM_N,
        },
        "breaches": breaches,
        "verdict": "CONCENTRATED" if breaches else "NOT_CONCENTRATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--json", default=None, help="also write the full report here")
    args = parser.parse_args(argv)

    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    if not rows:
        print("no rows", file=sys.stderr)
        return 1

    report = audit(rows)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"rows={report['rows']} distinct_closing_sentences={report['distinct_closing_sentences']}")
    print("closer kinds:")
    for kind, stat in report["closer_kinds"].items():
        print(f"  {kind:<20} {stat['n']:>4}  {stat['pct']:>5}%")
    print(f"  unclassified         {report['unclassified_closers']:>4}")
    print("top closing sentences:")
    for item in report["top_sentences"][:5]:
        print(f"  {item['n']:>4} rows / {item['intents']:>2} intents  {item['text'][:80]}")
    print("top closing 6-grams:")
    for item in report["top_6grams"][:5]:
        print(f"  {item['n']:>4} rows / {item['intents']:>2} intents  {item['text']}")
    print(f"verdict: {report['verdict']}")
    for breach in report["breaches"][:15]:
        print(f"  BREACH {breach}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
