from r3e_coach.rules import Ctx, analyze
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


def rules_of(findings):
    return {f.rule for f in findings}


def test_clean_session_has_no_high_findings():
    s = make_session(**base())
    findings = analyze(s, Ctx())
    assert all(f.severity != "high" for f in findings)


def test_hot_front_tyres_trigger_balance_finding():
    cols = base()
    cols["Tyre Temp FL"] = [98.0] * 60
    cols["Tyre Temp FR"] = [98.0] * 60
    findings = analyze(make_session(**cols), Ctx())
    assert "tyre_temp_balance" in rules_of(findings)
    f = next(f for f in findings if f.rule == "tyre_temp_balance")
    assert f.severity == "high"
    assert "Vorderreifen" in f.text["de"]


def test_understeer_detected_by_high_steering_in_corners():
    cols = base()
    for i in range(60):
        cols["G_Lat"][i] = 1.2
        cols["Steering_Angle"][i] = 16.0
    findings = analyze(make_session(**cols), Ctx())
    assert "understeer" in rules_of(findings)


def test_oversteer_detected_by_corrections():
    cols = base()
    for i in range(60):
        cols["G_Lat"][i] = 1.2
        cols["Steering_Angle"][i] = 6.0 + (2.0 if i % 2 else -2.0)
    findings = analyze(make_session(**cols), Ctx())
    assert "oversteer" in rules_of(findings)


def test_front_heavy_brake_temps_trigger_balance_finding():
    cols = base()
    for i in range(60):
        cols["Brake"][i] = 0.8
    cols["Brake Temp FL"] = [520.0] * 60
    cols["Brake Temp FR"] = [520.0] * 60
    findings = analyze(make_session(**cols), Ctx())
    assert "brake_balance" in rules_of(findings)


def test_bottoming_detected_on_straights():
    cols = base()
    for i in range(60):
        cols["Throttle"][i] = 1.0
        cols["Susp Travel FL"][i] = 1.0
    findings = analyze(make_session(**cols), Ctx())
    assert "bottoming" in rules_of(findings)


def test_inconsistent_laps_trigger_low_finding():
    cols = base(n=200)
    pattern = [100.0, 103.0, 101.5, 100.5, 102.5]
    cols["Lap Time"] = [pattern[i % len(pattern)] for i in range(200)]
    findings = analyze(make_session(**cols), Ctx())
    assert "consistency" in rules_of(findings)


def test_missing_channels_are_skipped():
    s = make_session(Time=[0.0, 1.0], Speed=[100.0, 110.0])
    assert analyze(s, Ctx()) == []
