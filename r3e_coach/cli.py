import argparse
import os
import sys

from .advice import build_advice
from .logdata import read_log, session_from_log
from .recorder import Recorder, default_recordings_dir
from .report import finding_dicts, render_json, render_text
from .rules import Ctx, analyze
from .setup_sheet import (build_sheet, default_sheets_dir, suggest_filename,
                          write_sheet)
from .store import (add_analysis, default_store_path, entry_key, get_entry,
                    list_keys, load, save)


def _add_common(p):
    p.add_argument("--config", help="Pfad zur JSON-Config (Standard: ./.r3e-coach.json, falls vorhanden)")
    p.add_argument("--lang", choices=["de", "en"], default="de", help="Ausgabesprache (Standard: de)")


def _add_store_args(p):
    p.add_argument("--store", help="Pfad zur setups.json (Standard: Anwendungsordner)")
    p.add_argument("--track", help="Streckenname (Standard: automatisch aus dem Log)")
    p.add_argument("--layout", help="Layout-Name (Standard: automatisch aus dem Log bzw. wie Strecke)")
    p.add_argument("--vehicle", help="Fahrzeugname (Standard: automatisch aus dem Log)")


def build_parser():
    p = argparse.ArgumentParser(
        prog="r3e-coach",
        description="R3E Setup-Coach: Telemetrie aus RaceRoom aufzeichnen (eigener Rekorder), analysieren und Setups verwalten.",
    )
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("analyze", help="Aufgezeichnete Coach-Logdatei analysieren (Standard, wenn nur eine Datei übergeben wird)")
    _add_common(a)
    a.add_argument("log", help="Pfad zur .coachlog-Aufzeichnung")
    a.add_argument("--min-speed", type=float, default=40.0,
                   help="Mindestgeschwindigkeit in km/h für relevante Fahrmanöver (Standard: 40)")
    a.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Text")
    _add_store_args(a)
    a.add_argument("--save", action="store_true",
                   help="Analyse unter 'track|layout|vehicle' in setups.json speichern")
    a.add_argument("--sheet", nargs="?", const="", default=None, metavar="DATEI",
                   help="Setup-Zettel (Garage-Checkliste) in DATEI schreiben (ohne DATEI: Standardordner mit Vorschlagsname)")

    r = sub.add_parser("record", help="Telemetrie aus RaceRoom aufzeichnen (eigener Rekorder, Strg+C beendet)")
    _add_common(r)
    r.add_argument("--hz", type=float, default=50.0, help="Abtastrate in Hz (Standard: 50)")
    r.add_argument("--out", help="Zielordner für .coachlog-Dateien (Standard: Dokumente\\R3E Setup-Coach\\recordings)")
    r.add_argument("--wait", action="store_true", help="Auf RaceRoom warten und automatisch mit der Aufzeichnung beginnen")

    s = sub.add_parser("setups", help="Gespeicherte Setups auflisten (setups.json)")
    _add_common(s)
    _add_store_args(s)
    s.add_argument("--key", help="Nur diesen Eintrag zeigen (Format 'track|layout|vehicle')")
    s.add_argument("--json", action="store_true", help="Ausgabe als JSON")

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
    t_.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    return p


def _stored_values(args):
    """0.7.0: gespeicherte Setup-Werte für track|layout|vehicle, falls vorhanden."""
    if not (getattr(args, "track", None) and getattr(args, "vehicle", None)):
        return None, None
    try:
        key = entry_key(args.track, args.layout, args.vehicle)
        entry = get_entry(load(args.store or default_store_path()), key)
    except (OSError, ValueError):
        return None, None
    if not entry:
        return None, None
    return entry.get("chassis") or None, entry.get("tires") or None


