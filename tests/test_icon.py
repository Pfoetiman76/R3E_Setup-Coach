import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(REPO, "tools", "gen_icon.py")


def _generate(out, extra):
    subprocess.run([sys.executable, GEN, "--out", str(out)] + extra,
                   check=True, capture_output=True, text=True)


def test_gen_icon_creates_valid_ico(tmp_path):
    _generate(tmp_path, ["--sizes", "16,32", "--png", "0"])
    ico = tmp_path / "app.ico"
    assert ico.is_file()
    data = ico.read_bytes()
    assert data[:4] == b"\x00\x00\x01\x00"          # ICO-Magic
    assert int.from_bytes(data[4:6], "little") == 2  # zwei Eintraege


def test_gen_icon_creates_valid_png(tmp_path):
    _generate(tmp_path, ["--sizes", "16", "--png", "32"])
    png = tmp_path / "logo-32.png"
    assert png.is_file()
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
