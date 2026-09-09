from pathlib import Path
import sys

import pytest

from tools.evaluation import parity_check as parity


def test_custom_prompt_and_model_cli(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["parity_check", "--prompt-file", "custom.txt",
                                    "--model", "candidate", "--limit", "3"])
    args = parity.parse_args()
    assert args.prompt_file == Path("custom.txt")
    assert args.model == "candidate"
    assert args.limit == 3


def test_existing_report_is_preserved(tmp_path, monkeypatch):
    report = tmp_path / "existing.md"
    report.write_text("prior evidence")
    monkeypatch.setattr(sys, "argv", ["parity_check", "--output", str(report)])
    with pytest.raises(FileExistsError, match="existing evidence"):
        parity.main()
    assert report.read_text() == "prior evidence"


def test_report_binds_actual_prompt_and_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(parity, "ROOT", tmp_path)
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("custom prompt\n")
    gguf = tmp_path / "fixture.gguf"
    gguf.write_bytes(b"synthetic test artifact")
    report = parity.markdown_report(
        [parity.ParityRow("fixture", 12, True, 4, True)], gguf=gguf,
        converter_commit="fixture", model_revision="fixture",
        prompt_path=prompt, model_tag="fixture-model")
    assert "1-item parity check" in report
    assert "fixture-model" in report
    assert parity.sha256(prompt) in report
    assert "does not claim numerical equivalence" in report
