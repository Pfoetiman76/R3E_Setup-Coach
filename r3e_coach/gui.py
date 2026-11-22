import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPlainTextEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from . import __version__
from .advice import build_advice
from .bridge_config import load_gui_config, default_config_path
from .logdata import read_log, session_from_log
from .queries import connect as db_connect, lap_stats
from .recorder import (STATE_MENUS, STATE_PAUSED, STATE_PIT,
                       STATE_RECORDING, STATE_STOPPED, STATE_WAITING,
                       Recorder, default_recordings_dir)
from .report import finding_dicts, render_text
from .setup_sheet import build_sheet, suggest_filename, write_sheet
from .rules import Ctx, analyze
from .store import (add_analysis, default_store_path, ensure_entry, entry_key,
                    get_entry, list_keys, load, save, upsert_values)
from .theme import apply_theme
from .updater import _start_swap, check_for_update, prepare_update

LABELS = {
    "de": {
        "title": "R3E Setup-Coach",
        "tab_record": "1) Aufzeichnen (RaceRoom)",
        "tab_analyze": "2) Telemetrie analysieren",
        "tab_setups": "3) Setups",
        "record": "Telemetrie aufzeichnen",
        "start": "Aufzeichnung starten",
        "stop": "Aufzeichnung stoppen",
        "outdir": "Zielordner:",
        "browse_out": "Wählen …",
        "rec_state_stopped": "Aufzeichnung gestoppt.",
        "rec_state_waiting": "Warte auf RaceRoom — Spiel bitte starten.",
        "rec_state_menus": "RaceRoom läuft — warte, bis Sie auf der Strecke sind.",
        "rec_state_paused": "Spiel pausiert — Aufzeichnung ruht.",
        "rec_state_pit": "In der Boxengasse — Aufzeichnung ruht.",
        "rec_state_recording": "Aufzeichnung läuft: {track} — {vehicle} ({samples} Samples)",
        "rec_saved": "Gespeichert: {file}",
        "rec_error": "Fehler bei der Aufzeichnung: {err}",
        "auto_record": "Automatisch aufzeichnen, sobald RaceRoom läuft (Start-Knopf entfällt)",
        "auto_started": "Automatische Aufzeichnung aktiv — warte auf RaceRoom …",
        "analyze": "Telemetrie analysieren und speichern",
        "log": "Aufzeichnung (.coachlog):",
        "browse": "Durchsuchen …",
        "run": "Analysieren",
        "run_save": "Analysieren und speichern",
        "sheet_btn": "Setup-Zettel …",
        "sheet_saved": "Setup-Zettel gespeichert: {file}",
        "sheet_need": "Bitte zuerst analysieren: Der Zettel beruht auf der aktuellen Telemetrie-Analyse.",
        "track": "Strecke:",
        "layout": "Layout:",
        "vehicle": "Fahrzeug:",
        "setups": "Gespeicherte Setups",
        "refresh": "Aktualisieren",
        "notes": "Notizen:",
        "target": "Zielzeit (ms):",
        "apply_values": "Setup-Werte übernehmen",
        "col_key": "Strecke | Layout | Fahrzeug",
        "col_target": "Zielzeit",
        "col_best": "Bestzeit (Resultate)",
        "col_avg": "Ø-Zeit (Resultate)",
        "col_updated": "Aktualisiert",
        "ready": "Bereit.",
        "need_log": "Bitte eine .coachlog-Aufzeichnung auswählen.",
        "need_key": "Bitte Strecke und Fahrzeug angeben, um die Analyse zu speichern.",
        "saved": "Analyse gespeichert unter '{key}'.",
        "values_saved": "Setup-Werte gespeichert.",
        "no_setups": "Noch keine Setups gespeichert.",
        "update_available": "Update verfügbar: {tag}",
        "update_current": "Version {version} — aktuell",
        "update_check_failed": "Version {version} — Update-Prüfung fehlgeschlagen",
        "update_btn": "Update installieren",
        "update_downloading": "Update wird geladen …",
        "update_restart": "Update installiert — App startet neu …",
        "update_error": "Update fehlgeschlagen: {err}",
        "update_no_exe": "Kein Exe-Modus (aus Quelle gestartet) — Update bitte manuell ausführen.",
    },
    "en": {
        "title": "R3E Setup Coach",
        "tab_record": "1) Record (RaceRoom)",
        "tab_analyze": "2) Analyze telemetry",
        "tab_setups": "3) Setups",
        "record": "Record telemetry",
        "start": "Start recording",
        "stop": "Stop recording",
        "outdir": "Destination folder:",
        "browse_out": "Browse …",
        "rec_state_stopped": "Recording stopped.",
        "rec_state_waiting": "Waiting for RaceRoom — please start the game.",
        "rec_state_menus": "RaceRoom running — waiting until you are on track.",
        "rec_state_paused": "Game paused — recording idle.",
        "rec_state_pit": "In pit lane — recording idle.",
        "rec_state_recording": "Recording: {track} — {vehicle} ({samples} samples)",
        "rec_saved": "Saved: {file}",
        "rec_error": "Recording error: {err}",
        "auto_record": "Record automatically as soon as RaceRoom runs (no start button needed)",
        "auto_started": "Automatic recording active — waiting for RaceRoom …",
        "analyze": "Analyze telemetry and save",
        "log": "Recording (.coachlog):",
        "browse": "Browse …",
        "run": "Analyze",
        "run_save": "Analyze and save",
        "sheet_btn": "Setup sheet …",
        "sheet_saved": "Setup sheet saved: {file}",
        "sheet_need": "Please analyze first: the sheet is based on the current telemetry analysis.",
        "track": "Track:",
        "layout": "Layout:",
        "vehicle": "Vehicle:",
        "setups": "Saved setups",
        "refresh": "Refresh",
        "notes": "Notes:",
        "target": "Target lap (ms):",
        "apply_values": "Apply setup values",
        "col_key": "Track | Layout | Vehicle",
        "col_target": "Target lap",
        "col_best": "Best lap (results)",
        "col_avg": "Avg lap (results)",
        "col_updated": "Updated",
        "ready": "Ready.",
        "need_log": "Please pick a .coachlog recording.",
        "need_key": "Please provide track and vehicle to save the analysis.",
        "saved": "Analysis saved under '{key}'.",
        "values_saved": "Setup values saved.",
        "no_setups": "No setups saved yet.",
        "update_available": "Update available: {tag}",
        "update_current": "Version {version} — up to date",
        "update_check_failed": "Version {version} — update check failed",
        "update_btn": "Install update",
        "update_downloading": "Downloading update …",
        "update_restart": "Update installed — restarting app …",
        "update_error": "Update failed: {err}",
        "update_no_exe": "Not running as exe (started from source) — please update manually.",
    },
}

