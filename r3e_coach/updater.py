import json
import os
import re
import sys
import urllib.request

from . import __version__

REPO = "Pfoetiman76/R3E_Setup-Coach"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_HINT = "R3E-Setup-Coach"


class UpdateInfo:
    def __init__(self, tag, url, name):
        self.tag = tag
        self.url = url
        self.name = name


def parse_version(text):
    m = re.match(r"^v?(\d+(?:\.\d+)*)", str(text).strip())
    if not m:
        return ()
    return tuple(int(p) for p in m.group(1).split("."))


def is_newer(tag, current=None):
    current = __version__ if current is None else current
    new, old = parse_version(tag), parse_version(current)
    if not new:
        return False
    width = max(len(new), len(old))
    return new + (0,) * (width - len(new)) > old + (0,) * (width - len(old))


def _open(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "r3e-setup-coach", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_latest_release(timeout=10):
    with _open(API_LATEST, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_asset(release):
    assets = release.get("assets", [])
    for asset in assets:
        name = asset.get("name", "")
        if ASSET_HINT in name and name.lower().endswith(".zip"):
            return asset
    for asset in assets:
        name = asset.get("name", "")
        if ASSET_HINT in name and name.lower().endswith(".exe"):
            return asset
    return assets[0] if assets else None


def check_for_update(timeout=10):
    try:
        release = fetch_latest_release(timeout=timeout)
    except Exception:
        return None
    tag = release.get("tag_name", "")
    if not is_newer(tag):
        return None
    asset = find_asset(release)
    if asset is None:
        return None
    return UpdateInfo(tag, asset.get("browser_download_url", ""), asset.get("name", ""))


def download_update(url, dest, timeout=60):
    with _open(url, timeout=timeout) as resp, open(dest, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    return dest


def current_exe_path():
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    return None


def app_dir():
    """Installationsordner der App (onedir-Build) oder None."""
    exe = current_exe_path()
    return os.path.dirname(exe) if exe else None


def pending_path(exe_path):
    return exe_path + ".new"


# Dateien, die ein Update NIE überschreibt (Nutzerdaten im App-Ordner).
PROTECTED_FILES = (".r3e-coach.json", "setups.json")


def build_swap_cmd(app_dir, staging, exe_name="R3E-Setup-Coach.exe"):
    """Erzeugt den Batch-Inhalt, der nach App-Ende den Ordner tauscht.

    Der Batch beseitigt zuerst Altlasten (`.old` aus einem abgebrochenen
    früheren Versuch — sonst hängt die ren-Schleife für immer), wartet dann
    mit Obergrenze (120 Sekunden), bis die laufende Exe freigegeben ist,
    kopiert die neuen Dateien über den App-Ordner (ohne zu löschen,
    geschützte Nutzer- und Hilfsdateien ausgenommen), stellt die alte Exe
    im Fehlerfall zurück, startet die neue Version und räumt auf.
    """
    excl = os.path.join(staging, ".update-exclude")
    with open(excl, "w", encoding="ascii", newline="\r\n") as fh:
        for name in PROTECTED_FILES + (".update-exclude",):
            fh.write(name + "\r\n")
    old = os.path.join(app_dir, exe_name + ".old")
    return (
        "@echo off\r\n"
        f'del "{old}" >nul 2>&1\r\n'
        "set /a tries=0\r\n"
        ":wait\r\n"
        "set /a tries+=1\r\n"
        "if %tries% gtr 120 goto abort\r\n"
        f'ren "{app_dir}\\{exe_name}" "{exe_name}.old" >nul 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait\r\n"
        ")\r\n"
        f'xcopy "{staging}\\*" "{app_dir}\\" /E /Y /I /Q /EXCLUDE:{excl} >nul\r\n'
        f'if not exist "{app_dir}\\{exe_name}" (\r\n'
        f'  ren "{old}" "{exe_name}"\r\n'
        ")\r\n"
        f'del "{old}" >nul 2>&1\r\n'
        f'start "" "{app_dir}\\{exe_name}"\r\n'
        f'rmdir /S /Q "{staging}"\r\n'
        "exit /b 0\r\n"
        ":abort\r\n"
        f'echo Update abgebrochen: App-Ordner unveraendert. >nul 2>&1\r\n'
        "exit /b 1\r\n"
    )


def prepare_update(info, dest_dir=None, timeout=60):
    """Lädt das Release-ZIP und stellt das Update für den Neustart bereit.

    Onedir-Build: Das ZIP wird nach '<app_dir>\\..\\R3E-Setup-Coach.update'
    entpackt; ein Batch-Skript übernimmt den Tausch nach App-Ende.
    Rückgabe: Pfad des Batch-Skripts (ausgeführt starten + App beenden).
    """
    app = dest_dir or app_dir()
    if not app:
        raise RuntimeError("Kein App-Ordner (nicht als Exe gestartet).")
    staging = os.path.join(os.path.dirname(os.path.abspath(app)),
                           os.path.basename(os.path.abspath(app)) + ".update")
    if os.path.isdir(staging):
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)
    zdest = os.path.join(staging, "update.zip")
    download_update(info.url, zdest, timeout=timeout)
    import zipfile
    with zipfile.ZipFile(zdest) as zf:
        zf.extractall(staging)
    os.remove(zdest)
    cmd_path = os.path.join(os.path.abspath(app), "apply-update.cmd")
    with open(cmd_path, "w", encoding="ascii", newline="") as fh:
        fh.write(build_swap_cmd(os.path.abspath(app), staging))
    return cmd_path


def apply_pending_update(exe_path=None):
    exe_path = exe_path or current_exe_path()
    if not exe_path:
        return False
    pending = pending_path(exe_path)
    if not os.path.isfile(pending):
        return False
    old = exe_path + ".old"
    try:
        if os.path.isfile(exe_path):
            os.replace(exe_path, old)
        os.replace(pending, exe_path)
    except OSError:
        if os.path.isfile(old) and not os.path.isfile(exe_path):
            os.replace(old, exe_path)
        return False
    try:
        os.remove(old)
    except OSError:
        pass
    return True


UPDATE_MESSAGES = {
    "de": {
        "current": "Installierte Version: {version}",
        "latest": "Neueste Release: {tag}",
        "available": "Update verfügbar: {tag} ({name})",
        "none": "Du hast bereits die neueste Version ({version}).",
        "downloaded": "Update bereitgestellt — alter Prozess beendet sich, dann wird automatisch die neue Version gestartet.",
        "applied": "Update installiert: {path}",
        "error": "Update-Prüfung fehlgeschlagen: {err}",
    },
    "en": {
        "current": "Installed version: {version}",
        "latest": "Latest release: {tag}",
        "available": "Update available: {tag} ({name})",
        "none": "You already have the latest version ({version}).",
        "downloaded": "Update prepared — once this process exits, the new version starts automatically.",
        "applied": "Update installed: {path}",
        "error": "Update check failed: {err}",
    },
}


def _msg(lang, key, **kwargs):
    return UPDATE_MESSAGES[lang][key].format(**kwargs)


def run_update(lang="de", check_only=False, out=None):
    out = out if out is not None else sys.stdout
    exe = current_exe_path()
    if exe and apply_pending_update(exe):
        print(_msg(lang, "applied", path=exe), file=out)
    print(_msg(lang, "current", version=__version__), file=out)
    info = check_for_update()
    if info is None:
        print(_msg(lang, "none", version=__version__), file=out)
        return 0
    print(_msg(lang, "latest", tag=info.tag), file=out)
    print(_msg(lang, "available", tag=info.tag, name=info.name), file=out)
    if check_only or not exe:
        return 0
    try:
        cmd_path = prepare_update(info)
    except Exception as exc:
        print(_msg(lang, "error", err=exc), file=out)
        return 1
    _start_swap(cmd_path)
    print(_msg(lang, "downloaded"), file=out)
    return 0


def _start_swap(cmd_path):
    """Startet das Tausch-Batch entkoppelt (Windows); es wartet bis App-Ende."""
    if os.name != "nt":
        return
    import subprocess
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen(["cmd", "/c", cmd_path], close_fds=True,
                     creationflags=DETACHED_PROCESS)