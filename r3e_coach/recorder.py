"""0.8.0: Eigener Telemetrie-Rekorder für RaceRoom — ersetzt R2M.

Liest die R3E-Shared-Memory-Schnittstelle ($R3E) im eigenen Takt,
erkennt automatisch Strecke/Layout/Fahrzeug und trennt die Aufzeichnung
bei Sessionwechsel oder Rückkehr ins Menü in eigene Dateien (.coachlog).
Pause und Boxenaufenthalt werden nicht mitgeschrieben (wie gewohnt).

Der Rekorder ist Qt-frei und damit identisch in CLI und GUI einsetzbar;
die GUI bettet ihn in einen Python-Thread ein und liest nur Statusfelder.
"""

import os
import threading
import time
from datetime import datetime

from .logdata import write_log
from .r3e_shared import TIRE_FR, TIRE_FL, TIRE_RL, TIRE_RR, R3EMemory

STATE_STOPPED = "stopped"
STATE_WAITING = "waiting"          # RaceRoom läuft nicht / nicht gefunden
STATE_MENUS = "menus"              # Spiel läuft, Spieler im Menü/nicht auf track
STATE_PAUSED = "paused"            # Spiel pausiert
STATE_PIT = "pit"                  # Spieler in der Boxengasse
STATE_RECORDING = "recording"      # Aufzeichnung läuft

DIAG_FILENAME = "coach-diagnose.txt"  # 0.9.2: Diagnose-Protokoll im Zielordner

COLUMNS = (
    "time", "lap_time", "speed", "throttle", "brake", "steer", "g_lat", "g_long",
    "susp_travel_fl", "susp_travel_fr", "susp_travel_rl", "susp_travel_rr",
    "tyre_temp_fl", "tyre_temp_fr", "tyre_temp_rl", "tyre_temp_rr",
    "tyre_press_fl", "tyre_press_fr", "tyre_press_rl", "tyre_press_rr",
    "brake_temp_fl", "brake_temp_fr", "brake_temp_rl", "brake_temp_rr",
)
UNITS = (
    "s", "s", "km/h", "0-1", "0-1", "deg", "g", "g",
    "mm", "mm", "mm", "mm",
    "C", "C", "C", "C",
    "bar", "bar", "bar", "bar",
    "C", "C", "C", "C",
)


def default_recordings_dir():
    base = os.path.expanduser("~")
    home = os.path.join(base, "Documents", "R3E Setup-Coach", "recordings")
    return home


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _safe(name):
    keep = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    cleaned = "".join(c for c in str(name) if c in keep).strip().replace(" ", "_")
    return cleaned[:48] or "unknown"


def sample_from_frame(frame):
    """Extrahiert eine Datenzeile (Reihenfolge = COLUMNS) aus einem Frame."""
    return [
        None,  # time wird vom Recorder absolut ergänzt
        frame.lap_time,
        frame.speed_kmh,
        frame.throttle if frame.throttle >= 0 else None,
        frame.brake if frame.brake >= 0 else None,
        frame.steer_deg,
        frame.g_lat,
        frame.g_long,
        frame.susp_travel[TIRE_FL], frame.susp_travel[TIRE_FR],
        frame.susp_travel[TIRE_RL], frame.susp_travel[TIRE_RR],
        frame.tyre_temp[TIRE_FL], frame.tyre_temp[TIRE_FR],
        frame.tyre_temp[TIRE_RL], frame.tyre_temp[TIRE_RR],
        frame.tyre_press[TIRE_FL], frame.tyre_press[TIRE_FR],
        frame.tyre_press[TIRE_RL], frame.tyre_press[TIRE_RR],
        frame.brake_temp[TIRE_FL], frame.brake_temp[TIRE_FR],
        frame.brake_temp[TIRE_RL], frame.brake_temp[TIRE_RR],
    ]


