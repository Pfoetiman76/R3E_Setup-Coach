import argparse
import os
import sys

from .bridge import BridgeError, find_config, load_config, resolve_args, resolve_exe, run_bridge
from .parser import parse_motec_csv
from .report import finding_dicts, render_json, render_text
from .rules import Ctx, analyze
from .store import add_analysis, default_store_path, entry_key, list_keys, load, save


def _add_common(p):
    p.add_argument("--config", help="Pfad zur JSON-Config (Standard: ./.r3e-coach.json, falls vorhanden)")
    p.add_argument("--lang", choices=["de", "en"], default="de", help="Ausgabesprache (Standard: de)")


def _add_store_args(p):
    p.add_argument("--store", help="Pfad zur setups.json (Standard: Anwendungsordner)")
    p.add_argument("--track", help="Streckenname (unverändert aus RaceRoom-Ergebnisdaten)")
    p.add_argument("--layout", help="Layout-Name (Standard: wie Strecke, falls RaceRoom kein eigenes Layout nennt)")
    p.add_argument("--vehicle", help="Fahrzeugname (unverändert aus RaceRoom-Ergebnisdaten)")


def build_parser():
    p = argparse.ArgumentParser(
        prog="r3e-coach",
        description="R3E Setup-Coach: MoTeC-i2-CSV analysieren, Setups verwalten und/oder Bridge-Exe (RaceRoom → MoTeC) steuern.",
    )
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("analyze", help="MoTeC-i2-CSV analysieren (Standard, wenn nur eine Datei übergeben wird)")
    _add_common(a)
    a.add_argument("csv", help="Pfad zum MoTeC-i2-CSV-Export")
    a.add_argument("--min-speed", type=float, default=40.0,
                   help="Mindestgeschwindigkeit in km/h für relevante Fahrmanöver (Standard: 40)")
    a.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")
    _add_store_args(a)
    a.add_argument("--save", action="store_true",
                   help="Analyse unter 'track|layout|vehicle' in setups.json speichern (erfordert --track und --vehicle)")

    s = sub.add_parser("setups", help="Gespeicherte Setups auflisten (setups.json)")
    _add_common(s)
    _add_store_args(s)
    s.add_argument("--key", help="Nur diesen Eintrag zeigen (Format 'track|layout|vehicle')")
    s.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")

    b = sub.add_parser("bridge", help="Bridge-Exe starten, das RaceRoom-Daten an MoTeC liefert, und per Strg+C stoppen")
    _add_common(b)
    b.add_argument("--exe", help="Pfad zur Bridge-Exe (oder \"bridge_exe\" in der Config)")
    b.add_argument("--cwd", help="Arbeitsverzeichnis für die Bridge (oder \"bridge_cwd\" in der Config)")
    b.add_argument("--args", nargs=argparse.REMAINDER,
                   help="Argumente für die Bridge, z. B. --args -- --port 5566")

    g = sub.add_parser("gui", help="Grafische Oberfläche starten (PySide6)")
    _add_common(g)

    u = sub.add_parser("update", help="Auf neues GitHub-Release prüfen und herunterladen")
    _add_common(u)
    u.add_argument("--check", action="store_true", help="Nur prüfen, nicht herunterladen")

    t_ = sub.add_parser("times", help="Best-/Ø-Zeiten aus results.db von R3E-Resultate (nur lesend)")
    _add_common(t_)
    t_.add_argument("--db", help="Pfad zur results.db (Standard: Dokumente\\RaceRoom Results Companion\\results.db)")
    t_.add_argument("--track", help="Streckenname (leer lassen für alle Kombinationen)")
    t_.add_argument("--layout", help="Layout-Name (Standard: wie Strecke)")
    t_.add_argument("--vehicle", help="Fahrzeugname")
    t_.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")
    return p


def _run_analyze(args):
    session = parse_motec_csv(args.csv)
    findings = analyze(session, Ctx(min_speed=args.min_speed))
    if args.json:
        print(render_json(findings, session, lang=args.lang))
    else:
        print(render_text(findings, session, lang=args.lang))
    if args.save:
        if not args.track or not args.vehicle:
            print("Fehler: --save erfordert --track und --vehicle (und optional --layout).", file=sys.stderr)
            return 2
        key = entry_key(args.track, args.layout, args.vehicle)
        store_path = args.store or default_store_path()
        data = load(store_path)
        record = add_analysis(data, key, {
            "csv_source": os.path.abspath(args.csv),
            "samples": len(session),
            "findings": finding_dicts(findings),
        })
        save(data, store_path)
        print(f"Gespeichert unter '{key}' ({len(record['findings'])} Fundstellen) → {store_path}")
    return 0


