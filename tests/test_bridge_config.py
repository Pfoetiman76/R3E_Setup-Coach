import pytest

from r3e_coach import bridge as b


def test_find_config_falls_back_to_exe_dir(tmp_path, monkeypatch):
    exe_dir = tmp_path / "R3E-Setup-Coach"
    exe_dir.mkdir()
    (exe_dir / ".r3e-coach.json").write_text('{"bridge_exe": "S:/x.exe"}', encoding="utf-8")
    monkeypatch.setattr(b.sys, "frozen", True, raising=False)
    monkeypatch.setattr(b.sys, "executable", str(exe_dir / "R3E-Setup-Coach.exe"))
    # cwd zeigt WOANDERS hin (Startmenü-Start): Config wird trotzdem gefunden
    monkeypatch.chdir(tmp_path / "..") if False else None
    path = b.find_config(None)
    assert path is not None
    assert b.load_config(path)["bridge_exe"] == "S:/x.exe"


def test_find_config_prefers_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(b.sys, "frozen", True, raising=False)
    monkeypatch.setattr(b.sys, "executable", str(tmp_path / "nowhere.exe"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".r3e-coach.json").write_text("{}", encoding="utf-8")
    assert b.find_config(None) == ".r3e-coach.json"


def test_save_config_atomic_and_mergeable(tmp_path):
    p = str(tmp_path / ".r3e-coach.json")
    (tmp_path / ".r3e-coach.json").write_text(
        '{"bridge_exe": "alt", "bridge_args": ["--port", "5566"]}', encoding="utf-8")
    data = b.load_config(p)
    data["bridge_exe"] = "neu"
    b.save_config(p, data)
    # alte, unbeteiligte Schluessel bleiben erhalten
    assert b.load_config(p)["bridge_args"] == ["--port", "5566"]
    assert b.load_config(p)["bridge_exe"] == "neu"
    assert not (tmp_path / ".r3e-coach.json.tmp").exists()


def test_default_config_path_next_to_exe(tmp_path, monkeypatch):
    exe_dir = tmp_path / "app"
    exe_dir.mkdir()
    monkeypatch.setattr(b.sys, "frozen", True, raising=False)
    monkeypatch.setattr(b.sys, "executable", str(exe_dir / "app.exe"))
    assert b.default_config_path() == str(exe_dir / ".r3e-coach.json")