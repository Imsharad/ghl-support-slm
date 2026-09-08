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
    demo_v3.run_demo("http://fixture", call=call)
    assert len(requests) == 4
    assert requests[0]["query"] == requests[1]["query"]
    assert "awaiting actual human grading" in capsys.readouterr().out
