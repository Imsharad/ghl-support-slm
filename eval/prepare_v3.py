"""Compile and screen fresh v3 items, without generating answers or sealing models."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.audit_overlap_v3 import EMBEDDER, REVISION, grams, normalize
from train.repro import sha256_file

KINDS = ("missing_information", "supplied_context", "constraint_or_failed_attempt",
         "multi_request_or_boundary")
THRESHOLD = .86


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def validate_case(case: dict) -> None:
    if case.get("kind") not in KINDS:
        raise ValueError("unknown scenario kind")
    query = case.get("query")
    if not isinstance(query, str) or not normalize(query):
        raise ValueError("nonempty query required")
    if any(token in query for token in ("<|im_start|>", "<|im_end|>", "<|endoftext|>")):
        raise ValueError("chat control token in query")
    for field in ("acceptable_actions", "critical_fail_if"):
        values = case.get(field)
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"nonempty {field} checklist required")


def compile_drafts(drafts: list[dict], categories: dict[str, str], revisions: dict | None = None) -> list[dict]:
    rows, seen_intents = [], set()
    for draft in drafts:
        if draft.get("status") != "unsealed_draft_no_model_outputs_generated":
            raise ValueError("expected explicitly unsealed draft")
        for group in draft["intents"]:
            intent = group["intent"]
            if intent not in categories or intent in seen_intents:
                raise ValueError("unknown or duplicate intent")
            seen_intents.add(intent)
            if Counter(c.get("kind") for c in group["cases"]) != Counter(KINDS):
                raise ValueError("exactly one case of each kind required per intent")
            for case in group["cases"]:
                validate_case(case)
                rows.append(dict(case, id=f"v3-final-{intent}-{KINDS.index(case['kind']) + 1:02d}",
                                 intent=intent, category=categories[intent]))
    if seen_intents != set(categories):
        raise ValueError("drafts must cover every expected intent")
    by_id = {row["id"]: row for row in rows}
    for item_id, revision in (revisions or {}).items():
        if item_id not in by_id or not isinstance(revision.get("reason"), str) or not revision["reason"].strip():
            raise ValueError("revision needs a known ID and screening reason")
        case = revision["case"]
        validate_case(case)
        original = by_id[item_id]
        if case["kind"] != original["kind"]:
            raise ValueError("revision cannot change scenario kind")
        by_id[item_id] = {**original, **{field: case[field] for field in
                                      ("kind", "query", "acceptable_actions", "critical_fail_if")}}
    rows = sorted(by_id.values(), key=lambda row: row["id"])
    if len({normalize(row["query"]) for row in rows}) != len(rows):
        raise ValueError("duplicate normalized final query")
    return rows


def screen(rows: list[dict], pools: list[dict], left: np.ndarray, right: np.ndarray) -> dict:
    for vectors, expected in ((left, len(rows)), (right, len(pools))):
        if (vectors.ndim != 2 or len(vectors) != expected or not expected
                or not np.isfinite(vectors).all()
                or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)):
            raise ValueError("finite unit-normalized embeddings must match input rows")
    if left.shape[1] != right.shape[1]:
        raise ValueError("embedding dimensions differ")
    similarity = left @ right.T
    corpus_grams = set().union(*(grams(row["query"]) for row in pools))
    corpus_queries = {normalize(row["query"]) for row in pools}
    corpus_ids = {row["id"] for row in pools}
    results = []
    for row, scores in zip(rows, similarity):
        nearest = pools[int(np.argmax(scores))]
        shared = sorted(grams(row["query"]) & corpus_grams)
        exact = normalize(row["query"]) in corpus_queries
        same_id = row["id"] in corpus_ids
        maximum = float(scores.max())
        results.append({"id": row["id"], "max_cosine": maximum,
                        "nearest_id": nearest["id"], "nearest_source": nearest["source"],
                        "nearest_query": nearest["query"], "shared_sixgrams": shared,
                        "normalized_exact": exact, "duplicate_source_id": same_id,
                        "pass": maximum < THRESHOLD and not (shared or exact or same_id)})
    within = left @ left.T
    np.fill_diagonal(within, -np.inf)
    internal = [{"left_id": rows[i]["id"], "right_id": rows[j]["id"], "cosine": float(within[i, j])}
                for i, j in zip(*np.where(np.triu(within, 1) >= THRESHOLD))]
    return {"pass": all(result["pass"] for result in results), "threshold": THRESHOLD,
            "results": results, "within_final_pairs_at_threshold": internal,
            "within_final_note": "Descriptive redundancy audit; not an exclusion selected from model performance.",
            "limitation": "Query similarity screening is not proof of semantic independence or real-world representativeness."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", type=Path, nargs="+", required=True)
    parser.add_argument("--revisions", type=Path)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed/v3-candidate03")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("refusing to overwrite an audit; use a new output directory")
    categories_path = ROOT / "data/intents.json"
    categories = {row["intent"]: row["category"] for row in read_json(categories_path)}
    if len(categories) != 27:
        raise ValueError("expected the canonical 27 intents")
    rows = compile_drafts([read_json(path) for path in args.drafts], categories,
                          read_json(args.revisions) if args.revisions else None)
    # Mandatory comparators cannot be omitted through a CLI list.
    source_paths = [args.data_dir / "train.jsonl", args.data_dir / "val.jsonl",
                    ROOT / "eval/challenge.jsonl", ROOT / "eval/challenge_v2.jsonl"]
    pool, sources = [], {}
    for path in source_paths:
        sources[str(path)] = sha256_file(path)
        source_rows = [json.loads(line, object_pairs_hook=unique_object)
                       for line in path.read_text().splitlines() if line.strip()]
        if not source_rows:
            raise ValueError(f"empty comparison source: {path}")
        for row in source_rows:
            query = row.get("query") or row.get("instruction")
            if not isinstance(query, str) or not normalize(query):
                raise ValueError(f"missing source query: {path}")
            pool.append({"id": row["id"], "source": str(path), "query": query})
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDER, revision=REVISION, device="cpu",
                                local_files_only=not args.allow_download)
    vectors = model.encode([row["query"] for row in rows + pool], normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)
    report = screen(rows, pool, vectors[:len(rows)], vectors[len(rows):])
    args.output_dir.mkdir(parents=True)
    cases_path = args.output_dir / "cases.jsonl"
    with cases_path.open("x") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    inputs = args.drafts + ([args.revisions] if args.revisions else [])
    report.update(schema=1, status="screened_not_sealed" if report["pass"] else "rejected_draft",
                  n_cases=len(rows), n_comparators=len(pool), against_sha256=sources,
                  draft_sha256={str(path): sha256_file(path) for path in inputs},
                  cases_sha256=sha256_file(cases_path),
                  protocol_sha256=sha256_file(ROOT / "eval/v3/protocol.json"),
                  intents_sha256=sha256_file(categories_path),
                  screening_code_sha256=sha256_file(Path(__file__)),
                  normalization_code_sha256=sha256_file(ROOT / "data/audit_overlap_v3.py"),
                  embedding_model=EMBEDDER, embedding_revision=REVISION,
                  next_gate="Select candidate using development only, then bind artifacts and protocol in a final seal before inference.")
    with (args.output_dir / "screening.json").open("x") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"pass": report["pass"], "n_cases": len(rows), "n_comparators": len(pool),
                      "max_cosine": max(item["max_cosine"] for item in report["results"]),
                      "failed_ids": [item["id"] for item in report["results"] if not item["pass"]],
                      "output_dir": str(args.output_dir)}))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
