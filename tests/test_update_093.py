"""Regressionstests für 0.9.3.

Zwei Bestätigte Defekte aus Marcels coach-diagnose.txt (22.11.2026):

A) Shared Memory wurde während einer ~8-Minuten-Fahrt dauerhaft nicht
   gefunden ("SHM NICHT GEFUNDEN", nie "SHM GEÖFFNET") — die Tags `Local\\$R3E`
   und `$R3E` reichten dafür nicht aus. 0.9.3 probiert zusätzlich den
   globalen Namensraum `Global\\$R3E` und protokolliert den gefundenen Tag.

B) Die Zielordner-Einstellung (recordings_dir) stand nach dem 0.9.2-
   Auto-Update wieder auf dem Standard, ohne dass der Nutzer etwas
   umstellte — die xcopy-/EXCLUDE-Sicherung der Config versagt offenbar
   auf Marcels Rechner. 0.9.3 sichert die geschützten Dateien zusätzlich
   nach %TEMP% und holt sie nach dem Kopieren zurück.
"""

import os
import re
from pathlib import Path

from r3e_coach.updater import PROTECTED_FILES, build_swap_cmd


def _src(name):
    here = Path(__file__).resolve().parent.parent
    return (here / "r3e_coach" / name).read_text(encoding="utf-8")


def test_r3e_shared_tries_global_namespace():
    """0.9.3 A: Global-Tag gehört zu den Kandidaten für mmap."""
    src = _src("r3e_shared.py")
    assert 'Local\\\\{self._name}' in src
    assert 'Global\\\\{self._name}' in src
    # Drei Kandidaten in fester Reihenfolge: Local, trivial, Global.
    m = re.search(r"for tag in \(([^)]*)\)", src)
    assert m, "Kandidaten-Schleife fehlt"
    parts = [p.strip() for p in m.group(1).split(",")]
    assert len(parts) == 3


def test_r3e_shared_records_tag_used():
    """0.9.3 A: gefundener Tag wird an tag_used gemeldet (für Diagnose)."""
    src = _src("r3e_shared.py")
    assert "self.tag_used = tag" in src
    assert "self.tag_used = None" in src


def test_recorder_logs_mapping_tag():
    """0.9.3 A: diagnose-Zeile nennt den Mapping-Namensraum."""
    src = _src("recorder.py")
    assert 'SHM GEÖFFNET — RaceRoom-Schnittstelle gefunden (Mapping: {tag})' in src
    assert 'getattr(self.memory, "tag_used", None)' in src


def test_swap_cmd_backs_up_protected_files(tmp_path):
    """0.9.3 B: Batch sichert Nutzerdaten nach %TEMP% und holt sie zurück."""
    staging = str(tmp_path / "app.update")
    os.makedirs(staging)
    app = str(tmp_path / "app")
    os.makedirs(app)
    cmd = build_swap_cmd(app, staging)
    keep = "%TEMP%\\r3e-coach-keep"
    # Vorbereitung: Keep-Ordner anlegen (mit Aufräumen eines alten Versuchs)
    assert f'if exist "{keep}" rmdir /S /Q "{keep}"' in cmd
    assert f'mkdir "{keep}"' in cmd
    xcopy = next(line for line in cmd.splitlines() if line.startswith("xcopy"))
    for name in PROTECTED_FILES:
        # Sicherung VOR dem Warten/Kopieren ...
        backup = [l for l in cmd.splitlines()
                  if f'copy /Y "{app}\\{name}" "{keep}\\{name}"' in l]
        assert backup, f"Sicherungszeile für {name} fehlt"
        assert cmd.index(backup[0]) < cmd.index(xcopy)
        # ... und Zurückholen NACH xcopy.
        restore = [l for l in cmd.splitlines()
                   if f'copy /Y "{keep}\\{name}" "{app}\\{name}"' in l]
        assert restore, f"Rückholzeile für {name} fehlt"
        assert cmd.index(restore[0]) > cmd.index(xcopy)
        # Vorhandene Dateien werden nur gesichert/gelöscht, nicht überschrieben
        assert f'if exist "{app}\\{name}"' in cmd
    # Aufräumen des Keep-Ordners im Erfolgsweg und im Abbruchweg
    assert cmd.count(f'rmdir /S /Q "{keep}"') >= 2


def test_swap_cmd_ascii_only(tmp_path):
    """Batch bleibt ASCII-kodierbar (prepare_update schreibt ascii)."""
    staging = str(tmp_path / "app.update")
    os.makedirs(staging)
    app = str(tmp_path / "app")
    os.makedirs(app)
    cmd = build_swap_cmd(app, staging)
    cmd.encode("ascii")


def test_workflows_ship_no_default_config():
    """0.9.3 B: Das Build bündelt keine .r3e-coach.json mehr."""
    here = Path(__file__).resolve().parent.parent
    for rel in (".github/workflows/release.yml", ".github/workflows/build-exe.yml",
                "scripts/build_exe.bat"):
        p = here / rel
        if p.is_file():
            assert "--add-data \".r3e-coach.json;.\"" not in \
                p.read_text(encoding="utf-8")
