from types import SimpleNamespace
import base64
import hashlib
import json
import sys

import pytest

from tools.evaluation.colab_existing import main, select_assignment, select_kernel


def test_exact_existing_assignment_only():
    existing = SimpleNamespace(endpoint="existing")
    assert select_assignment([existing], "existing") is existing
    with pytest.raises(ValueError):
        select_assignment([existing], "missing")
    with pytest.raises(ValueError):
        select_assignment([existing, existing], "existing")


@pytest.mark.parametrize("kernels", [[], [{"id": "a"}, {"id": "b"}], [{}]])
def test_never_guess_or_create_kernel(kernels):
    with pytest.raises(ValueError):
        select_kernel(kernels)


def test_single_existing_kernel():
    kernel = {"id": "a", "execution_state": "idle"}
    assert select_kernel([kernel]) is kernel


def setup_fake_download(monkeypatch, tmp_path, *, bad_hash=False, bad_name=False):
    payload = b"test artifact"
    manifest = {"schema": 1, "chunks": [{"name": "../bad" if bad_name else "part-00000",
                 "bytes": len(payload), "sha256": "0" * 64 if bad_hash else hashlib.sha256(payload).hexdigest()}]}
    assignment = SimpleNamespace(endpoint="existing", runtime_proxy_info=SimpleNamespace(url="https://example.invalid", token="synthetic"))
    monkeypatch.setitem(sys.modules, "colab_cli.common", SimpleNamespace(State=lambda: SimpleNamespace(
        client=SimpleNamespace(list_assignments=lambda: [assignment]))))
    monkeypatch.setitem(sys.modules, "colab_cli.runtime", SimpleNamespace(ColabRuntime=None))
    def get(url, **kwargs):
        content = json.dumps(manifest).encode() if url.endswith("manifest.json") else payload
        return SimpleNamespace(ok=True, json=lambda: {"type": "file", "format": "base64",
                                "content": base64.encodebytes(content).decode()})
    monkeypatch.setattr("requests.get", get)
    monkeypatch.setattr(sys, "argv", ["colab_existing", "--endpoint", "existing", "download-chunks", "/content/chunks", str(tmp_path / "download")])
    return payload


def test_verified_download_and_resume(monkeypatch, tmp_path):
    payload = setup_fake_download(monkeypatch, tmp_path)
    main()
    main()
    assert (tmp_path / "download/part-00000").read_bytes() == payload


@pytest.mark.parametrize("failure", ["bad_hash", "bad_name"])
def test_invalid_download_rejected(monkeypatch, tmp_path, failure):
    setup_fake_download(monkeypatch, tmp_path, **{failure: True})
    with pytest.raises(ValueError):
        main()
    assert not (tmp_path / "download/part-00000").exists()
