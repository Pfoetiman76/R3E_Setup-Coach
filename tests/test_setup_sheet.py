"""Tests für den Setup-Zettel (0.9.0): Aufbau, Dateiname, Datei, CLI, GUI-API."""

import os

import pytest

from r3e_coach import setup_sheet
from r3e_coach.advice import build_advice
from r3e_coach.cli import main
from r3e_coach.logdata import write_log
from r3e_coach.recorder import COLUMNS, UNITS
from r3e_coach.rules import Finding
from r3e_coach.setup_sheet import (build_sheet, suggest_filename, write_sheet)


def _advice_one():
    findings = [Finding(rule="understeer", category="balance", severity="hoch",
                       text={"de": "Untersteuern", "en": "Understeer"},
                       data={"direction": "understeer", "state": "mid"})]
    return build_advice(findings, {"arb_front": 4, "brake_bias": 56}, {})


def test_sheet_header_contains_meta():
    text = build_sheet({"track": "Sachsenring", "layout": "Sachsenring",
                       "vehicle": "Audi R8"}, _advice_one(), lang="de")
    assert text.startswith("R3E Setup-Coach — Setup-Zettel")
    assert "Fahrzeug: Audi R8" in text
    assert "Strecke: Sachsenring" in text
    assert "Erstellt:" in text


def test_sheet_steps_are_checklist():
    text = build_sheet({"track": "Sachsenring", "vehicle": "Audi R8"},
                      _advice_one(), lang="de")
    assert "[ ] " in text
    assert "Stabi vorne: 4 → 3" in text
    assert "[ ]" not in text.replace("[ ] ", "")  # kein leerer Kasten ohne Text


def test_sheet_empty_advice():
    text = build_sheet({"track": "Sachsenring", "vehicle": "Audi R8"}, [], lang="de")
    assert "Keine konkreten Setup-Änderungen abgeleitet." in text
    assert "[ ]" not in text


def test_sheet_english_and_note():
    text = build_sheet({"track": "Sachsenring", "vehicle": "Audi R8"},
                      _advice_one(), lang="en")
    assert "Setup Sheet" in text.splitlines()[0]
    assert "Vehicle: Audi R8" in text
    assert "garage display" in text


def test_sheet_filename_suggestion_sanitized():
    meta = {"track": "Nordschleife/Vln", "layout": "Vln", "vehicle": "Audi R8 LMS"}
    name = suggest_filename(meta)
    assert name == "Nordschleife_Vln_Vln_Audi_R8_LMS_setup-zettel.txt"
    assert "/" not in name


def test_write_sheet_atomic_and_crlf(tmp_path):
    path = str(tmp_path / "zettel.txt")
    text = build_sheet({"track": "Sachsenring", "vehicle": "Audi R8"}, [], lang="de")
    write_sheet(path, text)
    with open(path, "rb") as fh:
        raw = fh.read()
    assert b"\r\n" in raw
    assert not os.path.exists(path + ".tmp")
    assert raw.decode("utf-8") == text.replace("\n", "\r\n")


def _write_log(tmp_path):
    rows = [[i * 0.02, 95.0, 150.0 + i, 0.5, 0.0, 16.0, 1.2, 0.0,
             20.0, 20.0, 20.0, 20.0, 98.0, 98.0, 80.0, 80.0,
             None, None, None, None, 300.0, 300.0, 280.0, 280.0]
            for i in range(30)]
    f = tmp_path / "log.coachlog"
    meta = {"track": "Sachsenring", "layout": "Sachsenring",
            "vehicle": "Audi R8", "session_type": "practice"}
    write_log(f, meta, list(COLUMNS), list(UNITS), rows)
    return f


def test_cli_sheet_writes_file(tmp_path, capsys):
    f = _write_log(tmp_path)
    sheet = tmp_path / "zettel.txt"
    rc = main(["analyze", str(f), "--sheet", str(sheet)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Setup-Zettel geschrieben" in out
    text = sheet.read_text(encoding="utf-8")
    assert "Fahrzeug: Audi R8" in text
    assert "[ ] " in text


def test_cli_sheet_default_dir(tmp_path, capsys, monkeypatch):
    import r3e_coach.cli as cli_mod
    f = _write_log(tmp_path)
    monkeypatch.setattr(cli_mod, "default_sheets_dir", lambda: str(tmp_path / "sheets"))
    rc = main(["analyze", str(f), "--sheet"])
    out = capsys.readouterr().out
    assert rc == 0
    files = list((tmp_path / "sheets").glob("*.txt"))
    assert len(files) == 1
    assert "Sachsenring" in files[0].name
    assert out.count("Setup-Zettel geschrieben") == 1


def test_gui_sheet_api():
    """AST-Check ohne PySide6: Knopf, Handler und Builder sind verdrahtet."""
    import ast
    src = open(os.path.join(os.path.dirname(setup_sheet.__file__), "gui.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    names = {n.attr for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
             and n.value.id == "self"}
    methods = {n.name for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)}
    assert "make_setup_sheet" in methods
    assert '"sheet_btn"' in src and '"sheet_saved"' in src
    assert "build_sheet" in src and "write_sheet" in src and "suggest_filename" in src
    assert ".connect(self.make_setup_sheet)" in src
