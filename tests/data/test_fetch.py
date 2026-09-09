import json
import sys
import types

from data import fetch


def test_source_manifest_match_preserves_profiled_manifest():
    payload = {
        "repo_id": fetch.REPO_ID,
        "revision": fetch.REVISION,
        "source_filename": fetch.SOURCE_FILENAME,
        "sha256": "abc123",
        "row_count": fetch.EXPECTED_ROWS,
        "profiled_at": "sealed timestamp",
    }

    assert fetch.source_manifest_matches(payload, "abc123", fetch.EXPECTED_ROWS)
    assert not fetch.source_manifest_matches(payload, "different", fetch.EXPECTED_ROWS)
    assert not fetch.source_manifest_matches(payload, "abc123", fetch.EXPECTED_ROWS - 1)


def test_fetch_keeps_matching_profiled_manifest(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    csv_path = raw_dir / "bitext.csv"
    sha_path = raw_dir / "bitext.csv.sha256"
    sources_path = tmp_path / "sources.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / fetch.SOURCE_FILENAME).write_text("fixture", encoding="utf-8")

    original = {
        "repo_id": fetch.REPO_ID,
        "revision": fetch.REVISION,
        "source_filename": fetch.SOURCE_FILENAME,
        "sha256": "abc123",
        "row_count": fetch.EXPECTED_ROWS,
        "profiled_at": "sealed timestamp",
    }
    sources_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

    monkeypatch.setattr(fetch, "RAW_DIR", raw_dir)
    monkeypatch.setattr(fetch, "CSV_PATH", csv_path)
    monkeypatch.setattr(fetch, "SHA_PATH", sha_path)
    monkeypatch.setattr(fetch, "SOURCES_PATH", sources_path)
    monkeypatch.setattr(fetch, "sha256_file", lambda _: "abc123")
    monkeypatch.setattr(fetch, "count_rows", lambda _: fetch.EXPECTED_ROWS)
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(snapshot_download=lambda **_: str(cache_dir)),
    )

    assert fetch.fetch() == original
    assert json.loads(sources_path.read_text(encoding="utf-8")) == original
