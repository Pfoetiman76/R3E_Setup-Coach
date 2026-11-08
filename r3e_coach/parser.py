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


def parse_motec_csv(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        lines = fh.read().splitlines()
    section = None
    channel_rows = []
    data_rows = []
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
    if channel_rows and normalize(channel_rows[0][0] if channel_rows[0] else "") == "name":
        channel_rows = channel_rows[1:]
    if channel_rows:
        names = [r[0] if r else "" for r in channel_rows]
        units = [r[1] if len(r) > 1 else "" for r in channel_rows]
        rows = data_rows
    elif loose:
        names = loose[0]
        units = [""] * len(names)
        rows = loose[1:]
    else:
        names, units, rows = [], [], []
    n = len(names)
    parsed = []
    for r in rows:
        row = [_to_float(c) for c in r[:n]]
        row += [None] * (n - len(row))
        parsed.append(row)
    return Session(names, units, parsed, source=path)
