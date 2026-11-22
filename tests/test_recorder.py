"""Tests für recorder.py: Zustandsmaschine, Sitzungstrennung, saubere Dateien.

Fake-Shared-Memory: Sequenz von R3EMemory(mem=build_buffer(...))-Puffern.
"""

import threading

import pytest

from r3e_coach import r3e_shared as r3s
from r3e_coach.logdata import read_log
from r3e_coach.recorder import (COLUMNS, Recorder, STATE_MENUS,
                                STATE_RECORDING, STATE_WAITING,
                                default_recordings_dir, sample_from_frame)


def _frame(**kw):
    def mutate(s):
        s.game_mode = 0
        s.session_type = r3s.SESSION_PRACTICE
        s.car_speed = 40.0
        s.track_name = kw.get("track", "Sachsenring").encode()
        s.layout_name = kw.get("layout", kw.get("track", "Sachsenring")).encode()
        s.vehicle_info.name = kw.get("vehicle", "Audi R8").encode()
        if kw.get("menus"):
            s.game_in_menus = 1
        if kw.get("pit"):
            s.in_pitlane = 1
    return r3s.R3EMemory(mem=r3s.R3EMemory.build_buffer(mutate)).read_frame()


class FakeMemory:
    """Liefert pro read_frame() den nächsten injizierten Frame-Buffer."""

    def __init__(self, buffers):
        self._buffers = list(buffers)
        self.i = 0

    @classmethod
    def opener(cls, buffers):
        def open_():
            return cls(buffers)
        return open_

    def read_frame(self):
        if self.i >= len(self._buffers):
            raise OSError("Sequence zu Ende")
        buf = self._buffers[self.i]
        self.i += 1
        return r3s.R3EMemory(mem=buf).read_frame()

    def close(self):
        pass


def _buffer(**kw):
    def mutate(s):
        s.game_mode = 0
        s.session_type = r3s.SESSION_PRACTICE
        s.car_speed = 40.0
        s.track_name = kw.get("track", "Sachsenring").encode()
        s.layout_name = kw.get("layout", kw.get("track", "Sachsenring")).encode()
        s.vehicle_info.name = kw.get("vehicle", "Audi R8").encode()
        if kw.get("menus"):
            s.game_in_menus = 1
    return r3s.R3EMemory.build_buffer(mutate)


def test_default_dir_points_to_documents_recordings():
    d = default_recordings_dir()
    assert "recordings" in d and "R3E Setup-Coach" in d


def test_sample_from_frame_matches_columns():
    f = _frame()
    row = sample_from_frame(f)
    assert len(row) == len(COLUMNS)
    assert row[0] is None            # time ergänzt der Recorder
    assert row[1] is None                # lap_time_current_self <= 0 -> None
    assert row[2] == pytest.approx(144.0)  # 40 m/s in km/h
    assert row[4] == pytest.approx(0.0)   # brake


def test_handle_records_and_creates_session_file(tmp_path):
    rec = Recorder(out_dir=str(tmp_path), sleep=lambda s: None)
    rec._handle(_frame(track="Sachsenring", vehicle="Audi R8"))
    assert rec.state == STATE_RECORDING
    assert rec.samples == 1
    assert rec.current_file and rec.current_file.endswith(".coachlog")
    assert "Sachsenring" in rec.current_file
    rec._flush()
    assert rec.files
    from pathlib import Path as _P
    assert _P(rec.files[0]).exists()
    meta, columns, units, rows = read_log(rec.files[0])
    assert meta["track"] == "Sachsenring"
    assert meta["vehicle"] == "Audi R8"
    assert meta["hz"] == "50"
    assert len(rows) == 1
    assert rows[0][0] == pytest.approx(0.0)  # Zeitachse startet bei 0


def test_track_change_flushes_and_starts_new_file(tmp_path):
    rec = Recorder(out_dir=str(tmp_path), sleep=lambda s: None)
    rec._handle(_frame(track="Sachsenring"))
    rec._handle(_frame(track="Nürburgring Sprint", vehicle="BMW M4 GT3"))
    assert rec.current_file and "Nrburgring_Sprint" in rec.current_file.replace("\\", "/")
    rec._flush()
    assert len(rec.files) == 2
    meta1, _, _, rows1 = read_log(rec.files[0])
    meta2, _, _, rows2 = read_log(rec.files[1])
    assert meta1["track"] == "Sachsenring" and len(rows1) == 1
    assert meta2["track"] == "Nürburgring Sprint" and len(rows2) == 1


def test_menus_finish_file_cleanly(tmp_path):
    """Das R2M-ESC-Problem: Menü/Sessionwechsel beendet die Datei sauber."""
    rec = Recorder(out_dir=str(tmp_path), sleep=lambda s: None)
    rec._handle(_frame())
    rec._handle(_frame(menus=True))
    assert rec.state == STATE_MENUS
    assert rec.current_file is None
    from pathlib import Path as _P2
    assert rec.files and _P2(rec.files[0]).exists()
    meta, _, _, rows = read_log(rec.files[0])
    assert len(rows) == 1  # alles Vorherige ist gesichert


def test_run_loop_writes_file_on_stop(tmp_path):
    opener = FakeMemory.opener([_buffer(), _buffer(), _buffer(menus=True)])
    rec = Recorder(out_dir=str(tmp_path), hz=1000,
                   open_memory=opener, sleep=lambda s: None)
    t = threading.Thread(target=rec.run, daemon=True)
    t.start()
    for _ in range(200):
        if rec.state in (STATE_MENUS, STATE_RECORDING) and rec.files:
            break
        if rec.state == STATE_MENUS:
            break
    rec.stop()
    t.join(timeout=5)
    assert rec.files, "mindestens eine Datei nach Menü/Stop"
    meta, _, _, rows = read_log(rec.files[0])
    assert meta["track"] == "Sachsenring"
    assert len(rows) >= 1


def test_status_dict_shape(tmp_path):
    rec = Recorder(out_dir=str(tmp_path))
    st = rec.status()
    for key in ("state", "samples", "file", "files", "meta",
                "error", "warning"):
        assert key in st
    assert st["state"] != STATE_RECORDING


def test_missing_memory_waits_without_error(tmp_path):
    """0.9.1: RaceRoom läuft nicht -> Zustand WAITING ohne 'Fehler'-Meldung."""
    def open_missing():
        raise FileNotFoundError('RaceRoom-Shared-Memory "$R3E" nicht gefunden')

    rec = Recorder(out_dir=str(tmp_path), open_memory=open_missing,
                   sleep=lambda s: None)
    frame = rec._read()
    st = rec.status()
    assert frame is None
    assert st["state"] == STATE_WAITING
    assert st["error"] is None
