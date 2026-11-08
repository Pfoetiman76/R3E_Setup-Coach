import json

SEVERITY_LABELS = {
    "high": {"de": "HOCH", "en": "HIGH"},
    "medium": {"de": "MITTEL", "en": "MEDIUM"},
    "low": {"de": "NIEDRIG", "en": "LOW"},
}

CATEGORY_LABELS = {
    "tyres": {"de": "Reifen", "en": "Tyres"},
    "handling": {"de": "Fahrverhalten", "en": "Handling"},
    "brakes": {"de": "Bremsen", "en": "Brakes"},
    "suspension": {"de": "Fahrwerk", "en": "Suspension"},
    "consistency": {"de": "Konsistenz", "en": "Consistency"},
}

SEVERITY_ORDER = ["high", "medium", "low"]


def _label(table, key, lang):
    return table.get(key, {}).get(lang, key)


def _localized(entry, lang):
    if isinstance(entry, dict):
        return entry.get(lang, entry.get("de", ""))
    return entry


def render_text(findings, session, lang="de"):
    time = session.col("time")
    duration = ""
    if len(time) > 1 and time[0] is not None and time[-1] is not None:
        duration = f" · Dauer {time[-1] - time[0]:.1f} s"
    lines = [
        f"R3E Setup-Coach — {session.source}",
        f"{len(session)} Samples{duration}",
        "-" * 60,
    ]
    if not findings:
        if len(session) == 0:
            lines.append({"de": "Keine Daten gefunden (0 Samples) — Datei evtl. UTF-16/falsches Format? Kopfzeile prüfen.",
                          "en": "No data found (0 samples) — file maybe UTF-16/wrong format? Check the header row."}[lang])
        else:
            lines.append({"de": "Keine Auffälligkeiten gefunden — Setup scheint stimmig.",
                          "en": "No issues found — setup looks consistent."}[lang])
        return "\n".join(lines)
    for sev in SEVERITY_ORDER:
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        lines.append(f"[{ _label(SEVERITY_LABELS, sev, lang) }]")
        for f in group:
            cat = _label(CATEGORY_LABELS, f.category, lang)
            lines.append(f"  {cat} ({f.rule})")
            lines.append(f"    • {_localized(f.text, lang)}")
            for a in f.actions:
                lines.append(f"    → {_localized(a, lang)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_json(findings, session, lang="de"):
    payload = {
        "source": session.source,
        "samples": len(session),
        "language": lang,
        "findings": [
            {
                "rule": f.rule,
                "category": f.category,
                "severity": f.severity,
                "text": _localized(f.text, lang),
                "actions": [_localized(a, lang) for a in f.actions],
            }
            for f in findings
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
