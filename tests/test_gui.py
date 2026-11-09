import json

import pytest

from r3e_coach.cli import build_parser


def _gui():
    try:
        import PySide6  # noqa: F401
        import r3e_coach.gui
    except ImportError as exc:
        pytest.skip(f"PySide6 nicht verfügbar: {exc}")
    return r3e_coach.gui


def test_gui_subcommand_parses():
    args = build_parser().parse_args(["gui", "--lang", "en"])
    assert args.command == "gui"
    assert args.lang == "en"


def test_gui_labels_complete():
    gui = _gui()
    for lang in ("de", "en"):
        for key in ("title", "tab_bridge", "tab_analyze", "tab_setups",
                    "update_btn", "update_downloading", "update_restart",
                    "update_nextstart", "update_error", "saved",
                    "col_key", "col_target", "col_updated"):
            assert key in gui.LABELS[lang], f"{lang}.{key}"


def test_gui_class_api():
    gui = _gui()
    for attr in ("install_update", "_on_update_done", "start_bridge", "stop_bridge",
                 "browse_csv", "run_analyze", "run_analyze_save",
                 "reload_setups", "apply_setup_values"):
        assert hasattr(gui.CoachGui, attr)


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
