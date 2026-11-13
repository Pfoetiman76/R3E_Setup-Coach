import os
import sqlite3

import pytest

from r3e_coach import queries

SCHEMA = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest TEXT UNIQUE NOT NULL,
    session_type TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    track TEXT DEFAULT '',
    layout TEXT DEFAULT '',
    source_file TEXT DEFAULT ''
);
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    vehicle TEXT DEFAULT '',
    laps INTEGER DEFAULT 0,
    best_lap_ms INTEGER DEFAULT 0,
    car_id INTEGER DEFAULT 0,
    ai INTEGER DEFAULT -1
);
CREATE TABLE laps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    lap_no INTEGER DEFAULT 0,
    lap_time_ms INTEGER DEFAULT 0,
    valid INTEGER DEFAULT 1
);
"""


def _make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO sessions (digest, track, layout) VALUES ('d1', 'Sachsenring', 'Sachsenring')")
    conn.execute("INSERT INTO sessions (digest, track, layout) VALUES ('d2', 'Sachsenring', 'Sachsenring')")
    # echte Fahrer
    conn.execute("INSERT INTO entries (session_id, vehicle, best_lap_ms, ai) VALUES (1, 'Audi R8', 90000, 0)")
    conn.execute("INSERT INTO entries (session_id, vehicle, best_lap_ms, ai) VALUES (2, 'Audi R8', 91000, 0)")
    # KI-Fahrer: darf NICHT zaehlen
    conn.execute("INSERT INTO entries (session_id, vehicle, best_lap_ms, ai) VALUES (1, 'Audi R8', 60000, 1)")
    conn.execute("INSERT INTO laps (entry_id, lap_no, lap_time_ms) VALUES (1, 1, 95000)")
    conn.execute("INSERT INTO laps (entry_id, lap_no, lap_time_ms) VALUES (1, 2, 85000)")
    conn.execute("INSERT INTO laps (entry_id, lap_no, lap_time_ms) VALUES (2, 1, 88000)")
    # ungueltige Runde: darf nicht zaehlen
    conn.execute("INSERT INTO laps (entry_id, lap_no, lap_time_ms, valid) VALUES (2, 2, 80000, 0)")
    conn.commit()
    conn.close()


def test_lap_stats_best_and_avg(tmp_path):
    db = tmp_path / "results.db"
    _make_db(str(db))
    with queries.connect(str(db)) as conn:
        stats = queries.lap_stats(conn, "Sachsenring", "Sachsenring", "Audi R8")
    assert stats["best_ms"] == 85000
    assert stats["avg_ms"] == round((95000 + 85000 + 88000) / 3)
    assert stats["n_laps"] == 3
    assert stats["n_sessions"] == 2


def test_lap_stats_layout_none_matches_all_layouts(tmp_path):
    db = tmp_path / "results.db"
    _make_db(str(db))
    with queries.connect(str(db)) as conn:
        stats = queries.lap_stats(conn, "Sachsenring", None, "Audi R8")
    assert stats["best_ms"] == 85000


def test_lap_stats_ignores_ai(tmp_path):
    db = tmp_path / "results.db"
    _make_db(str(db))
    with queries.connect(str(db)) as conn:
        stats = queries.lap_stats(conn, "Sachsenring", "Sachsenring", "Audi R8")
    assert stats["best_ms"] != 60000


def test_lap_stats_empty_layout_falls_back_to_track(tmp_path):
    db = tmp_path / "results.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO sessions (digest, track, layout) VALUES ('d9', 'Norisring', '')")
    conn.execute("INSERT INTO entries (session_id, vehicle, best_lap_ms, ai) VALUES (1, 'BMW M4', 70000, 0)")
    conn.commit()
    conn.close()
    with queries.connect(str(db)) as conn:
        stats = queries.lap_stats(conn, "Norisring", "Norisring", "BMW M4")
    assert stats["best_ms"] == 70000


def test_combos_lists_known_keys(tmp_path):
    db = tmp_path / "results.db"
    _make_db(str(db))
    with queries.connect(str(db)) as conn:
        rows = queries.combos(conn)
    keys = [(c["track"], c["layout"], c["vehicle"]) for c in rows]
    assert ("Sachsenring", "Sachsenring", "Audi R8") in keys
    bests = {c["vehicle"]: c["best_ms"] for c in rows}
    assert bests["Audi R8"] == 85000  # Runden schlagen best_lap_ms


def test_connect_missing_db_yields_none(tmp_path):
    with queries.connect(str(tmp_path / "gibtsnicht.db")) as conn:
        assert conn is None
        assert queries.lap_stats(conn, "X", "X", "Y") is None
        assert queries.combos(conn) == []


def test_connect_is_read_only(tmp_path):
    db = tmp_path / "results.db"
    _make_db(str(db))
    with queries.connect(str(db)) as conn:
        try:
            conn.execute("CREATE TABLE sollte_nicht_gehen (x)")
        except sqlite3.OperationalError:
            pass
        else:
            pytest.fail("results.db muss read-only geöffnet werden")