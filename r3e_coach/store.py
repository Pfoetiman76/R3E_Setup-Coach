"""Eigentümer von setups.json (R3E-Datenkonzept).

Qt-frei. Alle Zugriffe auf setups.json laufen über dieses Modul:
- atomar schreiben (Suffix .tmp + os.replace)
- schema_version führen, unbekannte Felder ignorieren
- korrupte Dateien toleriert laden (leere Struktur statt Absturz)
- Primärschlüssel: "track|layout|vehicle"
"""

import json
import os
import sys
from datetime import datetime

SCHEMA_VERSION = 1

CHASSIS_FIELDS = (
    "arb_front",
    "arb_rear",
    "ride_height_front",
    "ride_height_rear",
    "camber_front",
    "camber_rear",
    "toe_front",
    "toe_rear",
    "brake_bias",
    "steering_lock",
)

TIRE_FIELDS = (
    "pressure_front",
    "pressure_rear",
)

ENTRY_TEXT_FIELDS = (
    "notes",
    "reference_session",
)

STORE_FILENAME = "setups.json"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def app_dir():
    """Anwendungsordner: neben der Exe (eingefroren) bzw. Repo-Wurzel (Quelle)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_store_path():
    return os.path.join(app_dir(), STORE_FILENAME)


def entry_key(track, layout=None, vehicle=None):
    """Primärschlüssel 'track|layout|vehicle'.

    Fehlt das Layout, wird der Streckenname eingesetzt (RaceRoom nennt das
    Standard-Layout wie die Strecke selbst). Namen werden unverändert
    übernommen — keine eigenen Schreibvarianten, damit die Schlüssel über
    alle Apps matchen.
    """
    track = str(track or "").strip()
    layout = str(layout or "").strip() or track
    vehicle = str(vehicle or "").strip()
    if not track or not vehicle:
        raise ValueError("track und vehicle sind für den Setupschlüssel erforderlich")
    return f"{track}|{layout}|{vehicle}"


def empty_data():
    return {"schema_version": SCHEMA_VERSION, "setups": {}}


def load(path=None):
    """setups.json laden — toleriert fehlende und korrupte Dateien."""
    path = os.fspath(path or default_store_path())
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return empty_data()
    if not isinstance(data, dict):
        return empty_data()
    setups = data.get("setups")
    if not isinstance(setups, dict):
        setups = {}
    out = empty_data()
    # schema_version: vorhandene akzeptieren, unbekannte Felder ignorieren
    out["schema_version"] = data.get("schema_version", SCHEMA_VERSION)
    for key, entry in setups.items():
        if isinstance(key, str) and isinstance(entry, dict):
            out["setups"][key] = entry
    return out


def save(data, path=None):
    """Atomar schreiben: Datei mit Suffix .tmp, dann os.replace."""
    path = os.fspath(path or default_store_path())
    out = dict(data)
    out["schema_version"] = data.get("schema_version", SCHEMA_VERSION)
    out["setups"] = data.get("setups", {})
    tmp = path + ".tmp"
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def get_entry(data, key):
    entry = data["setups"].get(key)
    return entry if isinstance(entry, dict) else None


def ensure_entry(data, key):
    """Eintrag anlegen, falls fehlend — mit Nullwerten und leeren Listen."""
    entry = get_entry(data, key)
    if entry is None:
        entry = {
            "updated_at": None,
            "target_lap_ms": None,
            "reference_session": None,
            "notes": "",
            "chassis": {f: None for f in CHASSIS_FIELDS},
            "tires": {f: None for f in TIRE_FIELDS},
            "analyses": [],
            "history": [],
        }
        data["setups"][key] = entry
    entry.setdefault("chassis", {})
    entry.setdefault("tires", {})
    entry.setdefault("analyses", [])
    entry.setdefault("history", [])
    for f in CHASSIS_FIELDS:
        entry["chassis"].setdefault(f, None)
    for f in TIRE_FIELDS:
        entry["tires"].setdefault(f, None)
    return entry


def _touch(entry):
    entry["updated_at"] = now_iso()


def upsert_values(data, key, chassis=None, tires=None, **fields):
    """Setup-Werte, Zielzeit, Notizen oder Bezugs-Session aktualisieren."""
    entry = ensure_entry(data, key)
    if chassis:
        for f in CHASSIS_FIELDS:
            if f in chassis:
                entry["chassis"][f] = chassis[f]
    if tires:
        for f in TIRE_FIELDS:
            if f in tires:
                entry["tires"][f] = tires[f]
    for f in ENTRY_TEXT_FIELDS + ("target_lap_ms",):
        if f in fields and fields[f] is not None:
            entry[f] = fields[f]
    _touch(entry)
    return entry


def add_analysis(data, key, analysis):
    """Analyseergebnis (Fundstellen im report.py-JSON-Format) speichern.

    Neue Analysen werden vorne eingefügt (neueste zuerst).
    """
    entry = ensure_entry(data, key)
    record = dict(analysis)
    record.setdefault("analyzed_at", now_iso())
    record.setdefault("applied", None)
    entry["analyses"].insert(0, record)
    _touch(entry)
    return record


def add_history(data, key, change, observed=None):
    """Änderung mit kurzer Beobachtung protokollieren — neue Einträge zuerst."""
    entry = ensure_entry(data, key)
    record = {"changed_at": now_iso(), "change": str(change), "observed": observed}
    entry["history"].insert(0, record)
    return record


def list_keys(data):
    return sorted(data.get("setups", {}).keys())
