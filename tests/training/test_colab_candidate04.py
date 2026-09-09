import hashlib
from pathlib import Path
import zipfile

import pytest

from tools.evaluation.colab_candidate04 import extract_bundle


def make_zip(tmp_path, name):
    path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name, "example")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_extract_requires_expected_hash(tmp_path):
    path, sha = make_zip(tmp_path, "payload.txt")
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="SHA-256"):
        extract_bundle(path, output, "0" * 64)
    assert not output.exists()
    extract_bundle(path, output, sha)
    assert (output / "payload.txt").read_text() == "example"
    with pytest.raises(ValueError, match="preserve"):
        extract_bundle(path, output, sha)


@pytest.mark.parametrize("name", ["../escape", "/absolute"])
def test_extract_rejects_escaping_member(tmp_path, name):
    path, sha = make_zip(tmp_path, name)
    with pytest.raises(ValueError, match="unsafe"):
        extract_bundle(path, tmp_path / "out", sha)
