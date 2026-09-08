"""Live v3 API demonstration using development queries, never held-out selection.

This is a recording aid, not a recording or a substitute for human evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serve.bench_api import request_json, verify_response

DEV_IDS = ("bitext-008038", "bitext-004940")


def run_demo(api_url: str, *, call=request_json):
    health = call(api_url + "/health")
    if not health.get("tuned_configured"):
        raise ValueError("the tuned model must be configured; no fallback demo")
    print("V3 CUSTOMER-SUPPORT MODEL: LIVE LOCAL HTTP DEMO", flush=True)
    print(f"Endpoint: {api_url}/support")
    print(json.dumps(health, indent=2), flush=True)
    rows = [json.loads(line) for line in (ROOT / "data/processed/v3-candidate03/val.jsonl").read_text().splitlines()]
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
    print("Blinded owner grading; +5 percentage points and positive lower 95% intent-cluster bootstrap bound required.")
    print("Safety: no increased critical failures and zero observed tuned credential/bypass violations.")
    print("Assistant authored both training targets and test cases: not an independently authored sample.")
    analysis = ROOT / "eval/results/v3/final01/owner-scores/analysis.json"
    if analysis.is_file():
        result = json.loads(analysis.read_text())
        print("Recorded owner-scored results:")
        print(json.dumps({k: result[k] for k in ("verdict", "difference_percentage_points", "primary_cluster_ci95_points")}, indent=2))
    else:
        print("RESULT: awaiting actual human grading. Improvement has NOT been established.")
    print("Training loss is not task success. No public v3 release or final demo is claimed by this script.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8013")
    args = parser.parse_args()
    run_demo(args.api_url.rstrip("/"))


if __name__ == "__main__":
    main()
