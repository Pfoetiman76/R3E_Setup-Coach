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


def pending_path(exe_path):
    return exe_path + ".new"


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
        "available": "Update verfügbar: {tag} ({name}) — wird beim nächsten Start installiert.",
        "none": "Du hast bereits die neueste Version ({version}).",
        "downloaded": "Update nach {dest} geladen. Beim nächsten Start wird es installiert.",
        "applied": "Update installiert: {path}",
        "error": "Update-Prüfung fehlgeschlagen: {err}",
    },
    "en": {
        "current": "Installed version: {version}",
        "latest": "Latest release: {tag}",
        "available": "Update available: {tag} ({name}) — will be installed on next start.",
        "none": "You already have the latest version ({version}).",
        "downloaded": "Update downloaded to {dest}. It will be installed on next start.",
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
    dest = pending_path(exe)
    try:
        download_update(info.url, dest)
    except Exception as exc:
        print(_msg(lang, "error", err=exc), file=out)
        return 1
    print(_msg(lang, "downloaded", dest=dest), file=out)
    return 0
