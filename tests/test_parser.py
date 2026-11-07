from r3e_coach.parser import parse_motec_csv

I2_SAMPLE = """[*Header]
Created=Test
[*SessionInfo]
Venue=Teststrecke
[Channel]
"Name","Units"
"Time","sec"
"Speed","km/h"
"G Lat","G"
"Steering_Angle","deg"
"Tyre Temp FL","degC"
"Tyre Temp FR","degC"
"Tyre Temp RL","degC"
"Tyre Temp RR","degC"
[Data]
0,0,0,0,70,70,70,70
1,120,1.0,5,90,90,80,80
2,150,1.2,8,95,95,82,82
"""


def test_parse_motec_sections(tmp_path):
    f = tmp_path / "log.csv"
    f.write_text(I2_SAMPLE, encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.has("time")
    assert s.has("speed")
    assert s.has("g_lat")
    assert s.has("steer")
    assert s.has("tyre_temp_fl")
    assert s.col("speed") == [0.0, 120.0, 150.0]
    assert s.units["speed"] == "km/h"
    assert s.source.endswith("log.csv")


def test_parse_plain_csv(tmp_path):
    f = tmp_path / "plain.csv"
    f.write_text("Time,Speed\n0,100\n1,120\n", encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.has("time")
    assert s.has("speed")
    assert s.col("speed") == [100.0, 120.0]


def test_non_numeric_cells_become_none(tmp_path):
    f = tmp_path / "gaps.csv"
    f.write_text("Time,Speed\n0,abc\n1,120\n", encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.col("speed") == [None, 120.0]
