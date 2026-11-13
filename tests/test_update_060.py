import os
import zipfile

import pytest

from r3e_coach import updater
from r3e_coach.updater import UpdateInfo, build_swap_cmd, is_newer, prepare_update


def test_is_newer_060_over_051():
    assert is_newer("v0.6.0", "0.5.1") is True
    assert is_newer("v0.6.0", "0.6.0") is False
    assert is_newer("v0.5.1", "0.6.0") is False


def test_build_swap_cmd_protects_user_files(tmp_path, monkeypatch):
    staging = str(tmp_path / "app.update")
    os.makedirs(staging)
    app = str(tmp_path / "app")
    os.makedirs(app)
    cmd = build_swap_cmd(app, staging)
    # geschützte Nutzerdateien und Hilfsdatei stehen im Exclude
    excl = open(os.path.join(staging, ".update-exclude"), encoding="ascii").read()
    assert ".r3e-coach.json" in excl
    assert "setups.json" in excl
    assert ".update-exclude" in excl
    # Batch: wartet auf Exe-Freigabe, kopiert, startet neu
    assert ":wait" in cmd
    assert f'ren "{app}\\R3E-Setup-Coach.exe"' in cmd
    assert f'xcopy "{staging}\\*"' in cmd
    assert f'start "" "{app}\\R3E-Setup-Coach.exe"' in cmd
    assert "rmdir /S /Q" in cmd


def test_prepare_update_stages_zip_and_cmd(tmp_path, monkeypatch):
    app = tmp_path / "R3E-Setup-Coach"
    app.mkdir()
    (app / "R3E-Setup-Coach.exe").write_bytes(b"old-exe")
    (app / "setups.json").write_text("{}", encoding="utf-8")

    zip_path = tmp_path / "fake.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("R3E-Setup-Coach.exe", b"new-exe")
        zf.writestr("_internal/dummy.txt", "x")
        zf.writestr(".r3e-coach.json", '{"bridge_exe": "S:/x.exe"}')

    def fake_download(url, dest, timeout=60):
        with open(zip_path, "rb") as src, open(dest, "wb") as out:
            out.write(src.read())
        return dest

    monkeypatch.setattr(updater, "download_update", fake_download)
    monkeypatch.setattr(updater, "app_dir", lambda: str(app))

    cmd_path = prepare_update(UpdateInfo("v0.6.0", "http://x/fake.zip", "fake.zip"))
    assert os.path.isfile(cmd_path)
    assert os.path.basename(cmd_path) == "apply-update.cmd"
    staging = os.path.join(str(tmp_path), "R3E-Setup-Coach.update")
    assert os.path.isfile(os.path.join(staging, "R3E-Setup-Coach.exe"))
    assert os.path.isfile(os.path.join(staging, "_internal", "dummy.txt"))
    assert not os.path.exists(os.path.join(staging, "update.zip"))
    # Exclude-Liste liegt im Staging und schützt Nutzerdaten
    excl = open(os.path.join(staging, ".update-exclude"), encoding="ascii").read()
    assert "setups.json" in excl and ".r3e-coach.json" in excl


def test_prepare_update_requires_app_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "app_dir", lambda: None)
    with pytest.raises(RuntimeError):
        prepare_update(UpdateInfo("v0.6.0", "http://x/fake.zip", "fake.zip"))