#!/usr/bin/env python3
"""Validate, compare, and optionally seal a challenge JSONL file."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

import numpy as np

from eval.auto_metrics import EMBED_MODEL, embed_texts


ROOT = Path(__file__).resolve().parents[1]
INTENTS_PATH = ROOT / "data" / "intents.json"
BITEXT_PATH = ROOT / "data" / "raw" / "bitext.csv"
SEALED_CHALLENGE_PATH = ROOT / "eval" / "challenge_v2.jsonl"
SEAL_PATH = ROOT / "eval" / "SEAL_v2.json"
BITEXT_CAP = 0.85
AGAINST_CAP = 0.80
STORED_TOLERANCE = 0.0001
IST = ZoneInfo("Asia/Kolkata")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
BASE_FIELDS = {
    "id",
    "intent",
    "kind",
    "query",
    "facts",
    "acceptable_actions",
    "critical_fail_if",
    "max_bitext_cosine",
    "demo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("challenge", type=Path)
    parser.add_argument("--against", type=Path, nargs="+", default=[])
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--approval-event")
    parser.add_argument("--provenance")
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


def load_intents(path: Path = INTENTS_PATH) -> list[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected a list")
    intents: list[str] = []
    for index, row in enumerate(value, 1):
        if not isinstance(row, dict) or not isinstance(row.get("intent"), str):
            raise ValueError(f"{path}:{index}: missing string intent")
        intents.append(row["intent"])
    return intents


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_nonempty_string(item) for item in value)
    )


def _unit_float(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and np.isfinite(value)
        and 0.0 <= float(value) <= 1.0
    )


def schema_errors(
    rows: Sequence[dict[str, Any]],
    intents: Sequence[str],
    *,
    require_v1_cosine: bool,
) -> list[str]:
    """Return all structural errors without loading the embedding model."""
    errors: list[str] = []
    expected_fields = BASE_FIELDS | ({"max_v1_cosine"} if require_v1_cosine else set())
    allowed_fields = BASE_FIELDS | {"max_v1_cosine"}
    if len(rows) != len(intents) * 2:
        errors.append(f"expected {len(intents) * 2} rows, got {len(rows)}")

    ids: list[str] = []
    for index, row in enumerate(rows, 1):
        label = f"row {index}"
        missing = sorted(expected_fields - row.keys())
        extra = sorted(row.keys() - allowed_fields)
        if missing:
            errors.append(f"{label}: missing fields {missing}")
        if extra:
            errors.append(f"{label}: unexpected fields {extra}")
        item_id = row.get("id")
        if not _nonempty_string(item_id):
            errors.append(f"{label}: id must be a non-empty string")
        else:
            ids.append(item_id)
        for field in ("intent", "kind", "query", "facts"):
            if not _nonempty_string(row.get(field)):
                errors.append(f"{label}: {field} must be a non-empty string")
        for field in ("acceptable_actions", "critical_fail_if"):
            if not _nonempty_string_list(row.get(field)):
                errors.append(f"{label}: {field} must be a non-empty list of strings")
        if row.get("kind") not in {"ordinary", "hard"}:
            errors.append(f"{label}: kind must be ordinary or hard")
        if row.get("demo") is not False:
            errors.append(f"{label}: demo must be false")
        if not _unit_float(row.get("max_bitext_cosine")):
            errors.append(f"{label}: max_bitext_cosine must be between 0 and 1")
        if "max_v1_cosine" in row and not _unit_float(row.get("max_v1_cosine")):
            errors.append(f"{label}: max_v1_cosine must be between 0 and 1")

    if len(set(ids)) != len(ids):
        errors.append("ids must be unique")

    prefixes: list[str] = []
    for item_id in ids:
        match = re.fullmatch(r"(ch2|ch)-(\d{3})", item_id)
        if match is None:
            errors.append(f"{item_id}: id must match ch-NNN or ch2-NNN")
        else:
            prefixes.append(match.group(1))
    if prefixes and len(set(prefixes)) == 1 and len(prefixes) == len(rows):
        prefix = prefixes[0]
        expected_ids = [f"{prefix}-{index:03d}" for index in range(1, len(rows) + 1)]
        if ids != expected_ids:
            errors.append(f"ids must be ordered {prefix}-001 through {prefix}-{len(rows):03d}")
    elif prefixes:
        errors.append("all ids must use one prefix")

    expected_layout = [
        (intent, kind)
        for intent in intents
        for kind in ("ordinary", "hard")
    ]
    actual_layout = [(row.get("intent"), row.get("kind")) for row in rows]
    if actual_layout != expected_layout:
        errors.append("rows must follow data/intents.json order with ordinary then hard")
    return errors


def load_bitext_instructions(path: Path = BITEXT_PATH) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "instruction" not in reader.fieldnames:
            raise ValueError(f"{path}: missing instruction column")
        instructions = [str(row.get("instruction") or "").strip() for row in reader]
    if not instructions or any(not item for item in instructions):
        raise ValueError(f"{path}: instruction column contains no data or an empty row")
    return instructions


def word_ngrams(text: str, n: int = 6) -> set[tuple[str, ...]]:
    tokens = TOKEN_RE.findall(text.casefold())
    return {tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def shared_ngrams(query: str, against_queries: Sequence[str], n: int = 6) -> set[tuple[str, ...]]:
    query_grams = word_ngrams(query, n)
    if not query_grams:
        return set()
    against_grams: set[tuple[str, ...]] = set()
    for against in against_queries:
        against_grams.update(word_ngrams(against, n))
    return query_grams & against_grams


def ngram_source_index(
    against_rows: Sequence[dict[str, Any]], n: int = 6
) -> dict[tuple[str, ...], set[str]]:
    index: dict[tuple[str, ...], set[str]] = {}
    for row in against_rows:
        for ngram in word_ngrams(str(row["query"]), n):
            index.setdefault(ngram, set()).add(str(row["id"]))
    return index


def _max_cosines(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
        raise ValueError("embedding arrays must be 2D with matching widths")
    if right.shape[0] == 0:
        return np.full(left.shape[0], np.nan, dtype=np.float32)
    return np.max(left @ right.T, axis=1)


def recompute_metrics(
    rows: Sequence[dict[str, Any]],
    bitext_instructions: Sequence[str],
    against_rows: Sequence[dict[str, Any]],
    *,
    embedder: Callable[[list[str]], np.ndarray] = embed_texts,
) -> list[dict[str, Any]]:
    queries = [str(row["query"]) for row in rows]
    against_queries = [str(row["query"]) for row in against_rows]
    against_ngrams = ngram_source_index(against_rows)
    query_vectors = embedder(queries)
    bitext_vectors = embedder(list(bitext_instructions))
    bitext_max = _max_cosines(query_vectors, bitext_vectors)
    if against_queries:
        against_vectors = embedder(against_queries)
        against_max = _max_cosines(query_vectors, against_vectors)
    else:
        against_max = np.full(len(rows), np.nan, dtype=np.float32)
    results: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        shared = sorted(word_ngrams(queries[index]) & against_ngrams.keys())
        results.append({
            "id": str(row["id"]),
            "intent": str(row["intent"]),
            "kind": str(row["kind"]),
            "bitext_cosine": float(bitext_max[index]),
            "v1_cosine": float(against_max[index]),
            "six_gram_hits": len(shared),
            "six_gram_sources": {
                " ".join(ngram): sorted(against_ngrams[ngram]) for ngram in shared
            },
        })
    return results


def metric_errors(rows: Sequence[dict[str, Any]], metrics: Sequence[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for row, metric in zip(rows, metrics):
        item_id = str(row["id"])
        bitext = float(metric["bitext_cosine"])
        v1 = float(metric["v1_cosine"])
        if bitext >= BITEXT_CAP:
            errors.append(f"{item_id}: Bitext cosine {bitext:.4f} is not below {BITEXT_CAP:.2f}")
        if abs(float(row["max_bitext_cosine"]) - round(bitext, 4)) > STORED_TOLERANCE:
            errors.append(
                f"{item_id}: stored max_bitext_cosine {float(row['max_bitext_cosine']):.4f} "
                f"does not match recomputed {bitext:.4f}"
            )
        if np.isfinite(v1):
            if v1 >= AGAINST_CAP:
                errors.append(f"{item_id}: v1 cosine {v1:.4f} is not below {AGAINST_CAP:.2f}")
            if "max_v1_cosine" in row and (
                abs(float(row["max_v1_cosine"]) - round(v1, 4)) > STORED_TOLERANCE
            ):
                errors.append(
                    f"{item_id}: stored max_v1_cosine {float(row['max_v1_cosine']):.4f} "
                    f"does not match recomputed {v1:.4f}"
                )
        if metric["six_gram_hits"]:
            examples = "; ".join(
                f"{ngram!r} in {','.join(source_ids)}"
                for ngram, source_ids in metric["six_gram_sources"].items()
            )
            errors.append(
                f"{item_id}: shares {metric['six_gram_hits']} six-gram(s) with --against: "
                f"{examples}"
            )
    return errors


def print_table(metrics: Sequence[dict[str, Any]]) -> None:
    print("id       intent                       kind      bitext cosine  v1 cosine  6-gram hits")
    for metric in metrics:
        v1 = metric["v1_cosine"]
        v1_text = f"{v1:.4f}" if np.isfinite(v1) else "-"
        print(
            f"{metric['id']:<8} {metric['intent']:<28} {metric['kind']:<9} "
            f"{metric['bitext_cosine']:<14.4f} {v1_text:<10} {metric['six_gram_hits']}"
        )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def seal_challenge(
    draft_path: Path,
    rows: Sequence[dict[str, Any]],
    against_paths: Sequence[Path],
    *,
    approval_event: str,
    provenance: str,
) -> dict[str, Any]:
    if not HEX64_RE.fullmatch(approval_event):
        raise ValueError("--approval-event must be a lowercase 64-character hex event id")
    if not provenance.strip():
        raise ValueError("--provenance must be non-empty")
    if any(not re.fullmatch(r"ch2-\d{3}", str(row.get("id", ""))) for row in rows):
        raise ValueError("v2 sealing requires ch2-NNN ids")
    existing = [path for path in (SEALED_CHALLENGE_PATH, SEAL_PATH) if path.exists()]
    if existing:
        raise ValueError(
            "refusing to overwrite sealed output: "
            + ", ".join(display_path(path) for path in existing)
        )
    draft_bytes = draft_path.read_bytes()
    challenge_sha = hashlib.sha256(draft_bytes).hexdigest()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    seal = {
        "schema_version": 2,
        "challenge_sha256": challenge_sha,
        "challenge_path": display_path(SEALED_CHALLENGE_PATH),
        "rows": len(rows),
        "draft_sha256": challenge_sha,
        "draft_path": display_path(draft_path),
        "approved_by": "shark",
        "approval_event": approval_event,
        "approved_at": now,
        "sealed_by": "Fable 5.1",
        "sealed_at": now,
        "provenance": provenance.strip(),
        "against_sha256": {
            display_path(path): file_sha256(path) for path in against_paths
        },
        "embedding_model": EMBED_MODEL,
        "max_bitext_cosine_cap": BITEXT_CAP,
        "max_v1_cosine_cap": AGAINST_CAP,
        "six_gram_overlap_cap": 0,
        "rule": (
            "eval/challenge_v2.jsonl must not change after this seal; "
            "eval/blind.py refuses a mismatching hash"
        ),
    }
    SEALED_CHALLENGE_PATH.write_bytes(draft_bytes)
    SEAL_PATH.write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
    return seal


def main() -> int:
    args = parse_args()
    rows = load_jsonl(args.challenge)
    errors = schema_errors(
        rows,
        load_intents(),
        require_v1_cosine=bool(args.against),
    )
    if errors:
        print_table([])
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    against_rows = [row for path in args.against for row in load_jsonl(path)]
    metrics = recompute_metrics(rows, load_bitext_instructions(), against_rows)
    print_table(metrics)
    errors = metric_errors(rows, metrics)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    if args.seal:
        if not args.against:
            print("FAIL --seal requires --against", file=sys.stderr)
            return 1
        if not args.approval_event or args.provenance is None:
            print("FAIL --seal requires --approval-event and --provenance", file=sys.stderr)
            return 1
        try:
            seal = seal_challenge(
                args.challenge,
                rows,
                args.against,
                approval_event=args.approval_event,
                provenance=args.provenance,
            )
        except ValueError as exc:
            print(f"FAIL {exc}", file=sys.stderr)
            return 1
        print(f"SEALED {seal['challenge_path']} sha256={seal['challenge_sha256']}")
        print(f"SEAL {display_path(SEAL_PATH)}")
    print(f"PASS rows={len(rows)} embedding_model={EMBED_MODEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
