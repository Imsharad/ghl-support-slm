import json
from pathlib import Path
import zipfile

import pytest
import yaml

from tools.build_training_bundle import bundle_sources, create_bundle, inside
from tools.run_training_bundle import verify
from train.repro import sha256_file


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    files = ["pyproject.toml", "uv.lock", "README.md", "configs/versions.json", "configs/prompt.txt",
             "configs/custom.txt", "data/prepare.py", "tools/check_run.py", "tools/run_training_bundle.py",
             "tools/check_cuda_host.py",
             "train/train.py", "data/processed/candidate/train.jsonl", "data/processed/candidate/val.jsonl",
             "eval/private_final.jsonl", ".env"]
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture content\n")
    config = {"data": {"dir": "data/processed/candidate", "train_file": "train.jsonl", "val_file": "val.jsonl"},
              "hub": {"push_checkpoints": False}, "strict_reproducibility": True,
              "prompt_file": "configs/custom.txt"}
    (root / "configs/train.yaml").write_text(yaml.safe_dump(config))
    (root / "data/processed/candidate/manifest.json").write_text(json.dumps({"output_sha256": {
        split: sha256_file(root / f"data/processed/candidate/{split}.jsonl") for split in ("train", "val")}}))
    return root


def test_bundle_is_deterministic_and_excludes_test_data_and_credentials(source, tmp_path):
    first, second = tmp_path / "a.zip", tmp_path / "b.zip"
    a = create_bundle(source, Path("configs/train.yaml"), first, "fixture-commit")
    b = create_bundle(source, Path("configs/train.yaml"), second, "fixture-commit")
    assert a["sha256"] == b["sha256"]
    with zipfile.ZipFile(first) as archive:
        assert not any("eval/" in name or name == ".env" for name in archive.namelist())
        dest = tmp_path / "unpacked"
        archive.extractall(dest)  # archive is created in this test from an explicit safe whitelist
    assert verify(dest)["git_sha"] == "fixture-commit"
    (dest / "train/train.py").write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(dest)


def test_bundle_rejects_changed_data_publication_and_external_paths(source):
    data = source / "data/processed/candidate/train.jsonl"
    data.write_text("changed")
    with pytest.raises(ValueError, match="corpus manifest"):
        bundle_sources(source, Path("configs/train.yaml"))
    with pytest.raises(ValueError, match="escapes"):
        inside(source, source.parent / "outside.txt")
    config_path = source / "configs/train.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["hub"]["push_checkpoints"] = True
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="publication"):
        bundle_sources(source, config_path)
