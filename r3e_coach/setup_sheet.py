"""0.9.0: Setup-Zettel — druckfertige Garage-Anleitung aus den Empfehlungen.

Der Setup-Zettel ist die verlässliche Alternative zum Schreiben von
SVM-Dateien (deren Binärformat undokumentiert ist): Der Coach erzeugt
eine bedienungsfreundliche Checkliste je Fahrzeug und Strecke mit den
Klickwegen für die Garage, zum Ausdrucken oder Abrufen am PC.

Qt-frei, reine Python-Standardbibliothek — dieselben Regeln wie
advice/report/store (R3E-Datenkonzept).
"""

import os
import re

from .advice import ADVICE_HEADER, NO_ADVICE
from .store import app_dir, now_iso

LABELS = {
    "de": {
        "title": "R3E Setup-Coach — Setup-Zettel",
        "vehicle": "Fahrzeug",
        "track": "Strecke",
        "layout": "Layout",
        "created": "Erstellt",
        "source": "Aufzeichnung",
        "steps_header": "Einstellungen in der Garage (der Reihe nach, oben zuerst testen):",
        "note": ("Hinweis: Werte beziehen sich auf die Anzeige der Garage im Spiel. "
                 "Nach jeder Änderung mindestens drei Runden fahren und den Effekt "
                 "an der Telemetrie prüfen."),
        "key_label": "Setup-Eintrag",
    },
    "en": {
        "title": "R3E Setup Coach — Setup Sheet",
        "vehicle": "Vehicle",
        "track": "Track",
        "layout": "Layout",
        "created": "Created",
        "source": "Recording",
        "steps_header": "Garage settings (in order, test the top one first):",
        "note": ("Note: values refer to the garage display in the game. "
                 "After each change drive at least three laps and check the "
                 "effect in the telemetry."),
        "key_label": "Setup entry",
    },
}

_CHECKBOX = "[ ] "
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _clean(value, fallback="?"):
    text = (value or "").strip() or fallback
    return _SAFE.sub("_", text)


def suggest_filename(meta, lang="de", created=None):
    """Dateiname-Vorschlag: <strecke>_<layout>_<fahrzeug>_setup-zettel.txt."""
    track = _clean(meta.get("track"), "strecke" if lang == "de" else "track")
    layout = _clean(meta.get("layout"))
    vehicle = _clean(meta.get("vehicle"), "fahrzeug" if lang == "de" else "vehicle")
    if layout and layout != track:
        return f"{track}_{layout}_{vehicle}_setup-zettel.txt"
    return f"{track}_{vehicle}_setup-zettel.txt"


def default_sheets_dir():
    """Standardordner für Zettel: <Anwendungsordner>\\sheets."""
    return os.path.join(app_dir(), "sheets")


def build_sheet(meta, advice, lang="de", key=None, log_source=None,
                created=None, check_boxes=True):
    """Aufbau des Setup-Zettels als Text.

    meta: dict mit track/layout/vehicle.
    advice: Ergebnis von build_advice (Liste von Empfehlungs-Dicts mit
    mehrsprachigem "text"). key/log_source optional für die Kopfzeile.
    """
    t = LABELS.get(lang, LABELS["de"])
    created = created or now_iso()
    lines = [t["title"], "=" * len(t["title"])]
    lines.append(f"{t['vehicle']}: {meta.get('vehicle') or '?'}")
    layout = meta.get("layout")
    if layout and layout != meta.get("track"):
        lines.append(f"{t['track']}: {meta.get('track') or '?'} ({layout})")
    else:
        lines.append(f"{t['track']}: {meta.get('track') or '?'}")
    if log_source:
        lines.append(f"{t['source']}: {log_source}")
    if key:
        lines.append(f"{t['key_label']}: {key}")
    lines.append(f"{t['created']}: {created}")
    lines.append("")
    steps = list(advice or [])
    if steps:
        lines.append(ADVICE_HEADER.get(lang, ADVICE_HEADER["de"]))
        lines.append("")
        prefix = _CHECKBOX if check_boxes else ""
        for item in steps:
            text = (item.get("text") or {}).get(lang) if isinstance(item, dict) else None
            if not text:
                continue
            lines.append(f"{prefix}{text}")
    else:
        lines.append(NO_ADVICE.get(lang, NO_ADVICE["de"]))
    lines.append("")
    lines.append(t["note"])
    return "\n".join(lines).rstrip() + "\n"


def write_sheet(path, text):
    """Zettel atomar schreiben (.tmp + os.replace, Muster wie save_config)."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    os.replace(tmp, path)
    return path
