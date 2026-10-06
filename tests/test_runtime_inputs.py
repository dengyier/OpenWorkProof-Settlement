import importlib.util
import hashlib
import json
from pathlib import Path

import pytest
import subprocess


spec = importlib.util.spec_from_file_location(
    "runtime_inputs", Path(__file__).parents[1] / "scripts" / "fetch-runtime-inputs.py"
)
runtime_inputs = importlib.util.module_from_spec(spec)


def load_module():
    spec.loader.exec_module(runtime_inputs)
    return runtime_inputs


def test_locked_inputs_are_downloaded_and_hash_checked(tmp_path, monkeypatch):
    module = load_module()
    wheel, deb = b"locked wheel", b"locked Debian package"
    wheel_hash, deb_hash = (hashlib.sha256(data).hexdigest() for data in (wheel, deb))
    core = tmp_path / "core"
    images = core / "supply-chain" / "images"
    for role in ("execution", "trusted-helper"):
        (images / role).mkdir(parents=True)
        (images / role / "requirements.lock").write_text(
            f"example==1.0 \\\n    --hash=sha256:{wheel_hash}\n"
        )
    (images / "trusted-helper" / "debian-packages.lock").write_text(
        f"{deb_hash}\texample_1_arm64.deb\texample\t1\tarm64\n"
    )
    metadata = json.dumps({"urls": [{"filename": "example-1.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/example.whl", "size": len(wheel), "digests": {"sha256": wheel_hash}}]}).encode()
    def read_url(url, byte_range=None):
        if url.startswith("https://pypi.org/"):
            return metadata
        if "/mr/binary/" in url:
            return json.dumps({"result": [{"architecture": "arm64", "hash": "b" * 40}],
                "fileinfo": {"b" * 40: [{"size": len(deb)}]}}).encode()
        assert url.startswith(("https://files.pythonhosted.org/", "https://snapshot.debian.org/file/"))
        return wheel if url.endswith(".whl") else deb
    monkeypatch.setattr(module, "read_url", read_url)
    output = tmp_path / "inputs"
    module.fetch_inputs(core, output)
    assert (output / "wheels" / "example-1.0-py3-none-any.whl").read_bytes() == wheel
    assert (output / "debs" / "example_1_arm64.deb").read_bytes() == deb
    assert (output / "debs" / "SHA256SUMS").read_text() == f"{deb_hash}  example_1_arm64.deb\n"
    with pytest.raises(FileExistsError):
        module.fetch_inputs(core, output)


def test_tampered_download_is_not_written(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "read_url", lambda url: b"wrong bytes")
    with pytest.raises(ValueError, match="SHA-256"):
        module.download("https://files.pythonhosted.org/a.whl", tmp_path / "a.whl", "0" * 64, len(b"wrong bytes"))
    assert not (tmp_path / "a.whl").exists()


def test_lock_does_not_silently_select_another_version():
    module = load_module()
    with pytest.raises(ValueError, match="wheel hash"):
        module.wheel_requirements("example==1.0\n")


def test_snapshot_file_address_cannot_escape_repository(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "read_url", lambda url: json.dumps({"result": [
        {"architecture": "arm64", "hash": "../outside"}]}).encode())
    with pytest.raises(ValueError, match="ambiguous"):
        module.snapshot_location("example", "1", "arm64")


def test_snapshot_fallback_uses_exact_version_and_architecture(monkeypatch):
    module = load_module()
    urls = []
    def read_url(url):
        urls.append(url)
        return json.dumps({"result": [{"architecture": "amd64", "hash": "a" * 40},
            {"architecture": "arm64", "hash": "b" * 40}], "fileinfo": {"b" * 40: [{"size": 10}]}}).encode()
    monkeypatch.setattr(module, "read_url", read_url)
    assert module.snapshot_location("example", "1+b11", "arm64") == ("https://snapshot.debian.org/file/" + "b" * 40, 10)
    assert "/example/1%2Bb11/binfiles" in urls[0]
    with pytest.raises(ValueError, match="architecture"):
        module.snapshot_location("example", "1+b11", "all")


def test_curl_transport_is_https_only_bounded_and_fails_closed(monkeypatch):
    module = load_module()
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"verified later")
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.read_url("https://pypi.org/example") == b"verified later"
    argv, kwargs = calls[0]
    assert argv[argv.index("--retry") + 1] == "2"
    assert argv[argv.index("--proto-redir") + 1] == "=https"
    assert "--insecure" not in argv and "-k" not in argv
    assert "--max-time" in argv and "--max-filesize" in argv
    assert kwargs["check"] is True
    with pytest.raises(ValueError, match="HTTPS"):
        module.read_url("http://pypi.org/example")


def test_large_input_uses_bounded_ranges_and_checks_total_hash(tmp_path, monkeypatch):
    module = load_module()
    data = b"x" * (2 * 1024 * 1024 + 3)
    ranges = []
    def read_url(url, byte_range=None):
        ranges.append(byte_range)
        start, end = byte_range
        return data[start:end + 1]
    monkeypatch.setattr(module, "read_url", read_url)
    target = tmp_path / "large.deb"
    module.download("https://snapshot.debian.org/file/hash", target, hashlib.sha256(data).hexdigest(), len(data))
    assert target.read_bytes() == data
    assert ranges == [(0, 1048575), (1048576, 2097151), (2097152, 2097154)]
    monkeypatch.setattr(module, "read_url", lambda url, byte_range=None: data)
    with pytest.raises(ValueError, match="range"):
        module.download("https://snapshot.debian.org/file/hash", tmp_path / "ignored.deb", "0" * 64, len(data))
    assert not (tmp_path / "ignored.deb").exists()
