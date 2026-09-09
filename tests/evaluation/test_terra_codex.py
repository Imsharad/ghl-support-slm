"""Codex subscription isolation and parser tests; no live model calls."""
import json
from pathlib import Path
import subprocess

import pytest

from eval import terra_codex as codex
from eval import terra_judge_v3 as judge


def events():
    return [{"type": "thread.started", "thread_id": "synthetic-thread"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "{}"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 30}}]


def test_command_starts_fresh_and_disables_context_and_tools():
    cmd = codex.command("/bin/codex", Path("/tmp/synthetic-pair"))
    assert cmd[1] == "exec" and cmd[-1] == "-"
    assert "resume" not in cmd and "fork" not in cmd
    assert "--ignore-user-config" in cmd and "--ephemeral" in cmd
    assert cmd[cmd.index("--sandbox")+1] == "read-only"
    assert cmd[cmd.index("--model")+1] == "gpt-5.6-terra"
    assert 'forced_login_method="chatgpt"' in cmd
    for name in ("memories", "shell_tool", "apps", "plugins", "multi_agent", "code_mode_host"):
        assert cmd[cmd.index(name)-1] == "--disable"
    assert 'memories.use_memories=false' in cmd
    assert 'project_doc_max_bytes=0' in cmd


def test_environment_drops_api_keys_and_inherited_task_context(monkeypatch):
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "CODEX_THREAD_ID", "RUNPOD_API_KEY", "OPENAI_BASE_URL"):
        monkeypatch.setenv(key, "NOT_FOR_GRADER")
    env = codex.environment()
    assert "NOT_FOR_GRADER" not in env.values()
    assert "PATH" in env and "HOME" in env


def test_subscription_auth_required_no_api_fallback(monkeypatch):
    monkeypatch.setattr(codex.shutil, "which", lambda _: "/bin/codex")
    def api_login(cmd, **kwargs):
        stdout = "codex-cli test" if "--version" in cmd else "Logged in using an API key"
        return subprocess.CompletedProcess(cmd, 0, stdout, "")
    monkeypatch.setattr(codex.subprocess, "run", api_login)
    with pytest.raises(ValueError, match="ChatGPT"):
        codex.CodexTransport()


def test_decode_one_turn_and_preserve_usage():
    raw = codex.decode_events("\n".join(map(json.dumps, events())), "model: gpt-5.6-terra\n", 0)
    assert raw["transport"] == "codex_chatgpt_subscription"
    assert raw["status"] == "completed"
    assert raw["usage"]["input_tokens"] == 100
    assert raw["id"] == "synthetic-thread"


@pytest.mark.parametrize("kind", ["command_execution", "mcp_tool_call", "web_search", "collab_tool_call", "file_change"])
def test_any_tool_event_invalidates_grade(kind):
    data = events()
    data.insert(2, {"type": "item.started", "item": {"type": kind}})
    with pytest.raises(ValueError, match="tools"):
        codex.decode_events("\n".join(map(json.dumps, data)), "", 0)


def test_failed_or_wrong_model_not_accepted():
    stdout = "\n".join(map(json.dumps, events()))
    with pytest.raises(ValueError):
        codex.decode_events(stdout, "", 1)
    with pytest.raises(ValueError, match="different model"):
        codex.decode_events(stdout, "model: other-model\n", 0)
    with pytest.raises(ValueError):
        codex.decode_events("\n".join(map(json.dumps, events()[:-1])), "", 0)


def test_only_known_isolation_diagnostics_are_allowed():
    data = events()
    for text in codex.EXPECTED_WARNINGS:
        data.insert(1, {"type": "item.completed", "item": {"type": "error", "message": text}})
    assert codex.decode_events("\n".join(map(json.dumps, data)), "", 0)["status"] == "completed"
    data.insert(1, {"type": "item.completed", "item": {"type": "error", "message": "Authentication failed"}})
    with pytest.raises(ValueError):
        codex.decode_events("\n".join(map(json.dumps, data)), "", 0)


def test_codex_is_default_dry_run_without_api_prices(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["judge", "--limit", "108"])
    judge.main()
    output = json.loads(capsys.readouterr().out)
    assert output["backend"] == "codex"
    assert output["billing"] == "existing_codex_subscription"
    assert output["sum_of_conservative_request_reservations_usd"] is None
    assert output["max_output_tokens_including_reasoning"] is None
