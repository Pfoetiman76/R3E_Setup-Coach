import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QFileDialog, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .bridge import (BridgeError, BridgeProcess, find_config, load_config, resolve_args,
                     resolve_exe)
from .parser import parse_motec_csv
from .report import finding_dicts, render_text
from .rules import Ctx, analyze
from .store import add_analysis, ensure_entry, list_keys, load, save, upsert_values
from .theme import apply_theme
from .updater import (apply_pending_update, check_for_update, current_exe_path,
                      download_update, pending_path)

LABELS = {
    "de": {
        "title": "R3E Setup-Coach",
        "tab_bridge": "1) Bridge (RaceRoom → MoTeC)",
        "tab_analyze": "2) Telemetrie analysieren",
        "tab_setups": "3) Setups",
        "bridge": "Bridge starten/stoppen",
        "exe": "Bridge-Exe:",
        "start": "Bridge starten",
        "stop": "Bridge stoppen",
        "analyze": "Telemetrie analysieren und speichern",
        "csv": "MoTeC-i2-CSV:",
        "browse": "Durchsuchen …",
        "run": "Analysieren",
        "run_save": "Analysieren und speichern",
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
        "col_updated": "Aktualisiert",
        "ready": "Bereit.",
        "running": "Bridge läuft (PID {pid}) — fahren, dann stoppen.",
        "stopped": "Bridge beendet.",
        "exited": "Bridge hat sich selbst beendet (Exit {rc}).",
        "need_csv": "Bitte CSV-Datei auswählen.",
        "need_key": "Bitte Strecke und Fahrzeug angeben, um die Analyse zu speichern.",
        "saved": "Analyse gespeichert unter '{key}'.",
        "values_saved": "Setup-Werte gespeichert.",
        "no_setups": "Noch keine Setups gespeichert.",
        "update_available": "Update verfügbar: {tag}",
        "update_btn": "Update installieren",
        "update_downloading": "Update wird geladen …",
        "update_restart": "Update installiert — App startet neu …",
        "update_nextstart": "Update geladen — wird beim nächsten Start installiert.",
        "update_error": "Update fehlgeschlagen: {err}",
        "update_no_exe": "Kein Exe-Modus (aus Quelle gestartet) — Update bitte manuell ausführen.",
    },
    "en": {
        "title": "R3E Setup Coach",
        "tab_bridge": "1) Bridge (RaceRoom → MoTeC)",
        "tab_analyze": "2) Analyze telemetry",
        "tab_setups": "3) Setups",
        "bridge": "Start/stop bridge",
        "exe": "Bridge exe:",
        "start": "Start bridge",
        "stop": "Stop bridge",
        "analyze": "Analyze telemetry and save",
        "csv": "MoTeC i2 CSV:",
        "browse": "Browse …",
        "run": "Analyze",
        "run_save": "Analyze and save",
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
        "col_updated": "Updated",
        "ready": "Ready.",
        "running": "Bridge running (PID {pid}) — drive, then stop.",
        "stopped": "Bridge stopped.",
        "exited": "Bridge exited on its own (exit {rc}).",
        "need_csv": "Please pick a CSV file.",
        "need_key": "Please provide track and vehicle to save the analysis.",
        "saved": "Analysis saved under '{key}'.",
        "values_saved": "Setup values saved.",
        "no_setups": "No setups saved yet.",
        "update_available": "Update available: {tag}",
        "update_btn": "Install update",
        "update_downloading": "Downloading update …",
        "update_restart": "Update installed — restarting app …",
        "update_nextstart": "Update downloaded — will be installed on next start.",
        "update_error": "Update failed: {err}",
        "update_no_exe": "Not running as exe (started from source) — please update manually.",
    },
}


def load_gui_config(config_path=None):
    path = find_config(config_path)
    return load_config(path) if path else {}


