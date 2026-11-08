import os

from r3e_coach.parser import parse_motec_csv
from r3e_coach.rules import Ctx, analyze

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "r2m_motec_lap14.csv")


def test_real_r2m_motec_csv_parses():
    s = parse_motec_csv(FIXTURE)
    assert len(s) > 0
    for key in ("time", "speed", "throttle", "brake", "steer", "g_lat", "g_long",
                "tyre_temp_fl", "tyre_temp_fr", "tyre_temp_rl", "tyre_temp_rr",
                "brake_temp_fl", "susp_travel_fl"):
        assert s.has(key), key
    assert s.col("speed")[0] is not None


def test_real_r2m_motec_csv_analyzes():
    s = parse_motec_csv(FIXTURE)
    findings = analyze(s, Ctx())
    assert isinstance(findings, list)
