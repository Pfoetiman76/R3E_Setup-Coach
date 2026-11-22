"""Regressionstests für 0.9.3.3: SHM-Öffnung wie PitBoss R3E.

Marcel bestätigte (22.11.2026): PitBoss R3E liest die RaceRoom-Daten
auf demselben Rechner problemlos, während Setup-Coach unterbrechungsfrei
"SHM NICHT GEFUNDEN" meldete. PitBoss R3E öffnet das Mapping per
OpenFileMappingW (NUR LESAN, nie anlegen); Setup-Coach nutzte dagegen
Pythons mmap-Mechanik (CreateFileMapping). 0.9.3.3 übernimmt wörtlich
die bewährte Öffnungsart, inklusive VirtualQuery für die Sichtgröße.
"""

import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent
       / "r3e_coach" / "r3e_shared.py").read_text(encoding="utf-8")


def test_open_uses_openfilemapping_readonly():
    """Öffnet per OpenFileMappingW mit FILE_MAP_READ — wie PitBoss R3E."""
    assert "OpenFileMappingW" in SRC
    assert "FILE_MAP_READ" in SRC
    assert "MapViewOfFile" in SRC


def test_never_creates_own_mapping():
    """Pythons mmap-Mechanik (CreateFileMapping) ist entfernt — der Coach
    kann kein eigenes Mapping unter dem Spiel-Namen anlegen."""
    assert "mmap.mmap(" not in SRC


def test_bare_name_first_then_local_then_global():
    """Reihenfolge: nackter Name zuerst (Standard der Sitzung), danach
    explizite Präfixe."""
    m = re.search(r"for tag in \(([^)]*)\)", SRC)
    assert m, "Kandidaten-Schleife fehlt"
    parts = [p.strip() for p in m.group(1).split(",")]
    assert parts == ["self._name", 'f"Local\\\\{self._name}"',
                     'f"Global\\\\{self._name}"']


def test_view_size_via_virtualquery():
    """Sichtgröße wird über VirtualQuery ermittelt (MEMORY_BASIC_INFORMATION)."""
    assert "_MemoryBasicInformation" in SRC
    assert "VirtualQuery" in SRC
    assert "RegionSize" in SRC


def test_close_releases_view_and_handle():
    """close() blendet die Sicht aus UND schließt das Handle."""
    assert "UnmapViewOfFile" in SRC
    assert "CloseHandle" in SRC
    #close gibt Map-Handle und Kernel-DLL-Referenz frei
    assert "self._map_handle = None" in SRC


def test_read_frame_pads_short_view():
    """read_frame: kürzere Sicht wird auf Struct-Größe mit Nullen gepolstert."""
    assert 'self._map is not None and self._map_handle is not None' in SRC
    assert 'buf + b"\\x00" * (want - len(buf))' in SRC
