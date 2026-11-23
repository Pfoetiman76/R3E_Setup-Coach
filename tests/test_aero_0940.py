"""Regressionstests für 0.9.4.0: Aero-Balance aus der Telemetrie.

Marcels Frage "nur Reifen? Was ist mit Achse und Aero?": Fahrwerk/Stabi und
Fahrzeughöhe waren seit 0.7.0 berücksichtigt; Aero fehlte im priorisierten
"Empfohlene nächste Schritte"-Block. 0.9.4.0 vergleicht den Lenkaufwand
pro g Querbeschleunigung in Schnellkurven (>= 160 km/h) mit Langsamkurven
(<= 110 km/h) und leitet Flügel-Hinweise ab.
"""

from r3e_coach import rules, store
from r3e_coach.advice import build_advice
from r3e_coach.rules import Ctx, Finding, analyze
from r3e_coach.store import CHASSIS_FIELDS
from r3e_coach.telemetry import Session


def make_session(**cols):
    names = list(cols.keys())
    rows = [list(r) for r in zip(*cols.values())]
    return Session(names, [""] * len(names), rows)


def aero_cols(n_slow=20, n_fast=20, slow_steer=8.0, fast_steer=16.0,
              slow_speed=90.0, fast_speed=180.0, g=1.2, wiggle=False):
    cols = {
        "Time": [float(i) for i in range(n_slow + n_fast)],
        "Speed": [slow_speed] * n_slow + [fast_speed] * n_fast,
        "Throttle": [0.5] * (n_slow + n_fast),
        "Brake": [0.0] * (n_slow + n_fast),
        "Steering_Angle": [],
        "G_Lat": [g] * (n_slow + n_fast),
        "G_Long": [0.0] * (n_slow + n_fast),
        "Tyre Temp FL": [85.0] * (n_slow + n_fast),
        "Tyre Temp FR": [85.0] * (n_slow + n_fast),
        "Tyre Temp RL": [85.0] * (n_slow + n_fast),
        "Tyre Temp RR": [85.0] * (n_slow + n_fast),
        "Brake Temp FL": [300.0] * (n_slow + n_fast),
        "Brake Temp FR": [300.0] * (n_slow + n_fast),
        "Brake Temp RL": [300.0] * (n_slow + n_fast),
        "Brake Temp RR": [300.0] * (n_slow + n_fast),
        "Susp Travel FL": [20.0] * (n_slow + n_fast),
        "Susp Travel FR": [20.0] * (n_slow + n_fast),
        "Susp Travel RL": [20.0] * (n_slow + n_fast),
        "Susp Travel RR": [20.0] * (n_slow + n_fast),
        "Lap Time": [95.0] * (n_slow + n_fast),
    }
    steer = []
    for i in range(n_slow):
        steer.append(slow_steer)
    for i in range(n_fast):
        if wiggle:
            steer.append(fast_steer if i % 2 == 0 else -fast_steer)
        else:
            steer.append(fast_steer)
    cols["Steering_Angle"] = steer
    return cols


def test_balanced_car_has_no_aero_finding():
    s = make_session(**aero_cols(fast_steer=8.0))
    findings = analyze(s, Ctx())
    assert "aero_understeer" not in {f.rule for f in findings}
    assert "aero_oversteer" not in {f.rule for f in findings}


def test_fast_corner_heavy_steering_triggers_aero_understeer():
    s = make_session(**aero_cols(slow_steer=6.0, fast_steer=14.0))
    findings = analyze(s, Ctx())
    assert "aero_understeer" in {f.rule for f in findings}
    aero = [f for f in findings if f.rule == "aero_understeer"][0]
    assert aero.data["ratio"] > 1.4
    assert "Abtriebsbalance" in aero.text["de"]


def test_aero_understeer_advice_names_wing_steps_and_targets():
    finding = Finding("aero_understeer", "aero", "medium", {"de": "", "en": ""},
                      [], data={})
    advice = build_advice([finding], chassis={"wing_front": 6, "wing_rear": 4})
    fields = [a["field"] for a in advice if a["field"]]
    assert "wing_front" in fields and "wing_rear" in fields
    front = [a for a in advice if a["field"] == "wing_front"][0]
    assert front["current"] == 6 and front["target"] == 7
    rear = [a for a in advice if a["field"] == "wing_rear"][0]
    assert rear["current"] == 4 and rear["target"] == 3
    assert "Frontflügel" in front["text"]["de"]


def test_aero_oversteer_advice_recommends_rear_wing():
    finding = Finding("aero_oversteer", "aero", "medium", {"de": "", "en": ""},
                      [], data={})
    advice = build_advice([finding], chassis={"wing_rear": 3})
    rear = [a for a in advice if a["field"] == "wing_rear"][0]
    assert rear["current"] == 3 and rear["target"] == 4
    assert "Heckflügel" in rear["text"]["de"]


def test_wing_fields_in_chassis_schema():
    """setups.json kennt ab 0.9.4.0 wing_front/wing_rear."""
    assert "wing_front" in CHASSIS_FIELDS
    assert "wing_rear" in CHASSIS_FIELDS
    data = {"schema_version": 1, "setups": {}}
    entry = store.ensure_entry(data, "Hockenheim|GP|Audi")
    assert entry["chassis"]["wing_front"] is None
    assert entry["chassis"]["wing_rear"] is None


def test_too_few_fast_samples_no_aero_finding():
    """Unter der Mindeststichprobe (10 Samples je Band) wird nichts behauptet."""
    s = make_session(**aero_cols(n_fast=5, n_slow=20, fast_steer=20.0))
    findings = analyze(s, Ctx())
    assert "aero_understeer" not in {f.rule for f in findings}
