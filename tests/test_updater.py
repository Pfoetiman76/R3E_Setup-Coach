import io
import json

import pytest

from r3e_coach import updater
from r3e_coach.updater import (apply_pending_update, check_for_update, find_asset, is_newer,
                               parse_version, pending_path, run_update)


def test_parse_version():
    assert parse_version("v0.2.0") == (0, 2, 0)
    assert parse_version("1.2") == (1, 2)
    assert parse_version("quatsch") == ()


def test_is_newer():
    assert is_newer("v0.2.0", "0.1.0")
    assert is_newer("v1.0", "0.9.9")
    assert not is_newer("v0.2.0", "0.2.0")
    assert not is_newer("v0.1.9", "0.2.0")
    assert not is_newer("", "0.2.0")


FAKE_RELEASE = {
    "tag_name": "v9.9.9",
    "assets": [
        {"name": "R3E-Setup-Coach-win.zip", "browser_download_url": "https://example.invalid/app.zip"},
        {"name": "SHA256.txt", "browser_download_url": "https://example.invalid/sha.txt"},
    ],
}


def _fake_urlopen_factory(payload):
    def fake(req, timeout=10):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))
    return fake


def test_check_for_update_picks_zip(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen", _fake_urlopen_factory(FAKE_RELEASE))
    info = check_for_update()
    assert info is not None
    assert info.tag == "v9.9.9"
    assert info.name == "R3E-Setup-Coach-win.zip"


def test_check_for_update_none_when_current(monkeypatch):
    release = dict(FAKE_RELEASE, tag_name="v0.2.0")
    monkeypatch.setattr(updater.urllib.request, "urlopen", _fake_urlopen_factory(release))
    assert check_for_update() is None


def test_check_for_update_offline_returns_none(monkeypatch):
    def boom(req, timeout=10):
        raise OSError("offline")
    monkeypatch.setattr(updater.urllib.request, "urlopen", boom)
    assert check_for_update() is None


def test_find_asset_prefers_zip():
    asset = find_asset(FAKE_RELEASE)
    assert asset["name"].endswith(".zip")


def test_apply_pending_update_swaps_files(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"old")
    pending_path(str(exe))
    new = tmp_path / "app.exe.new"
    new.write_bytes(b"new")
    assert apply_pending_update(str(exe))
    assert exe.read_bytes() == b"new"
    assert not new.exists()
    assert not (tmp_path / "app.exe.old").exists()


def test_apply_pending_update_noop_without_pending(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"old")
    assert not apply_pending_update(str(exe))
    assert exe.read_bytes() == b"old"


def test_run_update_check_only_offline(capsys):
    rc = run_update(lang="de", check_only=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "neueste Version" in out