STATE_LABELS = {
    STATE_STOPPED: "rec_state_stopped",
    STATE_WAITING: "rec_state_waiting",
    STATE_MENUS: "rec_state_menus",
    STATE_PAUSED: "rec_state_paused",
    STATE_PIT: "rec_state_pit",
    STATE_RECORDING: "rec_state_recording",
}


def _icon_candidates():
    """Kandidaten-Pfade für das Fenster-Icon.

    PNG bevorzugt: Qt kann die PNG-komprimierten Einträge der ICO-Datei
    nicht lesen (Windows für Exe/Verknüpfung schon) — das Fenster- und
    Taskleisten-Icon lädt daher assets/app.png, das ICO bleibt Fallback.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        internal = Path(getattr(sys, "_MEIPASS", exe_dir / "_internal"))
        bases = [internal, exe_dir, exe_dir / "_internal"]
    else:
        bases = [Path(__file__).resolve().parent.parent / "assets"]
    return [b / "app.png" for b in bases] + [b / "app.ico" for b in bases]


def _app_icon():
    """QIcon aus app.png/app.ico, oder None, wenn nichts Ladbares vorhanden ist."""
    for cand in _icon_candidates():
        if cand.is_file():
            icon = QIcon(str(cand))
            if not icon.isNull():
                return icon
    return None


class _UpdateSignals(QObject):
    """Thread-sichere Rückmeldung aus dem Update-Worker-Thread an die GUI.

    Qt-Regel: QTimer darf NUR im (GUI-)Hauptthread verwendet werden. Ein
    Hintergrund-Thread meldet daher Ergebnisse über Signale.
    """

    done = Signal(str)    # Pfad des Tausch-Batches
    failed = Signal(str)  # Fehlermeldung


class CoachGui(QMainWindow):
    def __init__(self, lang="de"):
        super().__init__()
        self.lang = lang
        self.t = LABELS[lang]
        self.recorder = None
        self.recorder_thread = None
        self._rec_files_seen = set()
        self.config, self._config_path = load_gui_config()
        self.update_info = None
        self._update_signals = _UpdateSignals()
        self._update_signals.done.connect(self._on_update_done)
        self._update_signals.failed.connect(self._on_update_error)
        self.setWindowTitle(f"{self.t['title']} {__version__}")
        self.resize(880, 640)

        tabs = QTabWidget()
        tabs.addTab(self._build_record_tab(), self.t["tab_record"])
        tabs.addTab(self._build_analyze_tab(), self.t["tab_analyze"])
        tabs.addTab(self._build_setups_tab(), self.t["tab_setups"])
        self.setCentralWidget(tabs)

        self.status_label = QLabel(self.t["ready"])
        self.statusBar().addPermanentWidget(self.status_label)
        self.update_btn = QPushButton(self.t["update_btn"])
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self.install_update)
        self.statusBar().addPermanentWidget(self.update_btn)

        self.rec_poll = QTimer(self)
        self.rec_poll.setInterval(500)
        self.rec_poll.timeout.connect(self._poll_recorder)
        QTimer.singleShot(0, self._auto_start_recording)
        QTimer.singleShot(0, self._check_update)

    # ---------- Oberfläche ----------

    def _build_record_tab(self):
        box = QGroupBox(self.t["record"])
        grid = QGridLayout(box)
        grid.addWidget(QLabel(self.t["outdir"]), 0, 0)
        self.outdir_edit = QLineEdit(self.config.get("recordings_dir") or default_recordings_dir())
        grid.addWidget(self.outdir_edit, 0, 1)
        browse = QPushButton(self.t["browse_out"])
        browse.clicked.connect(self.browse_outdir)
        grid.addWidget(browse, 0, 2)
        self.rec_state_label = QLabel(self.t["rec_state_stopped"])
        grid.addWidget(self.rec_state_label, 1, 0, 1, 3)
        self.auto_record_check = QCheckBox(self.t["auto_record"])
        self.auto_record_check.setChecked(bool(self.config.get("auto_record", True)))
        self.auto_record_check.toggled.connect(self._toggle_auto_record)
        grid.addWidget(self.auto_record_check, 2, 0, 1, 3)
        row = QHBoxLayout()
        self.rec_start_btn = QPushButton(self.t["start"])
        self.rec_start_btn.clicked.connect(self.start_recording)
        self.rec_stop_btn = QPushButton(self.t["stop"])
        self.rec_stop_btn.setEnabled(False)
        self.rec_stop_btn.clicked.connect(self.stop_recording)
        row.addWidget(self.rec_start_btn)
        row.addWidget(self.rec_stop_btn)
        row.addStretch(1)
        grid.addLayout(row, 2, 0, 1, 3)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(box)
        lay.addStretch(1)
        return page

    def _build_analyze_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        grid = QGridLayout()
        grid.addWidget(QLabel(self.t["log"]), 0, 0)
        self.log_edit = QLineEdit()
        grid.addWidget(self.log_edit, 0, 1)
        browse = QPushButton(self.t["browse"])
        browse.clicked.connect(self.browse_log)
        grid.addWidget(browse, 0, 2)
        grid.addWidget(QLabel(self.t["track"]), 1, 0)
        self.track_edit = QLineEdit()
        grid.addWidget(self.track_edit, 1, 1)
        grid.addWidget(QLabel(self.t["layout"]), 2, 0)
        self.layout_edit = QLineEdit()
        grid.addWidget(self.layout_edit, 2, 1)
        grid.addWidget(QLabel(self.t["vehicle"]), 3, 0)
        self.vehicle_edit = QLineEdit()
        grid.addWidget(self.vehicle_edit, 3, 1)
        lay.addLayout(grid)
        row = QHBoxLayout()
        run = QPushButton(self.t["run"])
        run.clicked.connect(self.run_analyze)
        run_save = QPushButton(self.t["run_save"])
        run_save.clicked.connect(self.run_analyze_save)
        row.addWidget(run)
        row.addWidget(run_save)
        sheet_btn = QPushButton(self.t["sheet_btn"])
        sheet_btn.clicked.connect(self.make_setup_sheet)
        row.addWidget(sheet_btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        lay.addWidget(self.output, 1)
        return page

    def _build_setups_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.t["setups"]))
        refresh = QPushButton(self.t["refresh"])
        refresh.clicked.connect(self.reload_setups)
        row.addStretch(1)
        row.addWidget(refresh)
        lay.addLayout(row)
        self.setups_table = QTableWidget(0, 5)
        self.setups_table.setHorizontalHeaderLabels(
            [self.t["col_key"], self.t["col_target"], self.t["col_best"],
             self.t["col_avg"], self.t["col_updated"]])
        self.setups_table.horizontalHeader().setStretchLastSection(True)
        self.setups_table.setColumnWidth(0, 420)
        self.setups_table.setColumnWidth(1, 100)
        self.setups_table.setColumnWidth(2, 130)
        self.setups_table.setColumnWidth(3, 130)
        self.setups_table.itemDoubleClicked.connect(self._show_setup_detail)
        self.setups_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.setups_table)
        detail = QGridLayout()
        detail.addWidget(QLabel(self.t["target"]), 0, 0)
        self.target_edit = QLineEdit()
        detail.addWidget(self.target_edit, 0, 1)
        detail.addWidget(QLabel(self.t["notes"]), 0, 2)
        self.notes_edit = QLineEdit()
        detail.addWidget(self.notes_edit, 0, 3)
        self.apply_btn = QPushButton(self.t["apply_values"])
        self.apply_btn.clicked.connect(self.apply_setup_values)
        detail.addWidget(self.apply_btn, 0, 4)
        lay.addLayout(detail)
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        lay.addWidget(self.detail_view, 1)
        return page

    # ---------- Aufzeichnung ----------

    def browse_outdir(self):
        path = QFileDialog.getExistingDirectory(self, self.t["outdir"],
                                                self.outdir_edit.text().strip() or "")
        if path:
            self.outdir_edit.setText(path)

    def _persist_recordings_dir(self, out_dir):
        try:
            path = self._config_path or default_config_path()
            try:
                data = load_gui_config(path)[0]
            except Exception:
                data = {}
            if data.get("recordings_dir") == out_dir:
                return
            from .bridge_config import save_config
            data["recordings_dir"] = out_dir
            save_config(path, data)
            self._config_path = path
        except Exception:
            pass

    def _persist_auto_record(self, enabled):
        """auto_record in der Config sichern (Fehler still — Aufnahme läuft weiter)."""
        try:
            path = self._config_path or default_config_path()
            try:
                data = load_gui_config(path)[0]
            except Exception:
                data = {}
            from .bridge_config import save_config
            data["auto_record"] = bool(enabled)
            save_config(path, data)
            self._config_path = path
        except Exception:
            pass

    def _auto_start_recording(self):
        """0.8.1: Wie PitBoss — die App startet die Aufzeichnung von selbst."""
        if self.auto_record_check.isChecked():
            self.start_recording()
            self.rec_state_label.setText(self.t["auto_started"])

    def _toggle_auto_record(self, checked):
        self._persist_auto_record(checked)
        if checked:
            if self.recorder is None:
                self.start_recording()
                self.rec_state_label.setText(self.t["auto_started"])
        else:
            if self.recorder is not None:
                self.stop_recording()

    def start_recording(self):
        if self.recorder is not None:
            return
        out_dir = self.outdir_edit.text().strip() or default_recordings_dir()
        self._persist_recordings_dir(out_dir)
        self.recorder = Recorder(out_dir=out_dir)
        self.recorder_thread = threading.Thread(target=self.recorder.run, daemon=True)
        self.recorder_thread.start()
        self.rec_start_btn.setEnabled(False)
        self.rec_stop_btn.setEnabled(True)
        self.rec_poll.start()
        if not self.auto_record_check.isChecked():
            self.auto_record_check.blockSignals(True)
            self.auto_record_check.setChecked(True)
            self.auto_record_check.blockSignals(False)
            self._persist_auto_record(True)

    def stop_recording(self, user_stop=True):
        if self.recorder is None:
            return
        rec = self.recorder
        rec.stop()
        if self.recorder_thread is not None:
            self.recorder_thread.join(timeout=5)
        self.recorder = None
        self.recorder_thread = None
        self.rec_poll.stop()
        self.rec_state_label.setText(self.t["rec_state_stopped"])
        self.rec_start_btn.setEnabled(True)
        self.rec_stop_btn.setEnabled(False)
        if user_stop and self.auto_record_check.isChecked():
            self.auto_record_check.blockSignals(True)
            self.auto_record_check.setChecked(False)
            self.auto_record_check.blockSignals(False)
            self._persist_auto_record(False)

    def _poll_recorder(self):
        """Fragt den Recorder-Status ab (reiner Lesezugriff im GUI-Thread)."""
        if self.recorder is None:
            return
        st = self.recorder.status()
        label = STATE_LABELS.get(st["state"], "rec_state_stopped")
        if st["state"] == STATE_RECORDING:
            self.rec_state_label.setText(self.t[label].format(
                track=st["meta"].get("track", "?"),
                vehicle=st["meta"].get("vehicle", "?"),
                samples=st["samples"]))
        else:
            self.rec_state_label.setText(self.t[label])
        if st["error"]:
            self.status_label.setText(self.t["rec_error"].format(err=st["error"]))
        for path in st["files"]:
            if path not in self._rec_files_seen:
                self._rec_files_seen.add(path)
                self.status_label.setText(self.t["rec_saved"].format(file=os.path.basename(path)))
                self.log_edit.setText(path)  # neueste Aufzeichnung direkt zum Analysieren

    def closeEvent(self, event):
        self.stop_recording(user_stop=False)
        super().closeEvent(event)

    # ---------- Analyse ----------

    def browse_log(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t["log"], "",
                                              "Coach-Log (*.coachlog);;Alle Dateien (*.*)")
        if path:
            self.log_edit.setText(path)
            self._fill_key_from_log(path)

    def _fill_key_from_log(self, path):
        """Strecke/Layout/Fahrzeug automatisch aus dem Log übernehmen."""
        try:
            meta, _, _, _ = read_log(path)
        except (OSError, ValueError):
            return
        if meta.get("track"):
            self.track_edit.setText(meta["track"])
        if meta.get("layout"):
            self.layout_edit.setText(meta["layout"])
        if meta.get("vehicle"):
            self.vehicle_edit.setText(meta["vehicle"])

    def _stored_setup_values(self):
        """Gespeicherte Setup-Werte, wenn Strecke+Auto im Reiter stehen."""
        track = self.track_edit.text().strip()
        vehicle = self.vehicle_edit.text().strip()
        if not track or not vehicle:
            return None, None
        try:
            key = entry_key(track, self.layout_edit.text().strip() or None, vehicle)
            entry = get_entry(load(default_store_path()), key)
        except (OSError, ValueError):
            return None, None
        if not entry:
            return None, None
        return entry.get("chassis") or None, entry.get("tires") or None

    def _analyze_current(self):
        path = self.log_edit.text().strip()
        if not path:
            self._show(self.t["need_log"])
            return None
        try:
            session = session_from_log(path)
        except (OSError, ValueError) as exc:
            self._show(str(exc))
            return None
        findings = analyze(session, Ctx())
        chassis, tires = self._stored_setup_values()
        advice = build_advice(findings, chassis, tires)
        self._show(render_text(findings, session, lang=self.lang, advice=advice))
        return {"session": session, "findings": findings, "advice": advice}

    def run_analyze(self):
        self._analyze_current()

    def make_setup_sheet(self):
        """0.9.0: Setup-Zettel — Garage-Checkliste aus der aktuellen Analyse."""
        result = self._analyze_current()
        if result is None:
            self._show(self.t["sheet_need"])
            return
        meta = {
            "track": self.track_edit.text().strip() or None,
            "layout": self.layout_edit.text().strip() or None,
            "vehicle": self.vehicle_edit.text().strip() or None,
        }
        key = None
        if meta["track"] and meta["vehicle"]:
            key = entry_key(meta["track"], meta["layout"] or None, meta["vehicle"])
        text = build_sheet(meta, result["advice"], lang=self.lang, key=key,
                           log_source=os.path.abspath(self.log_edit.text().strip()))
        default = os.path.join(self.outdir_edit.text().strip()
                               or os.path.expanduser("~"),
                               suggest_filename(meta, lang=self.lang))
        path, _ = QFileDialog.getSaveFileName(
            self, self.t["sheet_btn"], default, "Textdatei (*.txt);;Alle Dateien (*.*)")
        if not path:
            return
        write_sheet(path, text)
        self._show(text)
        self.status_label.setText(self.t["sheet_saved"].format(file=path))

    def run_analyze_save(self):
        result = self._analyze_current()
        if result is None:
            return
        track = self.track_edit.text().strip()
        vehicle = self.vehicle_edit.text().strip()
        if not track or not vehicle:
            self._show(self.t["need_key"])
            return
        key = entry_key(track, self.layout_edit.text().strip() or None, vehicle)
        data = load()
        add_analysis(data, key, {
            "log_source": os.path.abspath(self.log_edit.text().strip()),
            "samples": len(result["session"]),
            "findings": finding_dicts(result["findings"]),
        })
        save(data, default_store_path())
        self.status_label.setText(self.t["saved"].format(key=key))
        self.reload_setups()

    # ---------- Setups ----------

    def reload_setups(self):
        data = load(default_store_path())
        keys = list_keys(data)
        self.setups_table.setRowCount(0)
        if not keys:
            self.setups_table.setRowCount(1)
            item = QTableWidgetItem(self.t["no_setups"])
            item.setFlags(Qt.NoItemFlags)
            self.setups_table.setItem(0, 0, item)
            return
        self.setups_table.setRowCount(len(keys))
        with db_connect() as conn:
            for row, key in enumerate(keys):
                entry = data["setups"][key]
                self.setups_table.setItem(row, 0, QTableWidgetItem(key))
                target = entry.get("target_lap_ms")
                track, layout, vehicle = key.split("|", 2)
                stats = lap_stats(conn, track, layout, vehicle)
                best, avg = (stats or {}).get("best_ms"), (stats or {}).get("avg_ms")
                target_item = QTableWidgetItem(
                    f"{target / 1000:.3f} s" if isinstance(target, (int, float)) else "—")
                target_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if isinstance(target, (int, float)) and best:
                    delta = target - best
                    target_item.setToolTip(
                        f"Delta Ziel − Best: {delta / 1000:+.3f} s")
                    target_item.setForeground(
                        QColor("#8fd18f") if delta < 0 else QColor("#f2a3a3")
                        if delta > 2000 else QColor("#e6e6e8"))
                self.setups_table.setItem(row, 1, target_item)
                best_item = QTableWidgetItem(
                    f"{best / 1000:.3f} s" if best else "—")
                best_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setups_table.setItem(row, 2, best_item)
                avg_item = QTableWidgetItem(
                    f"{avg / 1000:.3f} s" if avg else "—")
                avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setups_table.setItem(row, 3, avg_item)
                self.setups_table.setItem(row, 4, QTableWidgetItem(entry.get("updated_at") or "—"))

    def _show_setup_detail(self, item):
        import json as _json
        row = item.row()
        key_item = self.setups_table.item(row, 0)
        if key_item is None or "|" not in key_item.text():
            return
        key = key_item.text()
        data = load(default_store_path())
        entry = data["setups"].get(key)
        if entry is None:
            return
        target = entry.get("target_lap_ms")
        self.target_edit.setText(str(target) if isinstance(target, int) else "")
        self.notes_edit.setText(entry.get("notes") or "")
        self.detail_view.setPlainText(_json.dumps({key: entry}, ensure_ascii=False, indent=2))

    def apply_setup_values(self):
        row = self.setups_table.currentRow()
        key_item = self.setups_table.item(row, 0) if row >= 0 else None
        if key_item is None or "|" not in key_item.text():
            return
        track, layout, vehicle = key_item.text().split("|", 2)
        key = entry_key(track, layout, vehicle)
        data = load(default_store_path())
        ensure_entry(data, key)
        target = self.target_edit.text().strip()
        upsert_values(data, key, notes=self.notes_edit.text().strip() or None,
                      target_lap_ms=int(target) if target.isdigit() else None)
        save(data, default_store_path())
        self.status_label.setText(self.t["values_saved"])
        self.reload_setups()

    # ---------- Ausgabe / Update ----------

    def _show(self, text):
        self.output.setPlainText(text)

    def _check_update(self):
        try:
            info = check_for_update()
            failed = False
        except Exception:
            info = None
            failed = True
        self.update_info = info
        if info is not None:
            self._show(self.t["update_available"].format(tag=info.tag))
            self.update_btn.setEnabled(True)
        elif failed:
            self._show(self.t["update_check_failed"].format(version=__version__))
        else:
            self._show(self.t["update_current"].format(version=__version__))

    def install_update(self):
        if self.update_info is None:
            return
        self.update_btn.setEnabled(False)
        self.status_label.setText(self.t["update_downloading"])
        self._show(self.t["update_downloading"])

        def work():
            try:
                cmd_path = prepare_update(self.update_info)
                self._update_signals.done.emit(str(cmd_path))
            except Exception as exc:
                self._update_signals.failed.emit(str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_done(self, cmd_path):
        self._show(self.t["update_restart"])
        self.status_label.setText(self.t["update_restart"])
        _start_swap(cmd_path)
        QApplication.instance().quit()

    def _on_update_error(self, err):
        self._show(self.t["update_error"].format(err=err))
        self.status_label.setText(self.t["update_error"].format(err=err))
        self.update_btn.setEnabled(True)


def main_gui(lang="de"):
    app = QApplication(sys.argv)
    apply_theme(app)
    icon = _app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    window = CoachGui(lang=lang)
    window.show()
    window.reload_setups()
    sys.exit(app.exec())
