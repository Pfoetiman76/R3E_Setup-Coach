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


def test_semicolon_delimited_csv(tmp_path):
    f = tmp_path / "r2m.csv"
    f.write_text("Time;Speed;Tyre Temp FL;Tyre Temp FR;Tyre Temp RL;Tyre Temp RR\n0;150;90;90;80;80\n1;160;91;91;81;81\n",
                 encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.has("speed")
    assert s.has("tyre_temp_fl")
    assert s.col("speed") == [150.0, 160.0]
    assert len(s) == 2


def test_utf16_encoded_csv(tmp_path):
    f = tmp_path / "motec_utf16.csv"
    f.write_bytes("Time,Speed\n0,100\n1,120\n".encode("utf-16"))
    s = parse_motec_csv(str(f))
    assert s.has("speed")
    assert s.col("speed") == [100.0, 120.0]


def test_header_plus_units_row(tmp_path):
    f = tmp_path / "units.csv"
    f.write_text('"Time","Speed"\n"sec","km/h"\n0,100\n1,120\n', encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.has("speed")
    assert s.col("speed") == [100.0, 120.0]
    assert s.units["speed"] == "km/h"


def test_unknown_data_section_used_as_fallback(tmp_path):
    f = tmp_path / "odd.csv"
    f.write_text('[Channel]\n"Time","sec"\n"Speed","km/h"\n[DataLogged]\n0,100\n1,120\n', encoding="utf-8")
    s = parse_motec_csv(str(f))
    assert s.has("speed")
    assert len(s) == 2
