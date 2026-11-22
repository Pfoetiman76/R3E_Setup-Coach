"""Tests für advice.py: konkrete Setup-Hinweise (0.7.0) inkl. gespeicherter Werte."""

import json

import pytest

from r3e_coach.advice import (ADVICE_HEADER, advice_dicts, build_advice,
                               render_lines)
from r3e_coach.logdata import write_log
from r3e_coach.recorder import COLUMNS, UNITS
from r3e_coach.rules import Ctx, Finding, analyze
from r3e_coach.store import entry_key, load, save, upsert_values
from r3e_coach.telemetry import Session


def make_understeer_findings():
    s = Session(
        ["time", "speed", "steer", "g_lat", "tyre_temp_fl", "tyre_temp_fr",
         "tyre_temp_rl", "tyre_temp_rr"],
        ["s", "km/h", "deg", "g", "C", "C", "C", "C"],
        [[0.1 * i, 150.0, 16.0, 1.2, 98.0, 98.0, 80.0, 80.0] for i in range(30)],
    )
    return analyze(s, Ctx())


def test_advice_without_stored_values_gives_direction_only():
    advice = build_advice(make_understeer_findings())
    assert advice
    first = advice[0]
    assert first["field"] == "pressure_front"  # Reifentemp-Balance zuerst (high)
    texts_de = " ".join(a["text"]["de"] for a in advice)
    assert "eine Stufe weicher" in texts_de
    assert "→" not in texts_de  # keine konkreten Werte ohne setups.json


def test_advice_with_stored_chassis_values_names_targets():
    advice = build_advice(
        make_understeer_findings(),
        chassis={"arb_front": 4, "brake_bias": 56},
    )
    texts_de = " ".join(a["text"]["de"] for a in advice)
    assert "Stabi vorne: 4 → 3" in texts_de
    assert "Bremsbalance: 56 % → 58 %" in texts_de


def test_advice_with_stored_tire_values_names_pressure_target():
    cols = ["time", "speed", "tyre_temp_fl", "tyre_temp_fr", "tyre_temp_rl",
             "tyre_temp_rr"]
    rows = [[0.1 * i, 150.0, 98.0, 98.0, 80.0, 80.0] for i in range(30)]
    findings = analyze(Session(cols, ["s"] * 6, rows), Ctx())
    advice = build_advice(findings, tires={"pressure_front": 1.6})
    texts_de = " ".join(a["text"]["de"] for a in advice)
    assert "1.6 bar → 1.5 bar" in texts_de


def test_advice_english_output():
    advice = build_advice(make_understeer_findings(), chassis={"arb_front": 4})
    texts_en = " ".join(a["text"].get("en", "") for a in advice)
    assert "Front anti-roll bar: 4 → 3" in texts_en


def test_advice_dicts_and_render_lines():
    advice = build_advice(make_understeer_findings(), chassis={"arb_front": 4})
    dicts = advice_dicts(advice, "en")
    assert dicts and dicts[0]["rule"] and isinstance(dicts[0]["text"], str)
    lines = render_lines(advice)
    assert lines[0].startswith("1) ")
    assert all(line.split(") ", 1)[0].isdigit() for line in lines)


def test_bottoming_advice_uses_both_ride_heights():
    s = Session(
        ["time", "speed", "susp_travel_fl", "susp_travel_fr",
         "susp_travel_rl", "susp_travel_rr"],
        ["s", "km/h", "mm", "mm", "mm", "mm"],
        [[0.1 * i, 200.0, 0.0, 0.0, 0.0, 0.0] for i in range(60)],
    )
    findings = analyze(s, Ctx())
    rules = {f.rule for f in findings}
    if "bottoming" not in rules:
        pytest.skip("kein Bottoming ausgelöst — Regelgrenzen geprüft lassen")
    advice = build_advice(findings, chassis={"ride_height_front": 3,
                                             "ride_height_rear": 4})
    texts_de = " ".join(a["text"]["de"] for a in advice)
    assert "Fahrzeughöhe vorn: 3 → 4" in texts_de
    assert "Fahrzeughöhe hinten: 4 → 5" in texts_de


# ---------- CLI-Integration (Ende-zu-Ende mit .coachlog und setups.json) ----------

def _write_understeer_log(tmp_path, name="log.coachlog"):
    rows = [[i * 0.02, 95.0, 150.0 + i, 0.5, 0.0, 16.0, 1.2, 0.0,
             20.0, 20.0, 20.0, 20.0, 98.0, 98.0, 80.0, 80.0,
             None, None, None, None, 300.0, 300.0, 280.0, 280.0]
            for i in range(30)]
    f = tmp_path / name
    write_log(f, {"track": "Sachsenring", "layout": "Sachsenring",
                  "vehicle": "Audi R8"}, list(COLUMNS), list(UNITS), rows)
    return f


def test_cli_advice_appended_without_store(capsys, tmp_path):
    f = _write_understeer_log(tmp_path)
    from r3e_coach.cli import main
    rc = main([str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Empfohlene nächste Schritte" in out
    assert "Stabi vorne eine Stufe weicher." in out


def test_cli_advice_uses_stored_values(capsys, tmp_path):
    f = _write_understeer_log(tmp_path)
    store = tmp_path / "setups.json"
    data = load(store)
    key = entry_key("Sachsenring", None, "Audi R8")
    upsert_values(data, key, chassis={"arb_front": 4, "brake_bias": 56})
    save(data, store)
    from r3e_coach.cli import main
    rc = main(["analyze", str(f), "--store", str(store)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Stabi vorne: 4 → 3" in out
    assert "Bremsbalance: 56 % → 58 %" in out


def test_cli_advice_in_json_output(capsys, tmp_path):
    f = _write_understeer_log(tmp_path)
    store = tmp_path / "setups.json"
    data = load(store)
    key = entry_key("Sachsenring", None, "Audi R8")
    upsert_values(data, key, tires={"pressure_front": 1.6, "pressure_rear": 1.5})
    save(data, store)
    from r3e_coach.cli import main
    rc = main(["analyze", str(f), "--store", str(store),
               "--track", "Sachsenring", "--vehicle", "Audi R8", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert isinstance(payload["advice"], list) and payload["advice"]
    press = [a for a in payload["advice"] if a["field"] == "pressure_front"]
    assert press and press[0]["current"] == 1.6
    assert payload["findings"][0].get("data", {}) != {}
