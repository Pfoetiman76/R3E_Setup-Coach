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
        for key in ("title", "tab_record", "tab_analyze", "tab_setups",
                    "record", "start", "stop", "outdir", "browse_out",
                    "auto_record", "auto_started",
                    "rec_state_stopped", "rec_state_waiting", "rec_state_recording",
                    "rec_saved", "rec_error",
                    "update_btn", "update_downloading", "update_restart",
                    "update_error", "saved",
                    "col_key", "col_target", "col_updated", "log"):
            assert key in gui.LABELS[lang], f"{lang}.{key}"


def test_gui_class_api():
    """0.8.0: Aufzeichnungs-API statt Bridge; Bridge-Methoden sind entfernt."""
    gui = _gui()
    for attr in ("install_update", "_on_update_done",
                 "start_recording", "stop_recording",
                 "_auto_start_recording", "_toggle_auto_record",
                 "browse_outdir", "browse_log",
                 "run_analyze", "run_analyze_save",
                 "reload_setups", "apply_setup_values"):
        assert hasattr(gui.CoachGui, attr)
    for gone in ("start_bridge", "stop_bridge", "browse_csv", "_poll_bridge"):
        assert not hasattr(gui.CoachGui, gone), f"entfernt erwartet: {gone}"


def test_gui_autorecord_pitboss_style():
    """0.8.1 (ohne PySide6): Automatische Aufzeichnung wie in PitBoss pruefen."""
    import ast, re
    src = open(__import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.dirname(
            __import__("os").path.abspath(__file__))), "r3e_coach", "gui.py"),
        encoding="utf-8").read()
    tree = ast.parse(src)
    # Haken existiert, Standard an, Persistenzschluessel auto_record
    assert "QCheckBox" in src
    assert 'self.config.get("auto_record", True)' in src
    assert 'data["auto_record"]' in src
    self_cls = [c for c in ast.walk(tree) if isinstance(c, ast.ClassDef)
                and c.name == "CoachGui"][0]
    names = {n.name for n in ast.walk(self_cls) if isinstance(n, ast.FunctionDef)}
    assert "_auto_start_recording" in names and "_toggle_auto_record" in names
    assert "_persist_auto_record" in names
    # App-Start triggert Auto-Start (singleShot 0 -> _auto_start_recording)
    assert "QTimer.singleShot(0, self._auto_start_recording)" in src
    # App-Ende schaltet den Automatik-Modus NICHT aus
    assert "closeEvent" in names
    m = re.search(r"def closeEvent\(self, event\):\s*self\.stop_recording\(user_stop=False\)", src)
    assert m, "closeEvent muss stop_recording(user_stop=False) aufrufen"
    # manueller Stop deaktiviert den Automatik-Modus
    assert "user_stop and self.auto_record_check.isChecked()" in src


def test_gui_starts_recorder_not_bridge(tmp_path, monkeypatch):
    """AST-Regression (ohne laufende GUI): Rekorder statt Bridge in gui.py."""
    import ast
    src = open(__import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.dirname(
            __import__("os").path.abspath(__file__))), "r3e_coach", "gui.py"),
        encoding="utf-8").read()
    assert "from .recorder import" in src
    assert "Recorder(" in src
    for gone in ("bridge_exe", "R2M", "start_bridge", "bridge.py", "placeholder"):
        assert gone not in src, f"Bridge-/Platzhalter-Rest in gui.py: {gone}"
    ast.parse(src)  # Syntax sicherstellen


def test_gui_config_roundtrip(tmp_path, monkeypatch):
    """Konfiguration: recordings_dir persistiert, alte Bridge-Schlüssel harmlos."""
    from r3e_coach import bridge_config
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".r3e-coach.json"
    cfg.write_text(json.dumps({"bridge_exe": "X:/old.exe",
                               "recordings_dir": "C:/rec"}), encoding="utf-8")
    data, path = bridge_config.load_gui_config(cfg)
    assert data["recordings_dir"] == "C:/rec"
    assert data["bridge_exe"] == "X:/old.exe"  # wird ignoriert, nicht gelöscht
    data["recordings_dir"] = "D:/neu"
    bridge_config.save_config(cfg, data)
    assert json.loads(cfg.read_text(encoding="utf-8"))["recordings_dir"] == "D:/neu"


def test_gui_qt_names_imported():
    """Regressionstest (laeuft ohne PySide6): Jeder in gui.py verwendete
    Q*-Name muss importiert sein — Vorfall 'QPlainTextEdit is not defined'
    in 0.5.0."""
    import ast
    import re
    path = __import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.dirname(
            __import__("os").path.abspath(__file__))), "r3e_coach", "gui.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                imported.add((a.asname or a.name).split(".")[-1])
    used = {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and re.match(r"^Q[A-Z]", n.id)}
    missing = used - imported
    assert not missing, f"In gui.py fehlende Qt-Importe: {sorted(missing)}"


def test_gui_record_tab_rows_separate():
    """0.9.1 (ohne PySide6): Haken und Start/Stop-Knoepfe in getrennten Zeilen."""
    src = open(__import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.dirname(
            __import__("os").path.abspath(__file__))), "r3e_coach", "gui.py"),
        encoding="utf-8").read()
    assert "grid.addWidget(self.auto_record_check, 2, 0, 1, 3)" in src
    assert "grid.addLayout(row, 3, 0, 1, 3)" in src
    assert "grid.addLayout(row, 2, 0, 1, 3)" not in src
