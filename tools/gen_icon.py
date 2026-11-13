#!/usr/bin/env python3
"""Erzeugt das App-Icon (assets/app.ico), ein PNG (assets/app.png, 256 px,
als Fenster-Icon für die GUI) und ein PNG (assets/logo-512.png) aus der
freigegebenen Logo-Geometrie — pure Standardbibliothek, keine Abhaengigkeiten.

Hintergrund app.png: Das ICO enthält PNG-komprimierte Einträge (Windows
akzeptiert das für Exe/Verknüpfung), aber Qt kann PNG-Einträge in ICO-Dateien
nicht lesen — das Fenster-/Taskleisten-Icon lädt daher die PNG-Datei.

Geometrie (512er Grundflaeche, final freigegeben von Marcel, 12.11.2026):
- dunkler Grund #1c1c1e, abgerundete Ecken, dezenter Rand
- weisses Rennrad (Reifen/Felge/Speichen/Nabe)
- klassischer Doppelmaulschluessel (#e8212b), diagonal, beide Maeuler offen

Aufruf: python tools/gen_icon.py [--out assets] [--sizes 16,24,32,48,64,128,256] [--png 512]
"""
import argparse
import math
import os
import struct
import zlib

BG = (28, 28, 30)
BORDER = (42, 42, 45)
WHITE = (230, 230, 232)
RED = (232, 33, 43)
SS = 4  # Supersampling-Faktor


def _render(size):
    """Rendert das Icon in der Zielgroesse (Antialiasing per Supersampling)."""
    S = size * SS
    scale = S / 512.0

    def P(v):
        return v * scale

    R = P(96)
    C = P(256)
    rot_a = -math.radians(45)

    def in_bg(x, y):
        cx = min(max(x, R), S - R)
        cy = min(max(y, R), S - R)
        return math.hypot(x - cx, y - cy) <= R

    def in_border(x, y):
        cx = min(max(x, R), S - R)
        cy = min(max(y, R), S - R)
        d = math.hypot(x - cx, y - cy)
        return d <= R and d >= R - P(4)

    def in_wheel(x, y):
        r = math.hypot(x - C, y - C)
        if (P(118) <= r <= P(136)) or (P(86) <= r <= P(100)) or r <= P(24):
            return True
        if r <= P(110):  # Speichen (4 Stueck, 0/90/180/270 Grad)
            for k in range(4):
                a = math.radians(90 + k * 90)
                x1, y1 = C + P(24) * math.cos(a), C + P(24) * math.sin(a)
                x2, y2 = C + P(93) * math.cos(a), C + P(93) * math.sin(a)
                vx, vy = x2 - x1, y2 - y1
                wx, wy = x - x1, y - y1
                t = max(0.0, min(1.0, (wx * vx + wy * vy) / (vx * vx + vy * vy)))
                if math.hypot(x - (x1 + t * vx), y - (y1 + t * vy)) <= P(8):
                    return True
        return False

    def rot(x, y):
        dx, dy = x - C, y - C
        return (C + dx * math.cos(rot_a) - dy * math.sin(rot_a),
                C + dx * math.sin(rot_a) + dy * math.cos(rot_a))

    def in_wrench(x, y):
        if P(176) <= y <= P(336) and abs(x - C) <= P(14):
            return True
        for head_cy, jaw_cy in ((P(162), P(158)), (P(350), P(354))):
            if math.hypot(x - C, y - head_cy) <= P(30):
                if head_cy == P(162):
                    cut = (y <= jaw_cy and abs(x - C) <= P(13)) or \
                        math.hypot(x - C, y - jaw_cy) <= P(15)
                else:
                    cut = (y >= jaw_cy and abs(x - C) <= P(13)) or \
                        math.hypot(x - C, y - jaw_cy) <= P(15)
                if not cut:
                    return True
        return False

    buf = bytearray(S * S * 3)
    for y in range(S):
        for x in range(S):
            px, py = x + 0.5, y + 0.5
            c = BG
            if in_border(px, py):
                c = BORDER
            if in_wheel(px, py):
                c = WHITE
            lx, ly = rot(px, py)
            if in_wrench(lx, ly):
                c = RED
            i = (y * S + x) * 3
            buf[i:i + 3] = bytes(c)

    out = bytearray(size * size * 3)
    n = SS * SS
    for y in range(size):
        for x in range(size):
            r = g = b = 0
            base = (y * SS) * S + x * SS
            for dy in range(SS):
                row = base + dy * S
                for dx in range(SS):
                    i = (row + dx) * 3
                    r += buf[i]; g += buf[i + 1]; b += buf[i + 2]
            i = (y * size + x) * 3
            out[i:i + 3] = bytes((r // n, g // n, b // n))
    return bytes(out)


def png_bytes(data, size):
    raw = b''.join(b'\x00' + data[y * size * 3:(y + 1) * size * 3] for y in range(size))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + \
            struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))


def render_png(size):
    return png_bytes(_render(size), size)


def render_ico(sizes):
    """ICO-Container mit PNG-Eintraegen (Windows Vista+)."""
    entries = b''
    data = b''
    offset = 6 + 16 * len(sizes)
    for s in sizes:
        d = render_png(s)
        w = 0 if s >= 256 else s
        entries += struct.pack('<BBBBHHII', w, w, 0, 0, 1, 32, len(d), offset)
        data += d
        offset += len(d)
    return struct.pack('<HHH', 0, 1, len(sizes)) + entries + data


def main():
    ap = argparse.ArgumentParser(description="App-Icon aus Logo-Geometrie erzeugen")
    ap.add_argument("--out", default="assets", help="Zielordner (Default: assets)")
    ap.add_argument("--sizes", default="16,24,32,48,64,128,256",
                    help="ICO-Groessen, Komma-separiert")
    ap.add_argument("--png", type=int, default=512, help="Logo-PNG-Groesse (0 = kein Logo-PNG)")
    ap.add_argument("--app-png", type=int, default=256,
                    help="Fenster-Icon-PNG-Groesse (0 = kein app.png)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    ico_path = os.path.join(args.out, "app.ico")
    with open(ico_path, "wb") as f:
        f.write(render_ico(sizes))
    print(f"geschrieben: {ico_path} ({len(sizes)} Groessen)")
    if args.app_png:
        app_png_path = os.path.join(args.out, "app.png")
        with open(app_png_path, "wb") as f:
            f.write(render_png(args.app_png))
        print(f"geschrieben: {app_png_path} ({args.app_png}x{args.app_png})")
    if args.png:
        png_path = os.path.join(args.out, "logo-%d.png" % args.png)
        with open(png_path, "wb") as f:
            f.write(render_png(args.png))
        print(f"geschrieben: {png_path}")


if __name__ == "__main__":
    main()