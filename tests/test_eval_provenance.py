import json

import pytest

from eval.run import OllamaRunner, ensure_run_manifest, inference_manifest


def test_manifest_refuses_changed_conditions_and_legacy_results(tmp_path):
    path = tmp_path / "outputs.jsonl"
    ensure_run_manifest(path, {"prompt": "first", "digest": "a"})
    ensure_run_manifest(path, {"prompt": "first", "digest": "a"})
    with pytest.raises(ValueError, match="manifest mismatch"):
        ensure_run_manifest(path, {"prompt": "second", "digest": "a"})
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text('{"id":"a"}\n')
    with pytest.raises(ValueError, match="no manifest"):
        ensure_run_manifest(legacy, {})
    assert legacy.read_text() == '{"id":"a"}\n'


def test_manifest_detects_same_id_with_changed_query(tmp_path):
    path = tmp_path / "split.jsonl"
    path.write_text('{"id":"a","query":"first"}\n')
    args = dict(split_path=path, system_prompt="card", model="base", backend="ollama",
                identity={"tag": "base", "digest": "a"})
    first = inference_manifest(**args)
    path.write_text('{"id":"a","query":"second"}\n')
    assert first != inference_manifest(**args)
    assert first["system_prompt"] == "card"


def test_ollama_uses_custom_prompt_exactly_once(monkeypatch):
    calls = []
    def post(url, payload, timeout):
        calls.append(payload)
        return {"message": {"content": "answer"}, "eval_count": 2}
    monkeypatch.setattr("eval.run.post_json", post)
    runner = OllamaRunner(tag="base", base_url="http://localhost:11434", timeout=10,
                          system_prompt="Exact custom card")
    assert runner("question").answer == "answer"
    assert calls[0]["messages"] == [
        {"role": "system", "content": "Exact custom card"},
        {"role": "user", "content": "question"}]
