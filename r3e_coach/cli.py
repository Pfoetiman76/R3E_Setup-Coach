import argparse
import sys

from .bridge import BridgeError, find_config, load_config, resolve_args, resolve_exe, run_bridge
from .parser import parse_motec_csv
from .report import render_json, render_text
from .rules import Ctx, analyze


def _add_common(p):
    p.add_argument("--config", help="Pfad zur JSON-Config (Standard: ./.r3e-coach.json, falls vorhanden)")
    p.add_argument("--lang", choices=["de", "en"], default="de", help="Ausgabesprache (Standard: de)")


def build_parser():
    p = argparse.ArgumentParser(
        prog="r3e-coach",
        description="R3E Setup-Coach: MoTeC-i2-CSV analysieren und/oder Bridge-Exe (RaceRoom → MoTeC) verwalten.",
    )
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("analyze", help="MoTeC-i2-CSV analysieren (Standard, wenn nur eine Datei übergeben wird)")
    _add_common(a)
    a.add_argument("csv", help="Pfad zum MoTeC-i2-CSV-Export")
    a.add_argument("--min-speed", type=float, default=40.0,
                   help="Mindestgeschwindigkeit in km/h für relevante Fahrmanöver (Standard: 40)")
    a.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")

    b = sub.add_parser("bridge", help="Bridge-Exe starten, das RaceRoom-Daten an MoTeC liefert, und per Strg+C stoppen")
    _add_common(b)
    b.add_argument("--exe", help="Pfad zum Bridge-Exe (oder \"bridge_exe\" in der Config)")
    b.add_argument("--cwd", help="Arbeitsverzeichnis für die Bridge (oder \"bridge_cwd\" in der Config)")
    b.add_argument("--args", nargs=argparse.REMAINDER,
                   help="Argumente für die Bridge, z. B. --args -- --port 5566")
    return p


def _run_analyze(args):
    session = parse_motec_csv(args.csv)
    findings = analyze(session, Ctx(min_speed=args.min_speed))
    if args.json:
        print(render_json(findings, session, lang=args.lang))
    else:
        print(render_text(findings, session, lang=args.lang))
    return 0


def _run_bridge(args):
    config = {}
    cfg_path = find_config(args.config)
    if cfg_path:
        config = load_config(cfg_path)
    exe = resolve_exe(args.exe, config)
    bridge_args = resolve_args(args.args, config)
    cwd = args.cwd or config.get("bridge_cwd")
    return run_bridge(exe, bridge_args, cwd=cwd, lang=args.lang)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("analyze", "bridge"):
        args = build_parser().parse_args(argv)
    else:
        args = build_parser().parse_args(["analyze", *argv])
    try:
        if args.command == "bridge":
            return _run_bridge(args)
        return _run_analyze(args)
    except BridgeError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"Fehler: Datei nicht gefunden: {exc.filename or exc}", file=sys.stderr)
        return 2
