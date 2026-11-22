"""Tests für logdata.py: .coachlog schreiben, lesen und in eine Session laden."""

import pytest

from r3e_coach.logdata import read_log, session_from_log, write_log
from r3e_coach.recorder import COLUMNS, UNITS


def _rows(n=5):
    return [[i * 0.02, 90.0 + i, 100.0 + i, 0.5, 0.2, 3.0, 0.4, -1.2,
             21.0, 21.0, 22.0, 22.0, 84.0, 84.0, 82.0, 82.0,
             1.8, 1.8, 1.8, 1.8, 300.0, 300.0, 290.0, 290.0]
            for i in range(n)]


def _write(tmp_path, name="log.coachlog", meta=None):
    f = tmp_path / name
    m = {"track": "Sachsenring", "layout": "Sachsenring", "vehicle": "Audi R8"}
    if meta:
        m.update(meta)
    write_log(f, m, list(COLUMNS), list(UNITS), _rows())
    return f


def test_write_and_read_roundtrip(tmp_path):
    f = _write(tmp_path)
    text = f.read_text(encoding="utf-8")
    assert text.startswith("[coachlog]")
    meta, columns, units, rows = read_log(f)
    assert meta["track"] == "Sachsenring"
    assert meta["vehicle"] == "Audi R8"
    assert columns[0] == "time" and len(columns) == len(COLUMNS)
    assert len(rows) == 5
    assert rows[1][2] == pytest.approx(101.0)
    # None-Zellen gehen leer raus und kommen als None zurück
    m2 = dict(meta)
    rows_none = [list(r) for r in _rows()]
    rows_none[0][16] = None
    write_log(f, m2, list(COLUMNS), list(UNITS), rows_none)
    _, _, _, rows2 = read_log(f)
    assert rows2[0][16] is None


def test_meta_auto_fields(tmp_path):
    f = _write(tmp_path)
    meta, _, _, _ = read_log(f)
    assert meta["recorded_at"]  # automatisch gesetzt
    assert meta["version"] == "1"


def test_session_from_log_resolves_channels(tmp_path):
    """Die normalisierten Spaltennamen müssen von telemetry.Session erkannt
    werden — sonst wäre die Recorder-Analyse-Kette broken."""
    f = _write(tmp_path)
    session = session_from_log(f)
    assert len(session) == 5
    for key in ("time", "speed", "steer", "g_lat", "g_long",
                "tyre_temp_fl", "tyre_press_fl"):
        assert session.has(key), f"Kanal fehlt: {key}"
    assert session.col("speed")[0] == pytest.approx(100.0)
    assert session.units.get("speed") == "km/h"


def test_read_log_rejects_files_without_columns(tmp_path):
    f = tmp_path / "broken.coachlog"
    f.write_text("[coachlog]\n[data]\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_log(f)


def test_read_log_missing_file(tmp_path):
    with pytest.raises(OSError):
        read_log(tmp_path / "gibt-es-nicht.coachlog")


def test_meta_values_survive_spaces(tmp_path):
    f = _write(tmp_path, meta={"track": "Nürburgring Sprint", "vehicle": "BMW M4 GT3"})
    meta, _, _, _ = read_log(f)
    assert meta["track"] == "Nürburgring Sprint"
    assert meta["vehicle"] == "BMW M4 GT3"
