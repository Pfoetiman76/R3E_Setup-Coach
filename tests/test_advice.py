"""0.7.0: konkrete priorisierte Setup-Hinweise (advice.py) + Integration.

Läuft ohne PySide6 (Kern ist Qt-frei), deckt rules-data, advice-Ziele
und die CLI-Integration ab.
"""

import json

import pytest

from r3e_coach.advice import ADVICE_HEADER, advice_dicts, build_advice, render_lines
from r3e_coach.cli import main
from r3e_coach.rules import Ctx, Finding, analyze
from r3e_coach.store import entry_key, load, save, upsert_values
from r3e_coach.telemetry import Session


def make_session(**cols):
    names = list(cols.keys())
    rows = [list(r) for r in zip(*cols.values())]
    return Session(names, [""] * len(names), rows)


def base(n=60, speed=150.0):
    return {
        "Time": [float(i) for i in range(n)],
        "Speed": [speed] * n,
        "Throttle": [0.5] * n,
        "Brake": [0.0] * n,
        "Steering_Angle": [0.0] * n,
        "G_Lat": [0.0] * n,
        "G_Long": [0.0] * n,
        "Tyre Temp FL": [85.0] * n,
        "Tyre Temp FR": [85.0] * n,
        "Tyre Temp RL": [85.0] * n,
        "Tyre Temp RR": [85.0] * n,
        "Brake Temp FL": [300.0] * n,
        "Brake Temp FR": [300.0] * n,
        "Brake Temp RL": [300.0] * n,
        "Brake Temp RR": [300.0] * n,
        "Susp Travel FL": [20.0] * n,
        "Susp Travel FR": [20.0] * n,
        "Susp Travel RL": [20.0] * n,
        "Susp Travel RR": [20.0] * n,
        "Lap Time": [95.0] * n,
    }


def understeer_session():
    cols = base()
    for i in range(60):
        cols["G_Lat"][i] = 1.2
        cols["Steering_Angle"][i] = 16.0
    return make_session(**cols)


# ---------- rules: strukturierte data ----------

def test_findings_carry_structured_data():
    cols = base()
    cols["Tyre Temp FL"] = [98.0] * 60
    cols["Tyre Temp FR"] = [98.0] * 60
    findings = analyze(make_session(**cols), Ctx())
    f = next(f for f in findings if f.rule == "tyre_temp_balance")
    assert f.data["direction"] == "front_hot"
    assert f.data["front"] > f.data["rear"]


def test_brake_direction_and_lockups_in_data():
    cols = base()
    for i in range(60):
        cols["Brake"][i] = 0.8
    cols["Brake Temp FL"] = [520.0] * 60
    cols["Brake Temp FR"] = [520.0] * 60
    findings = analyze(make_session(**cols), Ctx())
    f = next(f for f in findings if f.rule == "brake_balance")
    assert f.data["direction"] == "too_front"
    assert f.data["lockups"] >= 0


def test_finding_default_data_is_empty_dict():
    f = Finding("x", "tyres", "low", {"de": "", "en": ""})
    assert f.data == {}


# ---------- advice: konkrete Ziele ----------

def test_understeer_advice_with_stored_values():
    findings = analyze(understeer_session(), Ctx())
    chassis = {"arb_front": 4, "brake_bias": 56}
    advice = build_advice(findings, chassis=chassis)
    arb = next(a for a in advice if a["field"] == "arb_front")
    assert arb["current"] == 4 and arb["target"] == 3
    assert "4 → 3" in arb["text"]["de"]
    bias = next(a for a in advice if a["field"] == "brake_bias")
    assert bias["current"] == 56 and bias["target"] == 58
    assert "56 % → 58 %" in bias["text"]["de"]


def test_understeer_advice_without_stored_values():
    findings = analyze(understeer_session(), Ctx())
    advice = build_advice(findings)
    arb = next(a for a in advice if a["field"] == "arb_front")
    assert arb["current"] is None and arb["target"] is None
    assert "eine Stufe weicher" in arb["text"]["de"]