class CoachGui(QMainWindow):
    def __init__(self, lang="de"):
        super().__init__()
        self.lang = lang
        self.t = LABELS[lang]
        self.bridge = None
        self.bridge_poll = QTimer(self)
        self.bridge_poll.setInterval(500)
        self.bridge_poll.timeout.connect(self._poll_bridge)
        self.config = load_gui_config()
        self.update_info = None
        self.setWindowTitle(self.t["title"])
        self.resize(880, 640)

        tabs = QTabWidget()
        tabs.addTab(self._build_bridge_tab(), self.t["tab_bridge"])
        tabs.addTab(self._build_analyze_tab(), self.t["tab_analyze"])
        tabs.addTab(self._build_setups_tab(), self.t["tab_setups"])
        self.setCentralWidget(tabs)

        self.status_label = QLabel(self.t["ready"])
        self.statusBar().addPermanentWidget(self.status_label)
        self.update_btn = QPushButton(self.t["update_btn"])
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self.install_update)
        self.statusBar().addPermanentWidget(self.update_btn)
        QTimer.singleShot(0, self._check_update)

    # ---------- Oberfläche ----------

    def _build_bridge_tab(self):
        box = QGroupBox(self.t["bridge"])
        grid = QGridLayout(box)
        grid.addWidget(QLabel(self.t["exe"]), 0, 0)
        self.exe_edit = QLineEdit(self.config.get("bridge_exe", ""))
        grid.addWidget(self.exe_edit, 0, 1)
        row = QHBoxLayout()
        self.start_btn = QPushButton(self.t["start"])
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn = QPushButton(self.t["stop"])
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_bridge)
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addStretch(1)
        grid.addLayout(row, 1, 0, 1, 2)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(box)
        lay.addStretch(1)
        return page

    def _build_analyze_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        grid = QGridLayout()
        grid.addWidget(QLabel(self.t["csv"]), 0, 0)
        self.csv_edit = QLineEdit()
        grid.addWidget(self.csv_edit, 0, 1)
        browse = QPushButton(self.t["browse"])
        browse.clicked.connect(self.browse_csv)
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
        self.setups_table = QTableWidget(0, 3)
        self.setups_table.setHorizontalHeaderLabels(
            [self.t["col_key"], self.t["col_target"], self.t["col_updated"]])
        self.setups_table.horizontalHeader().setStretchLastSection(True)
        self.setups_table.setColumnWidth(0, 460)
        self.setups_table.setColumnWidth(1, 120)
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
        label = QLabel(self.t["apply_values"])
        self.apply_btn = QPushButton(self.t["apply_values"])
        self.apply_btn.clicked.connect(self.apply_setup_values)
        detail.addWidget(self.apply_btn, 0, 4)
        lay.addLayout(detail)
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        lay.addWidget(self.detail_view, 1)
        return page

    # ---------- Bridge ----------

    def _set_status(self, key, **kwargs):
        self.status_label.setText(self.t[key].format(**kwargs) if kwargs else self.t[key])

    def start_bridge(self):
        try:
            exe = resolve_exe(self.exe_edit.text().strip() or None, self.config)
            args = resolve_args(None, self.config)
            cwd = self.config.get("bridge_cwd")
        except BridgeError as exc:
            self._show(str(exc))
            return
        self.bridge = BridgeProcess(exe, args, cwd=cwd)
        self.bridge.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status("running", pid=self.bridge.proc.pid)
        self.bridge_poll.start()

    def _poll_bridge(self):
        if self.bridge is None:
            self.bridge_poll.stop()
            return
        if self.bridge.is_running():
            return
        self.bridge_poll.stop()
        self._set_status("exited", rc=self.bridge.proc.returncode)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def stop_bridge(self):
        if self.bridge is not None:
            self.bridge.stop()
        self._set_status("stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ---------- Analyse ----------

    def browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t["csv"], "",
                                              "CSV (*.csv);;Alle Dateien (*.*)")
        if path:
            self.csv_edit.setText(path)

    def _analyze_current(self):
        path = self.csv_edit.text().strip()
        if not path:
            self._show(self.t["need_csv"])
            return None
        session = parse_motec_csv(path)
        findings = analyze(session, Ctx())
        self._show(render_text(findings, session, lang=self.lang))
        return {"session": session, "findings": findings}

    def run_analyze(self):
        self._analyze_current()

    def run_analyze_save(self):
        result = self._analyze_current()
        if result is None:
            return
        track = self.track_edit.text().strip()
        vehicle = self.vehicle_edit.text().strip()
        if not track or not vehicle:
            self._show(self.t["need_key"])
            return
        from .store import default_store_path, entry_key
        key = entry_key(track, self.layout_edit.text().strip() or None, vehicle)
        data = load()
        add_analysis(data, key, {
            "csv_source": os.path.abspath(self.csv_edit.text().strip()),
            "samples": len(result["session"]),
            "findings": finding_dicts(result["findings"]),
        })
        save(data, default_store_path())
        self._set_status("saved", key=key)
        self.reload_setups()

    # ---------- Setups ----------

    def reload_setups(self):
        from .store import default_store_path
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
        for row, key in enumerate(keys):
            entry = data["setups"][key]
            self.setups_table.setItem(row, 0, QTableWidgetItem(key))
            target = entry.get("target_lap_ms")
            target_item = QTableWidgetItem(
                f"{target / 1000:.3f} s" if isinstance(target, (int, float)) else "—")
            target_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setups_table.setItem(row, 1, target_item)
            self.setups_table.setItem(row, 2, QTableWidgetItem(entry.get("updated_at") or "—"))

    def _show_setup_detail(self, item):
        import json as _json
        from .store import default_store_path
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
        from .store import default_store_path, entry_key
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
        self._set_status("values_saved")
        self.reload_setups()

    # ---------- Ausgabe / Update ----------

    def _show(self, text):
        self.output.setPlainText(text)

    def _check_update(self):
        try:
            info = check_for_update()
        except Exception:
            info = None
        self.update_info = info
        if info is not None:
            self._show(self.t["update_available"].format(tag=info.tag))
            self.update_btn.setEnabled(True)

    def install_update(self):
        if self.update_info is None:
            return
        self.update_btn.setEnabled(False)
        self._show(self.t["update_downloading"])

        def work():
            try:
                exe = current_exe_path()
                if exe is None:
                    QTimer.singleShot(0, lambda: self._show(self.t["update_no_exe"]))
                    return
                dest = pending_path(exe)
                download_update(self.update_info.url, dest)
                applied = apply_pending_update(exe)
                QTimer.singleShot(0, lambda: self._on_update_done(applied, exe))
            except Exception as exc:
                QTimer.singleShot(
                    0, lambda exc=exc: self._show(self.t["update_error"].format(err=exc)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_done(self, applied, exe):
        if applied:
            self._show(self.t["update_restart"])
            QTimer.singleShot(800, lambda: os.execv(sys.executable, [sys.executable]))
        else:
            self._show(self.t["update_nextstart"])


def main_gui(lang="de"):
    app = QApplication(sys.argv)
    apply_theme(app)
    window = CoachGui(lang=lang)
    window.show()
    window.reload_setups()
    sys.exit(app.exec())
