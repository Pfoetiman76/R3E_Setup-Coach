import csv
import re

from .channels import normalize
from .telemetry import Session

SECTION_RE = re.compile(r"^\[\s*([^\]]+?)\s*\]\s*$")


def _cells(line):
    delimiter = ";" if (";" in line and "," not in line) else "\t" if ("\t" in line and "," not in line and ";" not in line) else ","
    try:
        row = next(csv.reader([line], delimiter=delimiter))
    except csv.Error:
        return []
    return [c.strip() for c in row]


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_text(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def _is_number(text):
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False


def parse_motec_csv(path):
    lines = _read_text(path).splitlines()
    section = None
    channel_rows = []
    data_rows = []
    other_rows = []
    loose = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1).lower().lstrip("*")
            continue
        cells = _cells(line)
        if not cells:
            continue
        if section == "channel":
            channel_rows.append(cells)
        elif section == "data":
            data_rows.append(cells)
        elif section is None:
            loose.append(cells)
        else:
            other_rows.append(cells)
    if channel_rows and normalize(channel_rows[0][0] if channel_rows[0] else "") == "name":
        channel_rows = channel_rows[1:]
    if channel_rows:
        names = [r[0] if r else "" for r in channel_rows]
        units = [r[1] if len(r) > 1 else "" for r in channel_rows]
        rows = data_rows or other_rows
    elif loose:
        header_idx = None
        for i, cells in enumerate(loose):
            filled = [c for c in cells if c]
            if len(filled) >= 5 and all(not _is_number(c) for c in filled):
                header_idx = i
                break
        if header_idx is None:
            header_idx = 0
        names = loose[header_idx]
        rest = loose[header_idx + 1:]
        if rest and any(c for c in rest[0]) and all(not _is_number(c) for c in rest[0] if c):
            units = rest[0][:len(names)] + [""] * max(0, len(names) - len(rest[0]))
            rows = rest[1:]
        else:
            units = [""] * len(names)
            rows = rest
    else:
        names, units, rows = [], [], []
    n = len(names)
    parsed = []
    for r in rows:
        row = [_to_float(c) for c in r[:n]]
        row += [None] * (n - len(row))
        parsed.append(row)
    return Session(names, units, parsed, source=path)
