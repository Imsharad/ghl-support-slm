import json
from pathlib import Path
import subprocess

import pytest

from tools.artifacts.merge import artifact_hashes, select_prompt, validate_adapter


def test_prompt_comes_from_adapter_and_cannot_silently_change(tmp_path):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "prompt.txt").write_text("Actual training prompt\n")
    selected, prompt = select_prompt(adapter)
    assert selected == adapter / "prompt.txt" and prompt == "Actual training prompt"
    old = tmp_path / "old.txt"
    old.write_text("Historical business prompt")
    with pytest.raises(ValueError, match="differs"):
        select_prompt(adapter, old)


def test_missing_adapter_prompt_requires_explicit_provenance(tmp_path):
    with pytest.raises(ValueError, match="actual training"):
        select_prompt(tmp_path)
    explicit = tmp_path / "explicit.txt"
    explicit.write_text("Known old training prompt")
    assert select_prompt(tmp_path, explicit)[1] == "Known old training prompt"


def test_adapter_identity_and_weights_are_required(tmp_path):
    config = tmp_path / "adapter_config.json"
    config.write_text(json.dumps({"base_model_name_or_path": "expected"}))
    with pytest.raises(FileNotFoundError, match="safetensors"):
        validate_adapter(tmp_path, "expected")
    (tmp_path / "adapter_model.safetensors").write_bytes(b"test fixture")
    validate_adapter(tmp_path, "expected")
    with pytest.raises(ValueError, match="expected pinned"):
        validate_adapter(tmp_path, "other")


def test_artifact_fingerprint_excludes_optimizer_but_detects_adapter_change(tmp_path):
    weights = tmp_path / "adapter_model.safetensors"
    weights.write_bytes(b"before")
    (tmp_path / "state.pt").write_bytes(b"optimizer")
    before = artifact_hashes(tmp_path)
    assert set(before) == {"adapter_model.safetensors"}
    weights.write_bytes(b"after")
    assert artifact_hashes(tmp_path) != before


def test_conversion_refuses_existing_output_before_any_download(tmp_path):
    hf = tmp_path / "hf"
    hf.mkdir()
    output = tmp_path / "historical.gguf"
    output.write_bytes(b"preserved artifact")
    script = Path(__file__).resolve().parents[2] / "tools/artifacts/convert.sh"
    result = subprocess.run(["sh", str(script), str(hf), str(output)], capture_output=True, text=True)
    assert result.returncode != 0 and "output already exists" in result.stderr
    assert output.read_bytes() == b"preserved artifact"
