import argparse

from .parser import parse_motec_csv
from .report import render_json, render_text
from .rules import Ctx, analyze


def build_parser():
    p = argparse.ArgumentParser(
        prog="r3e-coach",
        description="Analysiert einen MoTeC-i2-CSV-Export und gibt Setup-Empfehlungen für RaceRoom (R3E).",
    )
    p.add_argument("csv", help="Pfad zum MoTeC-i2-CSV-Export")
    p.add_argument("--lang", choices=["de", "en"], default="de", help="Ausgabesprache (Standard: de)")
    p.add_argument("--min-speed", type=float, default=40.0,
                   help="Mindestgeschwindigkeit in km/h für relevante Fahrmanöver (Standard: 40)")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    session = parse_motec_csv(args.csv)
    findings = analyze(session, Ctx(min_speed=args.min_speed))
    if args.json:
        print(render_json(findings, session, lang=args.lang))
    else:
        print(render_text(findings, session, lang=args.lang))
    return 0
