import json

from r3e_coach.cli import main

CSV = """[*Header]
[Channel]
"Time","sec"
"Speed","km/h"
"G_Lat","G"
"Steering_Angle","deg"
"Tyre Temp FL","degC"
"Tyre Temp FR","degC"
"Tyre Temp RL","degC"
"Tyre Temp RR","degC"
[Data]
""" + "\n".join(
    f"{i},{150 + i},{1.2},{16.0},{98.0},{98.0},{80.0},{80.0}" for i in range(30)
)


def test_cli_text_de(tmp_path, capsys):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    rc = main([str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "R3E Setup-Coach" in out
    assert "HOCH" in out
    assert "Untersteuern" in out


def test_cli_json_en(tmp_path, capsys):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    rc = main([str(f), "--json", "--lang", "en"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["language"] == "en"
    assert any(f["rule"] == "understeer" for f in payload["findings"])
