"""Lesender Zugriff auf results.db von R3E-Resultate (R3E-Datenkonzept).

Eigentümer der Datenbank ist R3E-Resultate; der Setup-Coach liest NUR
(im SQLite-Modus mode=ro) und schreibt niemals hinein. Schlüssel und
Namen folgen der Konvention track|layout|vehicle (Namen unverändert aus
den RaceRoom-Ergebnisdaten, Zeiten in ms).
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_DIR = "RaceRoom Results Companion"
DB_NAME = "results.db"

# Nur echte Fahrer berücksichtigen (ai: -1 unbekannt, 0 echt, 1 KI).
_NOT_AI = "COALESCE(e.ai, -1) <> 1"


def default_db_path():
    base = Path.home() / "Documents"
    return str(base / DB_DIR / DB_NAME)


def db_exists(path=None):
    return os.path.isfile(path or default_db_path())


@contextmanager
def connect(path=None):
    """Öffnet results.db nur-lesend; yields None, wenn sie nicht existiert."""
    path = path or default_db_path()
    if not os.path.isfile(path):
        yield None
        return
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        yield conn
    finally:
        conn.close()


def _layout_filter(layout):
    """Layout-Filter: None = alle Layouts der Strecke."""
    if layout is None:
        return "1=1", []
    return "(COALESCE(NULLIF(s.layout, ''), s.track) = ?)", [layout]


def _base_conditions(track, layout, vehicle):
    sql = ["s.track = ?", "e.vehicle = ?", _NOT_AI]
    params = [track, vehicle]
    lf, lp = _layout_filter(layout)
    sql.append(lf)
    params.extend(lp)
    return " AND ".join(sql), params


def lap_stats(conn, track, layout=None, vehicle=None):
    """Best- und Ø-Zeiten (gültige Runden, echte Fahrer) je track|layout|vehicle.

    Rückgabe None ohne Datenbankverbindung, sonst dict mit best_ms (int|None),
    avg_ms (int|None), n_laps (int), n_sessions (int).
    """
    if conn is None:
        return None
    where, params = _base_conditions(track, layout, vehicle)
    row = conn.execute(
        "SELECT MIN(l.lap_time_ms), AVG(l.lap_time_ms), COUNT(*), "
        "COUNT(DISTINCT s.id) "
        "FROM laps l JOIN entries e ON l.entry_id = e.id "
        "JOIN sessions s ON e.session_id = s.id "
        f"WHERE {where} AND l.lap_time_ms > 0 AND COALESCE(l.valid, 1) <> 0",
        params).fetchone()
    best_ms, avg_ms, n_laps, n_sessions = row
    if best_ms is None:
        # Fallback: Bestzeit je Eintrag (keine RundenDetails vorhanden)
        row = conn.execute(
            "SELECT MIN(e.best_lap_ms), COUNT(DISTINCT s.id) "
            "FROM entries e JOIN sessions s ON e.session_id = s.id "
            f"WHERE {where} AND e.best_lap_ms > 0",
            params).fetchone()
        best_ms, n_sessions = row[0], (row[1] or 0)
    return {
        "best_ms": int(best_ms) if best_ms else None,
        "avg_ms": int(round(avg_ms)) if avg_ms else None,
        "n_laps": int(n_laps or 0),
        "n_sessions": int(n_sessions or 0),
    }


def combos(conn):
    """Alle bekannten Kombinationen track|layout|vehicle mit Bestzeit.

    Rückgabe Liste von dict(track, layout, vehicle, best_ms) — Bestzeit
    bevorzugt aus Runden, Fallback best_lap_ms.
    """
    if conn is None:
        return []
    rows = conn.execute(
        "SELECT s.track, COALESCE(NULLIF(s.layout, ''), s.track), e.vehicle, "
        "MIN(CASE WHEN l.lap_time_ms > 0 AND COALESCE(l.valid, 1) <> 0 "
        "    THEN l.lap_time_ms END), "
        "MIN(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) "
        "FROM sessions s JOIN entries e ON e.session_id = s.id "
        "LEFT JOIN laps l ON l.entry_id = e.id "
        f"WHERE {_NOT_AI} "
        "GROUP BY s.track, COALESCE(NULLIF(s.layout, ''), s.track), e.vehicle "
        "HAVING MIN(CASE WHEN l.lap_time_ms > 0 AND COALESCE(l.valid, 1) <> 0 "
        "    THEN l.lap_time_ms END) IS NOT NULL "
        "    OR MIN(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) IS NOT NULL"
    ).fetchall()
    out = []
    for track, layout, vehicle, best_laps, best_entry in rows:
        best = best_laps if best_laps else best_entry
        out.append({"track": track, "layout": layout, "vehicle": vehicle,
                    "best_ms": int(best) if best else None})
    out.sort(key=lambda c: (c["track"].lower(), c["vehicle"].lower()))
    return out