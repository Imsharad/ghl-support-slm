"""Validate and assemble provenance-labelled mixed grades without unblinding.

This never fills missing human notes or converts automated marks into human
scores. Outputs cannot be imported into the all-human grading sheet.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from eval.grader_v3 import payload
from eval.paired_v3 import COLUMNS, JUDGMENTS, sheet_text
from eval.terra_remaining_v3 import FIELDS, prepare
from eval import terra_judge_v3 as judge


def combine(data, raw_human, grades):
    prepare(raw_human, data)  # Validate identities, immutable fields, partial choices.
    human = {r["item_id"]: r for r in csv.DictReader(io.StringIO(raw_human.decode("utf-8-sig")))}
    if set(grades) - set(human):
        raise ValueError("Unexpected automated grade ID")
    rows, missing, missing_notes, overlap = [], [], [], []
    for position, original in enumerate(data["rows"], 1):
        item_id = original["item_id"]
        h = human[item_id]
        row = {**original, "question_number": position, "judge_source": "missing",
               "review_reason": "No grade available", "automated_evidence_A": "",
               "automated_evidence_B": ""}
        if any(h[k] for k in FIELDS):
            row.update({k: h[k] for k in FIELDS})
            row["judge_source"] = "human"
            absent = [k for k in FIELDS if not h[k].strip()]
            row["review_reason"] = "Missing human fields: " + ", ".join(absent) if absent else ""
            if "notes" in absent:
                missing_notes.append(position)
            if any(k in absent for k in (*JUDGMENTS, "preferred")):
                missing.append(position)
            if item_id in grades:
                overlap.append(position)  # Never overwrite a human judgment.
        elif item_id in grades:
            g = judge.validate_grade(grades[item_id], item_id)
            row.update({f"{k}_{s}": str(g[s][k]).lower() for s in ("A", "B") for k in judge.BOOL_FIELDS})
            row.update(judge_source="terra_human_calibrated_unreviewed", preferred=g["preferred"],
                       notes=sheet_text(g["preference_evidence"]),
                       automated_evidence_A=sheet_text(g["A"]["evidence"]),
                       automated_evidence_B=sheet_text(g["B"]["evidence"]),
                       review_reason="Automated grade, not independently approved" +
                       ("; judge flagged: " + g["uncertainty"] if g["needs_review"] else ""))
        else:
            missing.append(position)
        rows.append(row)
    summary = {
        "status": "incomplete" if missing or missing_notes else "assembled_unreviewed",
        "evaluation_design": "posthoc_mixed_human_and_human_calibrated_automated",
        "total_pairs": len(rows),
        "human_pairs": sum(r["judge_source"] == "human" for r in rows),
        "automated_pairs": sum(r["judge_source"] == "terra_human_calibrated_unreviewed" for r in rows),
        "missing_grade_questions": missing, "missing_human_evidence_questions": missing_notes,
        "human_precedence_overlap_questions": overlap,
        "primary_all_human_evaluation_complete": False,
        "models_unblinded": False, "improvement_established": False,
        "limitations": ["No all-human primary score is claimed.",
                        "The fixed 27 calibration examples came from this same test and lacked human evidence notes.",
                        "Fresh Codex sessions do not remove systematic judge bias.",
                        "Automated grade validity checks test structure and logic, not semantic correctness."],
    }
    return rows, summary


def audit(run_directory, human_path, output_directory):
    if output_directory.exists():
        raise ValueError("Refusing to overwrite prior audit")
    data = payload()
    raw_original = (run_directory / "human-progress-original.csv").read_bytes()
    selected, fixed, provenance = prepare(raw_original, data)
    binding = json.loads((run_directory / "manifest.json").read_text())["binding"]
    requests = {r["item_id"]: judge.request_for(r, fixed) for r in selected["rows"]}
    if (binding["source_sha256"] != data["source_sha256"] or binding["instructions"] != fixed
            or binding["provenance"] != provenance or binding["backend"] != "codex_chatgpt_subscription"
            or binding["request_sha256_by_id"] != {k: judge.digest(v) for k, v in requests.items()}):
        raise ValueError("Run/calibration/selection bindings differ")
    attempts = judge.read_history(run_directory / "attempts.jsonl", requests, subscription=True)
    grades = {a["item_id"]: a["finished"]["grade"] for a in attempts
              if a.get("finished", {}).get("status") == "valid"}
    raw_human = human_path.read_bytes()
    rows, summary = combine(data, raw_human, grades)
    files = {"human_export": human_path, "run_manifest": run_directory / "manifest.json",
             "run_journal": run_directory / "attempts.jsonl", "audit_code": Path(__file__)}
    summary.update(input_sha256={k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()},
                   attempts=len(attempts), valid_attempts=len(grades),
                   unsuccessful_attempts=[{"item_id": a["item_id"],
                                           "status": a.get("finished", {}).get("status", "interrupted")}
                                          for a in attempts if a.get("finished", {}).get("status") != "valid"])
    output_directory.mkdir(parents=True)
    with (output_directory / "mixed-grades-review.csv").open("x", newline="") as handle:
        columns = ["question_number", "judge_source", "review_reason", *COLUMNS,
                   "automated_evidence_A", "automated_evidence_B"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    with (output_directory / "audit.json").open("x") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--human-progress", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.run_directory, args.human_progress, args.output_directory), indent=2))


if __name__ == "__main__":
    main()
