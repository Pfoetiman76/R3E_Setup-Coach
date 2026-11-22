"""0.8.0: Eigenes Logformat des Setup-Coach (.coachlog) — lesbar und
schreibbar ohne externe Software (MoTeC i2 wird nicht mehr gebraucht).

Aufbau (Text, UTF-8):

    [coachlog]
    version=1
    track=Sachsenring
    layout=Sachsenring
    vehicle=Audi R8 LMS
    recorded_at=2026-11-22T09:00:00
    columns=time|lap_time|speed|throttle|...
    units=s|s|km/h|...
    [data]
    time,lap_time,speed,throttle,...
    0.020,95.0,142.8,0.42,...

Die Spaltennamen in 'columns' sind die intern normalisierten Kanalnamen
(time, speed, throttle, brake, steer, g_lat, g_long, tyre_temp_fl, ...),
die telemetry.Session direkt über das bestehende Kanal-Mapping einliest.
"""

import os
from datetime import datetime

MAGIC = "[coachlog]"
FORMAT_VERSION = 1


def _clean(value):
    return str(value if value is not None else "").replace("\n", " ").replace("\r", " ").strip()


def _float_text(v):
    if v is None:
        return ""
    return f"{v:.4f}"


def write_log(path, meta, columns, units, rows):
    """Schreibt eine .coachlog-Datei.

    meta: dict (u. a. track, layout, vehicle, recorded_at)
    columns: Liste normalisierter Kanalnamen
    units:   Liste gleicher Länge (Anzeige-Einheiten)
    rows:     Liste von Zeilen; jede Zeile eine Liste mit Zahlen/None
    """
    assert len(columns) == len(units), "columns/units muessen gleich lang sein"
    lines = [MAGIC]
    m = dict(meta or {})
    m.setdefault("version", FORMAT_VERSION)
    if not m.get("recorded_at"):
        m["recorded_at"] = datetime.now().isoformat(timespec="seconds")
    for key, value in m.items():
        if value is None:
            continue
        lines.append(f"{key}={_clean(value)}")
    lines.append("columns=" + "|".join(_clean(c) for c in columns))
    lines.append("units=" + "|".join(_clean(u) for u in units))
    lines.append("[data]")
    lines.append(",".join(_clean(c) for c in columns))
    for row in rows:
        lines.append(",".join(_float_text(row[i]) for i in range(len(columns))))
    path = os.fspath(path)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    return path


def _is_number(text):
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False


def read_log(path):
    """Liest eine .coachlog-Datei: (meta, columns, units, rows).

    meta enthält die Kopfdaten als Strings; jede Datenzeile wird als
    Float-Liste gelesen (leere Zelle -> None).
    """
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        raw = fh.read()
    meta = {}
    columns = []
    units = []
    rows = []
    section = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == MAGIC:
            section = "meta"
            continue
        if line == "[data]":
            section = "data"
            continue
        if section == "meta" and "=" in line:
            key, _, value = line.partition("=")
            meta[key.strip().lower()] = value
        elif section == "data":
            cells = [c.strip() for c in line.split(",")]
            if cells and cells[0] and _is_number(cells[0]):
                rows.append([float(c) if c else None for c in cells])
    if "|" in meta.get("columns", ""):
        columns = meta["columns"].split("|")
    if "|" in meta.get("units", ""):
        units = meta["units"].split("|")
    if not columns:
        raise ValueError(f"Keine Spaltendefinition in {path}")
    if not units or len(units) != len(columns):
        units = [""] * len(columns)
    return meta, columns, units, rows


def session_from_log(path):
    """Liest eine Logdatei und liefert direkt eine telemetry.Session.

    Die Spaltennamen der Coach-Logs sind bereits normalisiert; das
    bestehende Kanal-Mapping (channels.resolve) ordnet sie zuverlässig zu.
    """
    from .telemetry import Session

    meta, columns, units, rows = read_log(path)
    return Session(columns, units, rows, source=os.fspath(path))
