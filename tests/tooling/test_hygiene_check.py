import subprocess
import sys

import pytest

from tools.quality import hygiene_check


@pytest.mark.parametrize("with_secret", [False, True])
def test_staged_binary_does_not_crash_or_hide_ascii_secrets(tmp_path, monkeypatch, with_secret):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    content = b"\x00\xff\xc6\x80 synthetic binary fixture\n"
    if with_secret:
        content += ("sk-" + "A" * 25).encode()
    (tmp_path / "fixture.mp4").write_bytes(content)
    subprocess.run(["git", "-C", str(tmp_path), "add", "fixture.mp4"], check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["hygiene_check", "--staged"])
    assert hygiene_check.main() == (1 if with_secret else 0)
