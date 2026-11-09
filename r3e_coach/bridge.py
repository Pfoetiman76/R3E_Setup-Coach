import json
import os
import shutil
import subprocess
import sys

DEFAULT_CONFIG_NAME = ".r3e-coach.json"


class BridgeError(Exception):
    pass


def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise BridgeError(f"Config nicht lesbar ({path}): {exc}")
    except json.JSONDecodeError as exc:
        raise BridgeError(f"Config ist kein gültiges JSON ({path}): {exc}")
    if not isinstance(data, dict):
        raise BridgeError(f"Config muss ein JSON-Objekt sein ({path})")
    return data


def find_config(explicit):
    if explicit:
        return explicit
    if os.path.isfile(DEFAULT_CONFIG_NAME):
        return DEFAULT_CONFIG_NAME
    return None


def resolve_exe(explicit, config):
    exe = explicit or config.get("bridge_exe")
    if not exe:
        raise BridgeError(
            "Kein Bridge-Exe bekannt — bitte --exe angeben oder \"bridge_exe\" in der Config setzen.")
    if not (os.path.isfile(exe) or shutil.which(exe)):
        raise BridgeError(f"Bridge-Exe nicht gefunden: {exe}")
    return exe


def resolve_args(explicit_args, config):
    if explicit_args is not None:
        args = list(explicit_args)
    else:
        args = list(config.get("bridge_args", []))
    if args and args[0] == "--":
        args = args[1:]
    return args


class BridgeProcess:
    def __init__(self, exe, args=(), cwd=None):
        self.exe = exe
        self.args = list(args)
        self.cwd = cwd
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen([self.exe, *self.args], cwd=self.cwd)
        return self.proc

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout=5.0):
        if self.proc is None or self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


MESSAGES = {
    "started": {"de": "Bridge gestartet (PID {pid}): {cmd}", "en": "Bridge started (PID {pid}): {cmd}"},
    "stopped": {"de": "Bridge wird beendet …", "en": "Stopping bridge …"},
    "exited": {"de": "Bridge beendet sich selbst (Exit-Code {rc}).", "en": "Bridge exited on its own (exit code {rc})."},
    "hint": {"de": "Strg+C beendet die Bridge kontrolliert. Zum Fahren RaceRoom starten und in MoTeC i2 loggen.",
             "en": "Press Ctrl+C to stop the bridge cleanly. Start RaceRoom and log in MoTeC i2 while driving."},
}


def _msg(key, lang, **kwargs):
    text = MESSAGES[key][lang]
    return text.format(**kwargs) if kwargs else text


def run_bridge(exe, args=(), cwd=None, lang="de", out=None):
    out = out if out is not None else sys.stdout
    bp = BridgeProcess(exe, args, cwd)
    bp.start()
    cmd = " ".join([exe, *args])
    print(_msg("started", lang, pid=bp.proc.pid, cmd=cmd), file=out)
    print(_msg("hint", lang), file=out)
    try:
        rc = bp.proc.wait()
    except KeyboardInterrupt:
        print(_msg("stopped", lang), file=out)
        bp.stop()
        return 0
    print(_msg("exited", lang, rc=rc), file=out)
    return rc
