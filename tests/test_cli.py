import json

import pytest

from r3e_coach.cli import main, build_parser
from r3e_coach.logdata import write_log
from r3e_coach.recorder import COLUMNS, UNITS


def _sample_rows(n=30):
    """30 Zeilen mit stetiger Kurvenfahrt: Untersteuern (steer 16 Grad, g_lat 1.2)."""
    rows = []
    for i in range(n):
        rows.append([
            i * 0.02,        # time
            95.0,            # lap_time
            150.0 + i,       # speed
            0.5,             # throttle
            0.0,             # brake
            16.0,            # steer
            1.2,             # g_lat
            0.0,             # g_long
            20.0, 20.0, 20.0, 20.0,          # susp_travel
            98.0, 98.0, 80.0, 80.0,          # tyre_temp (vorn heiß)
            None, None, None, None,          # tyre_press
            300.0, 300.0, 280.0, 280.0,      # brake_temp
        ])
    return rows


def _write_log(tmp_path, name="log.coachlog", rows=None, meta=None):
    m = {"track": "Sachsenring", "layout": "Sachsenring",
         "vehicle": "Audi R8", "session_type": "practice"}
    if meta:
        m.update(meta)
    f = tmp_path / name
    write_log(f, m, list(COLUMNS), list(UNITS), rows or _sample_rows())
    return f


def test_cli_text_de(tmp_path, capsys):
    f = _write_log(tmp_path)
    rc = main([str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "R3E Setup-Coach" in out
    assert "HOCH" in out
    assert "Untersteuern" in out


def test_cli_json_en(tmp_path, capsys):
    f = _write_log(tmp_path)
    rc = main([str(f), "--json", "--lang", "en"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["language"] == "en"
    assert any(f["rule"] == "understeer" for f in payload["findings"])


def test_cli_save_persists_analysis(tmp_path, capsys):
    f = _write_log(tmp_path)
    store = tmp_path / "setups.json"
    rc = main(["analyze", str(f), "--save", "--store", str(store)])
    out = capsys.readouterr().out
    assert rc == 0
    # track/layout/vehicle kommen automatisch aus dem Log-Meta
    assert "Gespeichert unter 'Sachsenring|Sachsenring|Audi R8'" in out
    data = json.loads(store.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    entry = data["setups"]["Sachsenring|Sachsenring|Audi R8"]
    assert entry["analyses"][0]["samples"] == 30
    findings = entry["analyses"][0]["findings"]
    assert findings and findings[0]["rule"]
    assert "Untersteuern" in json.dumps(findings, ensure_ascii=False)
    assert entry["analyses"][0]["applied"] is None
    assert entry["analyses"][0]["log_source"].endswith("log.coachlog")


def test_cli_save_overrides_meta_key(tmp_path, capsys):
    f = _write_log(tmp_path)
    store = tmp_path / "setups.json"
    rc = main(["analyze", str(f), "--save", "--store", str(store),
               "--track", "Nürburgring", "--layout", "Nürburgring",
               "--vehicle", "BMW M4"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Gespeichert unter 'Nürburgring|Nürburgring|BMW M4'" in out


def test_cli_setups_list_and_detail(tmp_path, capsys):
    f = _write_log(tmp_path)
    store = tmp_path / "setups.json"
    main(["analyze", str(f), "--save", "--store", str(store)])
    capsys.readouterr()
    rc = main(["setups", "--store", str(store)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Sachsenring|Sachsenring|Audi R8" in out
    rc = main(["setups", "--store", str(store), "--key", "Sachsenring|Sachsenring|Audi R8"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Zielzeit" in out


def test_cli_record_parser_flags():
    args = build_parser().parse_args(
        ["record", "--hz", "25", "--out", "C:/rec", "--wait"])
    assert args.command == "record"
    assert args.hz == 25.0
    assert args.out == "C:/rec"
    assert args.wait is True


def test_cli_setups_parser_flags():
    args = build_parser().parse_args(
        ["setups", "--store", "x.json", "--key", "A|B|C", "--json"])
    assert args.command == "setups"
    assert args.key == "A|B|C"
    assert args.json is True


def test_cli_bridge_command_removed():
    """0.8.0: bridge/parser sind endgültig entfernt — auch auf CLI-Ebene."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(["bridge"])
