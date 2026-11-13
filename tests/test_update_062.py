import os

import pytest

from r3e_coach.updater import build_swap_cmd


def test_build_swap_cmd_hardened(tmp_path):
    staging = str(tmp_path / "app.update")
    os.makedirs(staging)
    app = str(tmp_path / "app")
    os.makedirs(app)
    cmd = build_swap_cmd(app, staging)
    exe = "R3E-Setup-Coach.exe"
    old = os.path.join(app, exe + ".old")  # wie im Batch (os.path.join)
    # Altlasten (.old aus abgebrochenem Versuch) werden zu Beginn beseitigt,
    # sonst hängt die ren-Warteschleife fuer immer.
    assert f'del "{old}"' in cmd
    # Warteschleife mit Obergrenze (120 s), kein Endlos-Hang
    assert "tries" in cmd and "goto wait" in cmd and "gtr 120" in cmd
    assert ":abort" in cmd
    # Fallback: ist nach dem Kopieren keine neue Exe da, wird die alte zurueckbenannt
    assert f'ren "{old}" "{exe}"' in cmd
    # Kern-Ablauf unveraltet
    assert ":wait" in cmd
    assert f'ren "{app}{os.sep}{exe}"' in cmd or f'ren "{app}\\{exe}"' in cmd
    assert f'xcopy "{staging}{os.sep}*" "{app}{os.sep}"' in cmd or \
        f'xcopy "{staging}\\*"' in cmd
    assert f'start "" "{app}{os.sep}{exe}"' in cmd or f'start "" "{app}\\{exe}"' in cmd
    assert "rmdir /S /Q" in cmd
    # Exclude-Liste schuetzt Nutzerdaten
    excl = open(os.path.join(staging, ".update-exclude"), encoding="ascii").read()
    assert ".r3e-coach.json" in excl
    assert "setups.json" in excl
    assert ".update-exclude" in excl
    # Batch ist ASCII-kodierbar (prepare_update schreibt encoding="ascii")
    cmd.encode("ascii")