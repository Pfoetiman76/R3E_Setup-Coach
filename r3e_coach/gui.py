import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

from .bridge import (BridgeError, BridgeProcess, find_config, load_config, resolve_args,
                     resolve_exe)
from .parser import parse_motec_csv
from .report import render_text
from .rules import Ctx, analyze
from .updater import (apply_pending_update, check_for_update, current_exe_path,
                      download_update, pending_path)

LABELS = {
    "de": {
        "title": "R3E Setup-Coach",
        "bridge": "1) Bridge starten (RaceRoom → MoTeC)",
        "exe": "Bridge-Exe:",
        "start": "Bridge starten",
        "stop": "Bridge stoppen (Strg+C im Terminal entfällt)",
        "analyze": "2) Telemetrie analysieren",
        "csv": "MoTeC-i2-CSV:",
        "browse": "Durchsuchen …",
        "run": "Analysieren",
        "ready": "Bereit.",
        "running": "Bridge läuft (PID {pid}) — fahren, dann stoppen.",
        "stopped": "Bridge beendet.",
        "exited": "Bridge hat sich selbst beendet (Exit {rc}).",
        "need_csv": "Bitte CSV-Datei auswählen.",
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
        "bridge": "1) Start bridge (RaceRoom → MoTeC)",
        "exe": "Bridge exe:",
        "start": "Start bridge",
        "stop": "Stop bridge",
        "analyze": "2) Analyze telemetry",
        "csv": "MoTeC i2 CSV:",
        "browse": "Browse …",
        "run": "Analyze",
        "ready": "Ready.",
        "running": "Bridge running (PID {pid}) — drive, then stop.",
        "stopped": "Bridge stopped.",
        "exited": "Bridge exited on its own (exit {rc}).",
        "need_csv": "Please pick a CSV file.",
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


class CoachGui:
    def __init__(self, root, lang="de"):
        self.root = root
        self.lang = lang
        self.t = LABELS[lang]
        self.bridge = None
        self.config = load_gui_config()
        root.title(self.t["title"])
        root.geometry("720x560")

        bridge_box = ttk.LabelFrame(root, text=self.t["bridge"])
        bridge_box.pack(fill="x", padx=8, pady=6)
        ttk.Label(bridge_box, text=self.t["exe"]).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.exe_var = tk.StringVar(value=self.config.get("bridge_exe", ""))
        ttk.Entry(bridge_box, textvariable=self.exe_var, width=60).grid(row=0, column=1, padx=4, pady=4)
        self.start_btn = ttk.Button(bridge_box, text=self.t["start"], command=self.start_bridge)
        self.start_btn.grid(row=1, column=0, padx=4, pady=4, sticky="w")
        self.stop_btn = ttk.Button(bridge_box, text=self.t["stop"], command=self.stop_bridge, state="disabled")
        self.stop_btn.grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ana_box = ttk.LabelFrame(root, text=self.t["analyze"])
        ana_box.pack(fill="x", padx=8, pady=6)
        ttk.Label(ana_box, text=self.t["csv"]).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.csv_var = tk.StringVar()
        ttk.Entry(ana_box, textvariable=self.csv_var, width=60).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(ana_box, text=self.t["browse"], command=self.browse_csv).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(ana_box, text=self.t["run"], command=self.run_analyze).grid(row=1, column=0, padx=4, pady=4, sticky="w")

        self.status_var = tk.StringVar(value=self.t["ready"])
        ttk.Label(root, textvariable=self.status_var, foreground="blue").pack(anchor="w", padx=8)
        self.update_info = None
        self.update_btn = ttk.Button(root, text=self.t["update_btn"], command=self.install_update,
                                     state="disabled")
        self.update_btn.pack(anchor="e", padx=8)
        self.output = scrolledtext.ScrolledText(root, wrap="word", height=22)
        self.output.pack(fill="both", expand=True, padx=8, pady=6)
        self._check_update()

    def _set_status(self, key, **kwargs):
        self.status_var.set(self.t[key].format(**kwargs) if kwargs else self.t[key])

    def start_bridge(self):
        try:
            exe = resolve_exe(self.exe_var.get().strip() or None, self.config)
            args = resolve_args(None, self.config)
            cwd = self.config.get("bridge_cwd")
        except BridgeError as exc:
            self._show(str(exc))
            return
        self.bridge = BridgeProcess(exe, args, cwd=cwd)
        self.bridge.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._set_status("running", pid=self.bridge.proc.pid)
        self._poll_bridge()

    def _poll_bridge(self):
        if self.bridge is None:
            return
        if self.bridge.is_running():
            self.root.after(500, self._poll_bridge)
        else:
            rc = self.bridge.proc.returncode
            self._set_status("exited", rc=rc)
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def stop_bridge(self):
        if self.bridge is not None:
            self.bridge.stop()
        self._set_status("stopped")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def browse_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Alle Dateien", "*.*")])
        if path:
            self.csv_var.set(path)

    def run_analyze(self):
        path = self.csv_var.get().strip()
        if not path:
            self._show(self.t["need_csv"])
            return
        session = parse_motec_csv(path)
        findings = analyze(session, Ctx())
        self._show(render_text(findings, session, lang=self.lang))

    def _show(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    def _check_update(self):
        try:
            info = check_for_update()
        except Exception:
            info = None
        self.update_info = info
        if info is not None:
            self._show(self.t["update_available"].format(tag=info.tag))
            self.update_btn.config(state="normal")

    def install_update(self):
        if self.update_info is None:
            return
        self.update_btn.config(state="disabled")
        self._show(self.t["update_downloading"])

        def work():
            try:
                exe = current_exe_path()
                if exe is None:
                    self.root.after(0, lambda: self._show(self.t["update_no_exe"]))
                    return
                dest = pending_path(exe)
                download_update(self.update_info.url, dest)
                applied = apply_pending_update(exe)
                self.root.after(0, self._on_update_done, applied, exe)
            except Exception as exc:
                self.root.after(0, lambda: self._show(self.t["update_error"].format(err=exc)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_done(self, applied, exe):
        if applied:
            self._show(self.t["update_restart"])
            self.root.after(800, lambda: os.execv(sys.executable, [sys.executable]))
        else:
            self._show(self.t["update_nextstart"])


def main_gui(lang="de"):
    root = tk.Tk()
    CoachGui(root, lang=lang)
    root.mainloop()
