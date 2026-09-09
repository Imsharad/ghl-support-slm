"""Live v3 API demonstration using development queries, never held-out selection.

This is a recording aid, not a recording or a substitute for human evaluation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serve.bench_api import request_json, verify_response

DEV_IDS = ("bitext-008038", "bitext-004940")


def run_demo(api_url: str, *, call=request_json):
    evidence = {"schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "api_url": api_url, "purpose": "live_development_demo_smoke_not_benchmark_or_video",
                "queries": []}
    health = call(api_url + "/health")
    if not health.get("tuned_configured"):
        raise ValueError("the tuned model must be configured; no fallback demo")
    print("V3 CUSTOMER-SUPPORT MODEL: LIVE LOCAL HTTP DEMO", flush=True)
    print(f"Endpoint: {api_url}/support")
    print(json.dumps(health, indent=2), flush=True)
    evidence["health"] = health
    rows = json.loads((ROOT / "serve/demo_queries_v3.json").read_text())["queries"]
    by_id = {row["id"]: row for row in rows}
    for item_id in DEV_IDS:
        query = by_id[item_id]["instruction"]
        print(f"\nDEVELOPMENT QUERY {item_id}: {query}", flush=True)
        answers = {}
        for model in ("base", "tuned"):
            print(f"Requesting {model} through HTTP...", flush=True)
            response = call(api_url + "/support", {"model": model, "query": query})
            verify_response(response, model, health)
            answers[model] = response
        evidence["queries"].append({"item_id": item_id, "query": query, "responses": answers})
        left = textwrap.wrap(answers["base"]["answer"], 52)
        right = textwrap.wrap(answers["tuned"]["answer"], 52)
        print(f"{'BASE':52} | TUNED")
        for index in range(max(len(left), len(right))):
            print(f"{left[index] if index < len(left) else '':52} | {right[index] if index < len(right) else ''}")
        for model, answer in answers.items():
            print(f"{model}: {answer['request_latency_ms']:.1f} ms, "
                  f"{answer['gen_tokens']} tokens, truncated={answer['truncated']}")
        if item_id == "bitext-004940":
            print("Failure check: no business payment policy was supplied. Neither model may assert PayPal acceptance.")
    print("\nEVALUATION DESIGN")
    print("108 screened, freshly authored cases; 27 intents; frozen artifacts/prompt/decoding.")
    print("Original protocol: blinded owner grading; +5 percentage points and positive lower 95% intent-cluster bootstrap bound required.")
    print("Safety: no increased critical failures and zero observed tuned credential/bypass violations.")
    print("Assistant authored both training targets and test cases: not an independently authored sample.")
    analysis = ROOT / "eval/results/v3/final01/owner-scores/analysis.json"
    partial = ROOT / "eval/results/v3/final01/partial-mixed-analysis-001/analysis.json"
    if analysis.is_file():
        result = json.loads(analysis.read_text())
        print("Recorded owner-scored results:")
        print(json.dumps({k: result[k] for k in ("verdict", "difference_percentage_points", "primary_cluster_ci95_points")}, indent=2))
    elif partial.is_file():
        result = json.loads(partial.read_text())
        print("Recorded POST-HOC PARTIAL MIXED-JUDGE results (not the original all-human primary test):")
        print(json.dumps({"observed": result["observed"],
                          "numeric_gates_only": result["observed_numeric_gates_only"],
                          "overall_improvement_established": result["overall_improvement_established"]}, indent=2))
        print("The owner omitted questions 107/108; missing human evidence notes remain disclosed.")
        evidence["partial_analysis_status"] = {k: result[k] for k in (
            "observed", "observed_numeric_gates_only", "overall_improvement_established")}
    else:
        print("RESULT: awaiting actual human grading. Improvement has NOT been established.")
    mixed = ROOT / "eval/results/v3/final01/mixed-review-001/audit.json"
    if mixed.is_file():
        audit = json.loads(mixed.read_text())
        print("POST-HOC DEVIATION: owner requested human-calibrated Terra for untouched pairs.")
        print(f"Saved audit: {audit['human_pairs']} human-marked and {audit['automated_pairs']} automated pairs.")
        print(f"Missing grades: {audit['missing_grade_questions']}; "
              f"human pairs missing evidence notes: {len(audit['missing_human_evidence_questions'])}.")
        print("This is not 108 independent human judgments or a successful primary result.")
        evidence["mixed_audit_status"] = {k: audit[k] for k in (
            "status", "human_pairs", "automated_pairs", "missing_grade_questions",
            "missing_human_evidence_questions", "primary_all_human_evaluation_complete")}
    print("Training loss is not task success. No public v3 release or final demo is claimed by this script.")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8013")
    parser.add_argument("--record-json", type=Path, help="Save actual HTTP response evidence to a new file; not a video recording")
    args = parser.parse_args()
    if args.record_json and args.record_json.exists():
        parser.error("Refusing to overwrite existing demo evidence")
    evidence = run_demo(args.api_url.rstrip("/"))
    if args.record_json:
        args.record_json.parent.mkdir(parents=True, exist_ok=True)
        with args.record_json.open("x") as handle:
            json.dump(evidence, handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    main()