class Recorder:
    """Pollt Shared Memory und schreibt Sitzungs-Logs.

    open_memory:callable — liefert pro Aufruf ein R3EMemory-Objekt
    (Produktion: R3EMemory; Tests: injizierter Puffer).
    """

    def __init__(self, out_dir=None, hz=50.0, open_memory=None, sleep=None):
        self.out_dir = out_dir or default_recordings_dir()
        self.hz = float(hz)
        self._open_memory = open_memory or R3EMemory
        self._sleep = sleep or time.sleep
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.memory = None
        self.state = STATE_STOPPED
        # 0.9.2: Diagnose-Protokoll (coach-diagnose.txt im Zielordner) —
        # rekonstruiert Ablaeufe, die im VR-Headset unsichtbar bleiben.
        self.diag_fh = None
        self._shm_fail_logged = False
        self.samples = 0
        self.current_file = None
        self.files = []
        self.last_meta = {}
        self.error = None
        self.warning = None
        self.version = None
        self._rows = []
        self._session_key = None
        self._t0 = None

    # ---------- Status für GUI/CLI ----------

    def status(self):
        with self._lock:
            return {
                "state": self.state,
                "samples": self.samples,
                "file": self.current_file,
                "files": list(self.files),
                "meta": dict(self.last_meta),
                "error": self.error,
                "warning": self.warning,
            }

    def stop(self):
        self._stop_event.set()

    # ---------- Aufzeichnung ----------

    def _diagnose(self, event):
        """0.9.2: Ereignis mit Uhrzeit in coach-diagnose.txt (Fehler still)."""
        try:
            if self.diag_fh is None:
                os.makedirs(self.out_dir, exist_ok=True)
                self.diag_fh = open(os.path.join(self.out_dir, DIAG_FILENAME),
                                    "a", encoding="utf-8")
            self.diag_fh.write(
                f"{datetime.now().isoformat(timespec='seconds')} {event}\n")
            self.diag_fh.flush()
        except Exception:
            pass

    def _set_state(self, state):
        with self._lock:
            if state == self.state:
                return
            prev, self.state = self.state, state
        self._diagnose(f"ZUSTAND {prev} -> {state}")

    def _flush(self):
        """Schreibt die gesammelten Zeilen in die aktuelle Datei."""
        with self._lock:
            rows = self._rows
            meta = dict(self.last_meta)
            path = self.current_file
            self._rows = []
            self._session_key = None
            self.current_file = None
        if path and rows:
            write_log(path, meta, list(COLUMNS), list(UNITS), rows)
            self._diagnose(f"DATEI GESCHRIEBEN {os.path.basename(path)} ({len(rows)} Samples)")
            with self._lock:
                self.files.append(path)

    def _new_session(self, frame):
        track = frame.track or "unknown"
        layout = frame.layout or track
        vehicle = frame.vehicle or "unknown"
        fname = f"{_safe(track)}_{_safe(vehicle)}_{_stamp()}.coachlog"
        path = os.path.join(self.out_dir, fname)
        with self._lock:
            self.current_file = path
            self.last_meta = {
                "track": frame.track or "",
                "layout": frame.layout or "",
                "vehicle": frame.vehicle or "",
                "session_type": str(frame.session_type),
                "hz": f"{self.hz:g}",
            }
            self._session_key = (track, layout, vehicle, frame.session_type)
            self._rows = []
            self._t0 = None  # Zeitachse pro Sitzung neu starten
        self._diagnose(f"SITZUNG NEU — {fname}")
        return path

    def run(self):
        """Blockierende Schleife (im eigenen Thread ausführen)."""
        dt = 1.0 / max(1.0, self.hz)
        next_t = time.monotonic()
        self._diagnose(f"AUFZEICHNUNG GESTARTET ({self.hz:g} Hz, Zielordner {self.out_dir})")
        try:
            while not self._stop_event.is_set():
                frame = self._read()
                self._handle(frame)
                next_t += dt
                delay = next_t - time.monotonic()
                if delay > 0:
                    self._sleep(delay)
                else:
                    next_t = time.monotonic()
        finally:
            self._flush()
            if self.memory is not None:
                self.memory.close()
                self.memory = None
            self._set_state(STATE_STOPPED)
            try:
                self._diagnose("AUFZEICHNUNG BEENDET")
                if self.diag_fh is not None:
                    self.diag_fh.close()
                    self.diag_fh = None
            except Exception:
                pass

    def _read(self):
        """Liefert den nächsten Frame; öffnet den Shared Memory bei Bedarf."""
        if self.memory is None:
            try:
                self.memory = self._open_memory()
                self._shm_fail_logged = False
                self._diagnose("SHM GEÖFFNET — RaceRoom-Schnittstelle gefunden")
            except FileNotFoundError:
                # 0.9.1: Spiel läuft schlicht nicht — normales Warten statt
                # irreführender "Fehler"-Meldung in der Statusleiste.
                if not self._shm_fail_logged:
                    self._diagnose("SHM NICHT GEFUNDEN — warte auf RaceRoom")
                    self._shm_fail_logged = True
                self._set_state(STATE_WAITING)
                self._sleep(0.5)
                return None
            except OSError as exc:
                if not self._shm_fail_logged:
                    self._diagnose(f"SHM FEHLER — {exc}")
                    self._shm_fail_logged = True
                self.error = str(exc)
                self._set_state(STATE_WAITING)
                self._sleep(0.5)
                return None
        try:
            return self.memory.read_frame()
        except (OSError, ValueError) as exc:
            self.error = str(exc)
            try:
                self.memory.close()
            except Exception:
                pass
            self.memory = None
            self._set_state(STATE_WAITING)
            self._sleep(0.5)
            return None

    def _handle(self, frame):
        if frame is None:
            return
        if not frame.running:
            self._flush()
            self._set_state(STATE_WAITING)
            return
        if frame.version and frame.version[0] == 3 and frame.version[1] > 6:
            self.warning = (f"R3E-Schnittstelle {frame.version[0]}.{frame.version[1]} ist"
                            "neuer als die unterstützte Version 3.6 — Kanäle ggf. unvollständig.")
        if frame.in_menus or frame.paused:
            # Menü/Pause: aktuelle Sitzung sauber abschließen; bei Rückkehr
            # zur Strecke beginnt automatisch eine neue Datei.
            self._flush()
            self._set_state(STATE_MENUS if frame.in_menus else STATE_PAUSED)
            return
        if frame.in_pitlane:
            self._flush()
            self._set_state(STATE_PIT)
            return
        key = (frame.track or "unknown", frame.layout or frame.track or "unknown",
               frame.vehicle or "unknown", frame.session_type)
        if key != getattr(self, "_session_key", None) or self.current_file is None:
            if self._rows:
                self._flush()
            self._new_session(frame)
        row = sample_from_frame(frame)
        if self._t0 is None:
            self._t0 = time.monotonic()
        row[0] = round(time.monotonic() - self._t0, 4)
        with self._lock:
            self._rows.append(row)
            self.samples += 1
        self._set_state(STATE_RECORDING)
