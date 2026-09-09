"""Fresh Codex CLI transport using saved ChatGPT sign-in, never API-key fallback."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile


DISABLED = (
    "apps", "plugins", "remote_plugin", "memories", "context_management",
    "shell_tool", "unified_exec", "shell_snapshot", "code_mode_host",
    "multi_agent", "multi_agent_v2", "hooks", "browser_use", "browser_use_external",
    "computer_use", "in_app_browser", "in_app_chat", "image_generation", "view_image",
    "workspace_dependencies", "skill_search", "skill_mcp_dependency_install",
    "goals", "sleep_tool", "unbounded_connection_retries",
)
OVERRIDES = (
    'forced_login_method="chatgpt"', 'model_provider="openai"',
    'model_reasoning_effort="medium"', 'web_search="disabled"',
    'history.persistence="none"', 'memories.use_memories=false',
    'memories.generate_memories=false', 'project_doc_max_bytes=0',
    'skills.max_context_tokens=1', 'mcp_servers={}',
    'features.skip_host_skill_discovery=true', 'approval_policy="never"',
    'suppress_unstable_features_warning=true',
)
EXPECTED_WARNINGS = (
    "Code Mode is unavailable because code-mode host is disabled.",
    "Exceeded skills context budget. All skill descriptions were removed",
)


def environment():
    # Keep saved CLI authentication in its existing location. Never copy tokens
    # or repurpose HOME/CODEX_HOME. Drop unrelated task/session credentials.
    allowed = {"PATH", "HOME", "CODEX_HOME", "TMPDIR", "LANG", "LC_ALL", "USER", "LOGNAME", "SHELL"}
    return {k: v for k, v in os.environ.items() if k in allowed}


def command(binary, workdir):
    args = [binary, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
            "--skip-git-repo-check", "--sandbox", "read-only", "--model", "gpt-5.6-terra",
            "--cd", str(workdir), "--json", "--color", "never",
            "--output-schema", str(workdir / "schema.json")]
    for feature in DISABLED:
        args += ["--disable", feature]
    for override in (*OVERRIDES, 'model_instructions_file=' + json.dumps(str(workdir / "instructions.txt"))):
        args += ["-c", override]
    return args + ["-"]  # Prompt through stdin, not process-list arguments.


def decode_events(stdout, stderr, returncode):
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    if returncode != 0 or any(e.get("type") in ("error", "turn.failed") for e in events):
        raise ValueError("Codex run failed; no fallback model or API request")
    if sum(e.get("type") == "thread.started" for e in events) != 1 or sum(e.get("type") == "turn.completed" for e in events) != 1:
        raise ValueError("Expected one fresh completed Codex turn")
    # Reject any tools/commands/delegation: these are not allowed evidence.
    allowed_items = {"agent_message", "reasoning"}
    messages = []
    for event in events:
        if event.get("type", "").startswith("item."):
            item = event.get("item", {})
            if item.get("type") == "error" and any(item.get("message", "").startswith(prefix) for prefix in EXPECTED_WARNINGS):
                continue  # Known isolation diagnostics, retained in codex_events.
            if item.get("type") not in allowed_items:
                raise ValueError("Codex attempted tools or other non-grading actions")
            if event["type"] == "item.completed" and item.get("type") == "agent_message":
                messages.append(item["text"])
    if len(messages) != 1:
        raise ValueError("Expected exactly one final grade message")
    observed = re.search(r"^model:\s*(\S+)", stderr, re.M)
    if observed and observed[1] != "gpt-5.6-terra":
        raise ValueError("Codex returned a different model")
    usage = next(e.get("usage", {}) for e in events if e.get("type") == "turn.completed")
    return {"model": "gpt-5.6-terra", "status": "completed",
            "id": next(e["thread_id"] for e in events if e.get("type") == "thread.started"),
            "output": [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": messages[0]}]}],
            "usage": usage, "transport": "codex_chatgpt_subscription",
            "codex_events": events, "observed_model": observed[1] if observed else None}


class CodexTransport:
    def __init__(self):
        self.binary = shutil.which("codex")
        if not self.binary:
            raise ValueError("Codex CLI is missing")
        self.env = environment()
        version = subprocess.run([self.binary, "--version"], env=self.env, capture_output=True, text=True, timeout=15, check=True)
        self.version = version.stdout.strip()
        auth = subprocess.run([self.binary, "login", "status"], env=self.env, capture_output=True, text=True, timeout=15)
        if auth.returncode or "Logged in using ChatGPT" not in auth.stdout + auth.stderr:
            raise ValueError("Codex must be signed in with ChatGPT. No API-key fallback is allowed.")
        self.fingerprint = {"backend": "codex_chatgpt_subscription", "cli_version": self.version,
                            "transport_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "disabled_features": DISABLED, "config": OVERRIDES,
                            "ephemeral": True, "ignore_user_config": True,
                            "fresh_temp_directory_per_pair": True, "wall_timeout_seconds": 180}

    def __call__(self, request, _unused_key=None):
        # Each call gets a different cwd containing only static instructions and
        # schema. No shared files, final-model key, grading history, or repository.
        with tempfile.TemporaryDirectory(prefix="ghl-terra-pair-") as temporary:
            cwd = Path(temporary)
            (cwd / "schema.json").write_text(json.dumps(request["text"]["format"]["schema"]))
            (cwd / "instructions.txt").write_text(request["instructions"])
            prompt = request["input"][0]["content"]
            proc = subprocess.Popen(command(self.binary, cwd), cwd=cwd, env=self.env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, start_new_session=True)
            try:
                stdout, stderr = proc.communicate(prompt, timeout=180)
            except BaseException:
                # Kill only this task's process group; do not leave an orphan
                # consuming subscription usage after a timeout or interruption.
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()
                raise
            try:
                return decode_events(stdout, stderr, proc.returncode)
            except (ValueError, KeyError, TypeError):
                # Preserve raw execution evidence without printing it or hiding
                # attempted tools. The shared runner marks this response invalid.
                return {"model": "gpt-5.6-terra", "status": "failed",
                        "transport": "codex_chatgpt_subscription",
                        "codex_exit_code": proc.returncode,
                        "codex_stdout": stdout, "codex_stderr": stderr}