def test_brake_balance_directions():
    f_front = Finding("brake_balance", "brakes", "medium", {"de": "", "en": ""},
                      data={"direction": "too_front"})
    f_rear = Finding("brake_balance", "brakes", "medium", {"de": "", "en": ""},
                     data={"direction": "too_rear"})
    chassis = {"brake_bias": 56}
    adv_front = build_advice([f_front], chassis=chassis)
    adv_rear = build_advice([f_rear], chassis=chassis)
    assert adv_front[0]["target"] == 54
    assert adv_rear[0]["target"] == 58


def test_tyre_window_pressure_targets():
    f = Finding("tyre_temp_window", "tyres", "medium", {"de": "", "en": ""},
                data={"state": "hot"})
    tires = {"pressure_front": 1.9, "pressure_rear": 2.0}
    advice = build_advice([f], tires=tires)
    front = next(a for a in advice if a["field"] == "pressure_front")
    rear = next(a for a in advice if a["field"] == "pressure_rear")
    assert front["target"] == pytest.approx(1.8)
    assert rear["target"] == pytest.approx(1.9)
    assert "1.9 bar → 1.8 bar" in front["text"]["de"]


def test_bottoming_raises_both_ride_heights():
    f = Finding("bottoming", "suspension", "medium", {"de": "", "en": ""},
                data={"min_travel": 1.0})
    chassis = {"ride_height_front": 5, "ride_height_rear": 6}
    advice = build_advice([f], chassis=chassis)
    fields = [a["field"] for a in advice]
    assert fields == ["ride_height_front", "ride_height_rear"]
    assert advice[0]["target"] == 6 and advice[1]["target"] == 7


def test_consistency_produces_no_setup_advice():
    f = Finding("consistency", "consistency", "low", {"de": "", "en": ""},
                data={"delta_pct": 2.0})
    assert build_advice([f]) == []


def test_severity_priority_order_preserved():
    high = Finding("understeer", "handling", "high", {"de": "", "en": ""})
    medium = Finding("bottoming", "suspension", "medium", {"de": "", "en": ""})
    advice = build_advice([high, medium])
    assert advice[0]["severity"] == "high"


# ---------- advice: Ausgabe ----------

def test_render_lines_numbered_and_dicts_localized():
    f = Finding("brake_balance", "brakes", "high", {"de": "", "en": ""},
                data={"direction": "too_front"})
    advice = build_advice([f], chassis={"brake_bias": 56})
    lines = render_lines(advice, lang="de")
    assert lines == ["1) Bremsbalance: 56 % → 54 % (senken um 2 %; "
                     "Grund: vordere Bremsscheiben deutlich heißer als hintige)."]
    dicts = advice_dicts(advice, lang="en")
    assert dicts[0]["field"] == "brake_bias"
    assert dicts[0]["target"] == 54
    assert "reason" in dicts[0]["text"]
    assert ADVICE_HEADER["de"].startswith("Empfohlene")


# ---------- CLI-Integration (Ende-zu-Ende mit setups.json) ----------

CSV = """[*Header]
[Channel]
"Time","sec"
"Speed","km/h"
"G_Lat","G"
"Steering_Angle","deg"
[Data]
""" + "\n".join(f"{i},{150 + i},{1.2},{16.0}" for i in range(30))


def test_cli_advice_appended_without_store(capsys, tmp_path):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    from r3e_coach.cli import main
    rc = main([str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Empfohlene nächste Schritte" in out
    assert "1) Stabi vorne eine Stufe weicher." in out


def test_cli_advice_uses_stored_values(capsys, tmp_path):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    store = tmp_path / "setups.json"
    data = load(store)
    key = entry_key("Sachsenring", None, "Audi R8")
    upsert_values(data, key, chassis={"arb_front": 4, "brake_bias": 56})
    save(data, store)
    rc = main(["analyze", str(f), "--store", str(store),
               "--track", "Sachsenring", "--vehicle", "Audi R8"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Stabi vorne: 4 → 3" in out
    assert "Bremsbalance: 56 % → 58 %" in out


def test_cli_advice_in_json_output(capsys, tmp_path):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    store = tmp_path / "setups.json"
    data = load(store)
    save(data, store)
    rc = main(["analyze", str(f), "--store", str(store),
               "--track", "Sachsenring", "--vehicle", "Audi R8", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert isinstance(payload["advice"], list) and payload["advice"]
    assert payload["advice"][0]["field"] == "arb_front"
    assert payload["findings"][0].get("data", {}) != {