def _run_analyze(args):
    session = session_from_log(args.log)
    findings = analyze(session, Ctx(min_speed=args.min_speed))
    # Strecke/Fahrzeug: automatisch aus dem Log (Meta), außer überschrieben.
    meta, _, _, _ = read_log(args.log)
    track = args.track or (meta.get("track") or "").strip() or None
    vehicle = args.vehicle or (meta.get("vehicle") or "").strip() or None
    layout = args.layout or (meta.get("layout") or "").strip() or None
    _args_probe = argparse.Namespace(track=track, vehicle=vehicle, layout=layout,
                                     store=getattr(args, "store", None))
    chassis, tires = _stored_values(_args_probe)
    advice = build_advice(findings, chassis, tires)
    if args.json:
        print(render_json(findings, session, lang=args.lang, advice=advice))
    else:
        print(render_text(findings, session, lang=args.lang, advice=advice))
    if args.sheet is not None:
        sheet_text = build_sheet(
            {"track": track, "layout": layout, "vehicle": vehicle},
            advice, lang=args.lang, key=entry_key(track, layout, vehicle)
            if track and vehicle else None,
            log_source=os.path.abspath(args.log))
        sheet_path = args.sheet
        if not sheet_path:
            os.makedirs(default_sheets_dir(), exist_ok=True)
            sheet_path = os.path.join(
                default_sheets_dir(),
                suggest_filename({"track": track, "layout": layout, "vehicle": vehicle},
                                 lang=args.lang))
        write_sheet(sheet_path, sheet_text)
        print(f"Setup-Zettel geschrieben → {sheet_path}")
    if args.save:
        if not track or not vehicle:
            print("Fehler: --save erfordert Strecke und Fahrzeug (im Log vorhanden oder angegeben).", file=sys.stderr)
            return 2
        key = entry_key(track, layout, vehicle)
        store_path = args.store or default_store_path()
        data = load(store_path)
        record = add_analysis(data, key, {
            "log_source": os.path.abspath(args.log),
            "samples": len(session),
            "findings": finding_dicts(findings),
        })
        save(data, store_path)
        print(f"Gespeichert unter '{key}' ({len(record['findings'])} Fundstellen) → {store_path}")
    return 0


def _run_record(args):
    import threading
    import time as _time

    rec = Recorder(out_dir=args.out or default_recordings_dir(), hz=args.hz)
    print(f"Aufzeichnung startet ({args.hz:g} Hz) — Strg+C beendet und speichert.")
    print(f"Zielordner: {rec.out_dir}")
    thread = threading.Thread(target=rec.run, daemon=True)
    thread.start()
    last_state = None
    try:
        while thread.is_alive():
            _time.sleep(0.5)
            st = rec.status()
            if st["state"] != last_state:
                last_state = st["state"]
                if st["state"] == "recording":
                    print(f" » Aufzeichnung läuft: {st['meta'].get('track')} — "
                          f"{st['meta'].get('vehicle')}")
                elif st["state"] == "waiting":
                    print(" » Warte auf RaceRoom …")
                else:
                    print(f" » Status: {st['state']}")
    except KeyboardInterrupt:
        pass
    finally:
        rec.stop()
        thread.join(timeout=5)
        st = rec.status()
        for path in st["files"]:
            print(f"Gespeichert: {path}")
        if not st["files"]:
            print("Keine Aufzeichnung erstellt (RaceRoom lief nicht oder keine Session auf der Strecke).")
        if st["error"]:
            print(f"Hinweis: {st['error']}", file=sys.stderr)
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
        print(f"  Analyse {i} ({stamp}, {a.get('samples', '?')} Samples, {state}): {a.get('log_source', a.get('csv_source', '?'))}")
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("analyze", "record", "setups", "gui", "update", "times"):
        args = build_parser().parse_args(argv)
    else:
        args = build_parser().parse_args(["analyze", *argv])
    try:
        if args.command == "record":
            return _run_record(args)
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
    except FileNotFoundError as exc:
        print(f"Fehler: Datei nicht gefunden: {exc.filename or exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
