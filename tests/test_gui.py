import json

import pytest

from r3e_coach.cli import build_parser


def _gui():
    try:
        import tkinter  # noqa: F401
        import r3e_coach.gui
    except ImportError as exc:
        pytest.skip(f"tkinter nicht verfügbar: {exc}")
    return r3e_coach.gui


def test_gui_subcommand_parses():
    args = build_parser().parse_args(["gui", "--lang", "en"])
    assert args.command == "gui"
    assert args.lang == "en"


def test_gui_module_importable():
    gui = _gui()
    for lang in ("de", "en"):
        for key in ("update_btn", "update_downloading", "update_restart", "update_nextstart", "update_error"):
            assert key in gui.LABELS[lang]
    assert hasattr(gui.CoachGui, "install_update")
    assert hasattr(gui.CoachGui, "_on_update_done")


def test_load_gui_config(tmp_path, monkeypatch):
    gui = _gui()
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".r3e-coach.json"
    cfg.write_text(json.dumps({"bridge_exe": "X:/bridge.exe"}), encoding="utf-8")
    assert gui.load_gui_config(None)["bridge_exe"] == "X:/bridge.exe"
    assert gui.load_gui_config(None) == gui.load_gui_config(".r3e-coach.json")


def test_load_gui_config_empty_without_file(tmp_path, monkeypatch):
    gui = _gui()
    monkeypatch.chdir(tmp_path)
    assert gui.load_gui_config(None) == {}
