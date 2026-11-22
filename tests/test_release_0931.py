"""Regressionstests für 0.9.3.1: vierstellige Version + automatischer Release.

Marcels Vorgaben (22.11.2026, "wie bei PitBoss"):
1. Ab sofort vierstellige Versionen vx.y.z.w mit fortlaufendem Build-Zähler.
2. Der Release-Workflow legt Tag und Release SELBST an, sobald main eine
   neue Version enthält — keine manuellen Klicks für Marcel mehr.
"""

import re
from pathlib import Path

from r3e_coach.updater import parse_version, is_newer

ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_parse_version_four_segments():
    """v0.9.3.1 wird als 4er-Tupel gelesen (Updater bleibt kompatibel)."""
    assert parse_version("v0.9.3.1") == (0, 9, 3, 1)
    assert parse_version("0.9.3.1") == (0, 9, 3, 1)
    assert parse_version("v0.9.3") == (0, 9, 3)
    assert parse_version("kaputt") == ()


def test_is_newer_comparable_with_build_counter():
    """Vergleich klappt über Segmentlängen hinweg (Padding mit Nullen)."""
    assert is_newer("v0.9.3.1", "0.9.3") is True
    assert is_newer("v0.9.3", "0.9.3.1") is False
    assert is_newer("v0.9.3.2", "0.9.3.1") is True
    assert is_newer("v0.9.4.0", "0.9.3.9") is True
    assert is_newer("v0.9.3.1", "0.9.3.1") is False


def test_version_four_part_everywhere():
    """pyproject, __init__ und setup.iss tragen dieselbe 4-stellige Version."""
    pyproject = _read("pyproject.toml")
    init = _read("r3e_coach/__init__.py")
    iss = _read("installer/setup.iss")
    m = re.search(r'version = "(\d+\.\d+\.\d+\.\d+)"', pyproject)
    assert m, "pyproject enthält keine 4-stellige Version"
    v = m.group(1)
    assert f'__version__ = "{v}"' in init
    assert f'#define MyAppVersion "{v}"' in iss


def test_auto_release_workflow_exists_and_self_builds():
    """auto-release.yml: baut Assets selbst und legt Tag+Release selbst an."""
    p = ROOT / ".github" / "workflows" / "auto-release.yml"
    assert p.is_file(), "auto-release.yml fehlt"
    y = _read(".github/workflows/auto-release.yml")
    # Trigger: push auf main
    assert "branches: [main]" in y
    # Version aus pyproject; nur wenn Release-Tag fehlt (Guard-Flag)
    assert "exists" in y
    assert "steps.ver.outputs.exists == 'false'" in y
    # Eigenständiger Build statt Kette (Workflow-Tags triggern keine Workflows)
    assert "pyinstaller --onedir" in y
    assert "iscc" in y or "build-installer.ps1" in y or "innosetup" in y
    # Tag + Release automatisch mit Version aus pyproject
    assert "softprops/action-gh-release@v2" in y
    assert "v${{ steps.ver.outputs.version }}" in y
    # gleiche Assets wie der alte manuelle Weg
    for asset in ("R3E-Setup-Coach-win.zip", "SHA256.txt",
                  "R3E-Setup-Coach-Setup.exe", "SHA256-Setup.txt"):
        assert asset in y


def test_updater_still_full_asset_list():
    """Guard gegen versehentliche Asset-Umbenennung: Updater findet das Zip."""
    y = _read(".github/workflows/auto-release.yml")
    assert "R3E-Setup-Coach-win.zip" in y
