import json

import pytest

from serve import record_demo_v3 as demo


def test_terminal_controls_are_not_executed():
    assert "\x1b" not in "".join(demo.safe_lines("hello\x1b[2Jworld"))
    assert max(map(len, demo.safe_lines("x " * 100))) <= 108


def test_recording_rejects_overflow_and_uses_real_clock(tmp_path, capsys):
    clock = [0.0]
    rec = demo.Recording(tmp_path, now=lambda: clock[0], wait=lambda s: clock.__setitem__(0, clock[0]+s))
    rec.screen("Synthetic page", ["fixture"])
    rec.hold(5)
    with pytest.raises(ValueError, match="overflow"):
        rec.screen("Too wide", ["x" * 111])
    assert rec.close() == 5
    records = [json.loads(line) for line in (tmp_path / "demo.cast").read_text().splitlines()]
    assert "env" not in records[0]
    assert records[1][0] == 0 and records[-1][0] == 5


def test_full_presentation_live_calls_and_layout(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    final = tmp_path / "eval/results/v3/final01"
    (final / "partial-mixed-analysis-001").mkdir(parents=True)
    health = {"tuned_configured": True, "prompt_sha256": "fixture", "models": {
        m: {"digest": m} for m in ("base", "tuned")}}
    (final / "SEAL.json").write_text(json.dumps({"inference": {"prompt_sha256": "fixture"}, "models": health["models"]}))
    analysis = {"observed": {"pass_counts": {"base": 59, "tuned": 81}, "micro_pass_rates": {"base": .55, "tuned": .76},
        "micro_difference_points": 20.75, "critical_failures": {"base": 11, "tuned": 9},
        "credential_violations": {"base": 1, "tuned": 2}}, "observed_macro_analysis": {
        "observed_macro_difference_points": 21.6, "observed_macro_cluster_ci95_points": [8.95,34.26]},
        "missing_case_sensitivity": {"worst_case": {"difference_points": 18.52}, "best_case": {"difference_points": 22.22}}}
    (final / "partial-mixed-analysis-001/analysis.json").write_text(json.dumps(analysis))
    source = tmp_path / "data/processed/v3-candidate03/val.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(json.dumps({"id": i, "instruction": "Synthetic query"}) for i in ("bitext-008038", "bitext-004940")))
    calls = []
    def call(url, payload=None):
        if payload is None:
            return health
        calls.append(payload)
        return {"model": payload["model"], "model_digest": payload["model"], "prompt_sha256": "fixture",
            "answer": "Synthetic response", "prompt_tokens": 10, "gen_tokens": 10, "latency_ms": 1,
            "request_latency_ms": 2, "tokens_per_s": 10, "truncated": False}
    clock = [0.0]
    def factory(directory):
        return demo.Recording(directory, now=lambda: clock[0], wait=lambda s: clock.__setitem__(0, clock[0]+s))
    result = demo.present(tmp_path / "out", "http://fixture", call=call, recorder=factory)
    assert 120 <= result["duration_seconds"] <= 300
    assert len(calls) == 4 and calls[0]["query"] == calls[1]["query"]
    assert len(result["scenes"]) == 9
    assert "safety gate FAILED" in capsys.readouterr().out
    assert json.loads((tmp_path / "out/live-http.json").read_text())["queries"][0]["responses"]["base"]["answer"] == "Synthetic response"
