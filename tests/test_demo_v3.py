import json

import pytest

from serve import demo_v3


def test_demo_rejects_absent_tuned_model():
    with pytest.raises(ValueError, match="no fallback"):
        demo_v3.run_demo("http://fixture", call=lambda _: {"tuned_configured": False})


def test_demo_uses_actual_http_pairs_and_marks_missing_scores(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo_v3, "ROOT", tmp_path)
    source = tmp_path / "data/processed/v3-candidate03/val.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(json.dumps({"id": i, "instruction": "fixture " + i}) for i in demo_v3.DEV_IDS))
    health = {"tuned_configured": True, "prompt_sha256": "fixture", "models": {
        "base": {"digest": "base"}, "tuned": {"digest": "tuned"}}}
    requests = []
    def call(url, payload=None):
        if payload is None:
            return health
        requests.append(payload)
        return dict(payload, answer="synthetic test response", model_digest=payload["model"],
                    prompt_sha256="fixture", prompt_tokens=4, gen_tokens=4,
                    latency_ms=1, request_latency_ms=2, tokens_per_s=4, truncated=False)
    audit_path = tmp_path / "eval/results/v3/final01/mixed-review-001/audit.json"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(json.dumps({"status": "incomplete", "human_pairs": 29,
        "automated_pairs": 77, "missing_grade_questions": [107,108],
        "missing_human_evidence_questions": list(range(2,31)),
        "primary_all_human_evaluation_complete": False}))
    evidence = demo_v3.run_demo("http://fixture", call=call)
    assert len(requests) == 4
    assert requests[0]["query"] == requests[1]["query"]
    printed = capsys.readouterr().out
    assert "awaiting actual human grading" in printed
    assert "not 108 independent human judgments" in printed
    assert "29 human-marked and 77 automated" in printed
    assert len(evidence["queries"]) == 2
    assert evidence["queries"][0]["responses"]["base"]["answer"] == "synthetic test response"
    assert evidence["mixed_audit_status"]["primary_all_human_evaluation_complete"] is False
    partial = tmp_path / "eval/results/v3/final01/partial-mixed-analysis-001/analysis.json"
    partial.parent.mkdir(parents=True)
    partial.write_text(json.dumps({"observed": {"n": 106},
        "observed_numeric_gates_only": "not_demonstrated", "overall_improvement_established": False}))
    latest = demo_v3.run_demo("http://fixture", call=call)
    printed = capsys.readouterr().out
    assert "POST-HOC PARTIAL MIXED-JUDGE" in printed
    assert "awaiting actual human grading" not in printed
    assert latest["partial_analysis_status"]["overall_improvement_established"] is False