def _run_setups(args):
    store_path = args.store or default_store_path()
    data = load(store_path)
    keys = list_keys(data)
    if args.key:
        if args.key not in data["setups"]:
            print(f"Fehler: Kein Eintrag '{args.key}' in {store_path}", file=sys.stderr)
            return 2
        if args.json:
            import json
            print(json.dumps({args.key: data["setups"][args.key]}, ensure_ascii=False, indent=2))
        else:
            _print_entry(args.key, data["setups"][args.key], store_path)
        return 0
    if args.json:
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if not keys:
        print(f"Noch keine Setups gespeichert ({store_path}).")
        return 0
    print(f"Gespeicherte Setups ({len(keys)}) — {store_path}:")
    for key in keys:
        entry = data["setups"][key]
        target = entry.get("target_lap_ms")
        target_s = f"{target / 1000:.3f} s" if isinstance(target, (int, float)) else "—"
        updated = entry.get("updated_at") or "—"
        analyses = len(entry.get("analyses", []))
        print(f"  {key} · Ziel {target_s} · Analysen {analyses} · aktualisiert {updated}")
    return 0


def _print_entry(key, entry, store_path):
    target = entry.get("target_lap_ms")
    target_s = f"{target / 1000:.3f} s" if isinstance(target, (int, float)) else "—"
    print(f"Setup '{key}' — {store_path}")
    print(f"  Zielzeit: {target_s}")
    if entry.get("reference_session"):
        print(f"  Bezugs-Session: {entry['reference_session']}")
    if entry.get("notes"):
        print(f"  Notizen: {entry['notes']}")
    chassis = entry.get("chassis") or {}
    tires = entry.get("tires") or {}
    vals = ", ".join(f"{k}={v}" for k, v in chassis.items() if v is not None)
    if vals:
        print(f"  Fahrwerk: {vals}")
    vals = ", ".join(f"{k}={v}" for k, v in tires.items() if v is not None)
    if vals:
        print(f"  Reifen: {vals}")
    for i, a in enumerate(entry.get("analyses", []), 1):
        stamp = a.get("analyzed_at") or "?"
        applied = a.get("applied")
        state = {True: "umgesetzt", False: "verworfen", None: "offen"}[applied]
        print(f"  Analyse {i} ({stamp}, {a.get('samples', '?')} Samples, {state}): {a.get('csv_source', '?')}")
        for f in a.get("findings", []):
            print(f"    [{f.get('severity', '?').upper()}] {f.get('text', '')}")
    for h in entry.get("history", []):
        print(f"  Historie {h.get('changed_at')}: {h.get('change', '')}"
              + (f" — {h['observed']}" if h.get("observed") else ""))


def _run_times(args):
    from .queries import combos, connect, db_exists, default_db_path, lap_stats
    db = args.db or default_db_path()
    if not db_exists(db):
        print(f"Hinweis: results.db nicht gefunden ({db}) — "
              "erst R3E-Resultate starten, damit die Datenbank entsteht.")
        return 0
    if not args.track and not args.vehicle:
        with connect(db) as conn:
            rows = combos(conn)
        if args.json:
            import json
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("Noch keine Zeiten in results.db.")
            return 0
        print(f"Bekannte Kombinationen ({len(rows)}) — {db}:")
        for c in rows:
            best = f"{c['best_ms'] / 1000:.3f} s" if c.get("best_ms") else "—"
            print(f"  {c['track']}|{c['layout']}|{c['vehicle']} · Best {best}")
        return 0
    if not args.track or not args.vehicle:
        print("Fehler: --track und --vehicle zusammen angeben (oder beide weglassen).", file=sys.stderr)
        return 2
    layout = args.layout or args.track
    with connect(db) as conn:
        stats = lap_stats(conn, args.track, layout, args.vehicle)
    if stats is None:
        print(f"Keine Daten für '{args.track}|{layout}|{args.vehicle}'.")
        return 0
    if args.json:
        import json
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0
    best = f"{stats['best_ms'] / 1000:.3f} s" if stats["best_ms"] else "—"
    avg = f"{stats['avg_ms'] / 1000:.3f} s" if stats["avg_ms"] else "—"
    print(f"Zeiten für '{args.track}|{layout}|{args.vehicle}' — {db}:")
    print(f"  Bestzeit: {best} · Ø: {avg} · Runden: {stats['n_laps']} · Sitzungen: {stats['n_sessions']}")
    return 0


def _run_bridge(args):
    config = {}
    cfg_path = find_config(args.config)
    if cfg_path:
        config = load_config(cfg_path)
    exe = resolve_exe(args.exe, config)
    bridge_args = resolve_args(args.args, config)
    cwd = args.cwd or config.get("bridge_cwd")
    if cwd and not os.path.isdir(cwd):
        raise BridgeError(f"Arbeitsverzeichnis existiert nicht: {cwd}")
    return run_bridge(exe, bridge_args, cwd=cwd, lang=args.lang)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("analyze", "setups", "bridge", "gui", "update", "times"):
        args = build_parser().parse_args(argv)
    else:
        args = build_parser().parse_args(["analyze", *argv])
    try:
        if args.command == "bridge":
            return _run_bridge(args)
        if args.command == "setups":
            return _run_setups(args)
        if args.command == "gui":
            from .gui import main_gui
            main_gui(lang=args.lang)
            return 0
        if args.command == "update":
            from .updater import run_update
            return run_update(lang=args.lang, check_only=args.check)
        if args.command == "times":
            return _run_times(args)
        return _run_analyze(args)
    except BridgeError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"Fehler: Datei nicht gefunden: {exc.filename or exc}", file=sys.stderr)
        return 2