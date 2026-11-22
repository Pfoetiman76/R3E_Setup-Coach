"""Konfigurationsdatei des Coaches laden und speichern.

Historie: Diese Logik stammte aus bridge.py (R2M-Bridge, entfernt in 0.8.0).
Übrig bleibt das reine Konfigurations-Handling — die Datei .r3e-coach.json
im Installations- bzw. Benutzerordner.
"""

import json
import os
import sys
from pathlib import Path

DEFAULT_CONFIG_NAME = ".r3e-coach.json"


def _search_paths():
    """Kandidaten-Ordner für die Konfigurationsdatei (in Prioritätsordnung)."""
    paths = []
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent)
    paths.append(Path.home())
    paths.append(Path(__file__).resolve().parent)
    return paths


def find_config():
    """Liefert den Pfad der ersten existierenden Konfigurationsdatei (oder None)."""
    for base in _search_paths():
        cand = base / DEFAULT_CONFIG_NAME
        if cand.is_file():
            return cand
    return None


def default_config_path():
    """Pfad, an dem eine neue Konfiguration angelegt wird."""
    if getattr(sys, "frozen", False):
        # Exe-Ordner (auch bei Startmenü-Start): 0.6.4-Verhalten beibehalten.
        exe_dir = Path(sys.executable).resolve().parent
        if os.access(exe_dir, os.W_OK):
            return exe_dir / DEFAULT_CONFIG_NAME
    return Path.home() / DEFAULT_CONFIG_NAME


def load_config(path):
    """Lädt die Konfiguration; Rückgabe: dict."""
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        data = raw if isinstance(raw, dict) else {}
    except FileNotFoundError:
        data = {}
    except (json.JSONDecodeError, OSError):
        data = {}
    return data


def save_config(path, data):
    """Speichert die Konfiguration als JSON (atomic write)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_gui_config(path=None):
    """Konfiguration für die GUI: (config-dict, gelesener Pfad)."""
    if path is None:
        path = find_config()
    if path is None:
        return {}, default_config_path()
    return load_config(path), path
