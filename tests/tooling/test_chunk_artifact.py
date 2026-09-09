import json

import pytest

from tools.artifacts.chunk_artifact import assemble, prepare


def test_roundtrip_and_no_overwrite(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"payload" * 99)
    parts = tmp_path / "parts"
    prepare(source, parts, chunk_bytes=20)
    output = tmp_path / "output"
    assemble(parts, output)
    assert output.read_bytes() == source.read_bytes()
    with pytest.raises(FileExistsError):
        prepare(source, parts)
    with pytest.raises(ValueError):
        assemble(parts, output)


def test_tampered_chunk_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    parts = tmp_path / "parts"
    prepare(source, parts)
    (parts / "part-00000").write_bytes(b"changed")
    with pytest.raises(ValueError):
        assemble(parts, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_manifest_path_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    parts = tmp_path / "parts"
    manifest = prepare(source, parts)
    manifest["chunks"][0]["name"] = "../source"
    (parts / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        assemble(parts, tmp_path / "output")
