import pytest

pytest.importorskip("PySide6")

import r3e_coach.gui as gui
from r3e_coach.gui import _app_icon, _icon_candidates


def test_icon_candidates_source_mode_end_with_app_ico():
    cands = _icon_candidates()
    assert cands
    assert all(str(c).endswith("app.ico") for c in cands)


def test_app_icon_none_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "_icon_candidates", lambda: [tmp_path / "app.ico"])
    assert _app_icon() is None


def test_app_icon_found_when_file_exists(monkeypatch, tmp_path):
    ico = tmp_path / "app.ico"
    ico.write_bytes(b"fake")
    monkeypatch.setattr(gui, "_icon_candidates", lambda: [ico])
    icon = _app_icon()
    assert icon is not None
    assert not icon.isNull()