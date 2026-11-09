import json

import pytest

from r3e_coach.cli import main, build_parser

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


def _write_csv(tmp_path):
    f = tmp_path / "log.csv"
    f.write_text(CSV, encoding="utf-8")
    return f


def test_cli_text_de(tmp_path, capsys):
    f = _write_csv(tmp_path)
    rc = main([str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "R3E Setup-Coach" in out
    assert "HOCH" in out
    assert "Untersteuern" in out


def test_cli_json_en(tmp_path, capsys):
    f = _write_csv(tmp_path)
    rc = main([str(f), "--json", "--lang", "en"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["language"] == "en"
    assert any(f["rule"] == "understeer" for f in payload["findings"])


def test_cli_save_requires_track_and_vehicle(tmp_path, capsys):
    f = _write_csv(tmp_path)
    store = tmp_path / "setups.json"
    rc = main(["analyze", str(f), "--save", "--store", str(store)])
    assert rc == 2
    assert "track" in capsys.readouterr().err.lower() or "--save" in capsys.readouterr().err
    assert not store.exists()


def test_cli_save_persists_analysis(tmp_path, capsys):
    f = _write_csv(tmp_path)
    store = tmp_path / "setups.json"
    rc = main(["analyze", str(f), "--save", "--store", str(store),
               "--track", "Sachsenring", "--vehicle", "Audi R8"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Gespeichert unter 'Sachsenring|Sachsenring|Audi R8'" in out
    data = json.loads(store.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    entry = data["setups"]["Sachsenring|Sachsenring|Audi R8"]
    assert entry["analyses"][0]["samples"] == 30
    findings = entry["analyses"][0]["findings"]
    assert findings and findings[0]["rule"]
    assert "Untersteuern" in json.dumps(findings, ensure_ascii=False)
    assert entry["analyses"][0]["applied"] is None
    assert entry["analyses"][0]["csv_source"].endswith("log.csv")


def test_cli_setups_list_and_detail(tmp_path, capsys):
    f = _write_csv(tmp_path)
    store = tmp_path / "setups.json"
    main(["analyze", str(f), "--save", "--store", str(store),
          "--track", "Sachsenring", "--vehicle", "Audi R8"])
    capsys.readouterr()
    rc = main(["setups", "--store", str(store)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Sachsenring|Sachsenring|Audi R8" in out
    assert "Gespeicherte Setups (1)" in out
    rc = main(["setups", "--store", str(store), "--key", "Sachsenring|Sachsenring|Audi R8"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Setup 'Sachsenring|Sachsenring|Audi R8'" in out
    assert "Analyse 1" in out
    assert "offen" in out


def test_cli_setups_key_not_found(tmp_path, capsys):
    store = tmp_path / "setups.json"
    rc = main(["setups", "--store", str(store), "--key", "X|X|Y"])
    assert rc == 2
    assert "Kein Eintrag" in capsys.readouterr().err


def test_cli_setups_empty_and_json(tmp_path, capsys):
    store = tmp_path / "setups.json"
    rc = main(["setups", "--store", str(store)])
    assert rc == 0
    assert "Noch keine Setups" in capsys.readouterr().out
    rc = main(["setups", "--store", str(store), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["setups"] == {}


def test_cli_setups_args_parse():
    args = build_parser().parse_args(
        ["setups", "--store", "x.json", "--key", "A|B|C", "--json"])
    assert args.command == "setups"
    assert args.key == "A|B|C"
    assert args.json is True
