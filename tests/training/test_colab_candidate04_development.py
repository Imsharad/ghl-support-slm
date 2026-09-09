import hashlib
import zipfile

import pytest

from tools.evaluation.colab_candidate04_development import FILES, install_addon


def test_addon_is_exact_whitelist_and_preserves_existing(tmp_path):
    bundle = tmp_path / "addon.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        for name in FILES:
            archive.writestr(name, "fixture:" + name)
    sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
    root = tmp_path / "root"
    root.mkdir()
    install_addon(bundle, root, sha)
    install_addon(bundle, root, sha)
    (root / "eval/run.py").write_text("preserve this change")
    with pytest.raises(ValueError, match="preserve"):
        install_addon(bundle, root, sha)
    assert (root / "eval/run.py").read_text() == "preserve this change"


def test_addon_rejects_unlisted_member(tmp_path):
    bundle = tmp_path / "addon.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("eval/final-queries.jsonl", "excluded")
    with pytest.raises(ValueError, match="whitelist"):
        install_addon(bundle, tmp_path, hashlib.sha256(bundle.read_bytes()).hexdigest())
