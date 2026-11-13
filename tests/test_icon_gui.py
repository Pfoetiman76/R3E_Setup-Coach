import struct
import zlib

import pytest

pytest.importorskip("PySide6")

import r3e_coach.gui as gui
from r3e_coach.gui import _app_icon, _icon_candidates


def _tiny_png():
    """Minimales gueltiges 1x1-RGB-PNG."""
    raw = b"\x00" + b"\x00\x00\x00"

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + \
            struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def test_icon_candidates_prefer_png():
    cands = _icon_candidates()
    assert cands
    assert str(cands[0]).endswith("app.png")
    assert all(str(c).endswith(("app.png", "app.ico")) for c in cands)


def test_app_icon_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "_icon_candidates", lambda: [tmp_path / "app.png"])
    assert _app_icon() is None


def test_app_icon_loads_png(monkeypatch, tmp_path):
    p = tmp_path / "app.png"
    p.write_bytes(_tiny_png())
    monkeypatch.setattr(gui, "_icon_candidates", lambda: [p])
    icon = _app_icon()
    assert icon is not None
    assert not icon.isNull()


def test_app_icon_falls_back_to_readable_candidate(monkeypatch, tmp_path):
    bad = tmp_path / "a" / "app.png"
    bad.parent.mkdir()
    bad.write_bytes(b"kein bild")
    good = tmp_path / "b" / "app.png"
    good.parent.mkdir()
    good.write_bytes(_tiny_png())
    monkeypatch.setattr(gui, "_icon_candidates", lambda: [bad, good])
    icon = _app_icon()
    assert icon is not None
    assert not icon.isNull()