"""0.7.0: Konkrete, priorisierte Setup-Hinweise aus den Fundstellen.

Kombiniert die Diagnosen des Regelwerks mit den gespeicherten Setup-Werten
aus setups.json: Wo ein aktueller Wert vorliegt, nennt der Coach ein
konkretes Ziel (z. B. "Stabi vorne: 4 → 3" oder "Bremsbalance: 56 % → 54 %"),
sonst eine klar gerichtete Stufenänderung ("eine Stufe weicher").

Qt-frei, reine Python-Standardbibliothek — dieselben Regeln wie
parser/rules/store (R3E-Datenkonzept).
"""

ADVICE_HEADER = {
    "de": "Empfohlene nächste Schritte (priorisiert — oben zuerst testen):",
    "en": "Recommended next steps (prioritized — test the top one first):",
}

NO_ADVICE = {
    "de": "Keine konkreten Setup-Änderungen abgeleitet.",
    "en": "No concrete setup changes derived.",
}

LABELS = {
    "arb_front": {"de": "Stabi vorne", "en": "Front anti-roll bar"},
    "arb_rear": {"de": "Stabi hinten", "en": "Rear anti-roll bar"},
    "ride_height_front": {"de": "Fahrzeughöhe vorn", "en": "Front ride height"},
    "ride_height_rear": {"de": "Fahrzeughöhe hinten", "en": "Rear ride height"},
    "wing_front": {"de": "Frontflügel", "en": "Front wing"},
    "wing_rear": {"de": "Heckflügel", "en": "Rear wing"},
    "brake_bias": {"de": "Bremsbalance", "en": "Brake balance"},
    "pressure_front": {"de": "Reifendruck vorne", "en": "Front tyre pressure"},
    "pressure_rear": {"de": "Reifendruck hinten", "en": "Rear tyre pressure"},
}

UNITS = {
    "brake_bias": "%",
    "pressure_front": "bar",
    "pressure_rear": "bar",
}


def _num(v):
    if isinstance(v, bool):
        return None
    return v if isinstance(v, (int, float)) else None


def _fmt(v):
    return f"{v:g}"


def _label(field, lang):
    return LABELS.get(field, {}).get(lang, field)


def _unit(field):
    return UNITS.get(field, "")


def _item(rule, severity, field, current, target, text):
    return {
        "rule": rule,
        "severity": severity,
        "field": field,
        "current": current,
        "target": target,
        "text": text,
    }


def _with_value(rule, severity, field, current, target, direction_de, direction_en,
                reason_de, reason_en):
    unit = _unit(field)
    suffix = f" {unit}" if unit else ""
    cur_s = f"{_fmt(current)}{suffix}"
    tgt_s = f"{_fmt(target)}{suffix}"
    label_de, label_en = _label(field, "de"), _label(field, "en")
    return _item(rule, severity, field, current, target,
                 {"de": f"{label_de}: {cur_s} → {tgt_s} ({direction_de}; Grund: {reason_de}).",
                  "en": f"{label_en}: {cur_s} → {tgt_s} ({direction_en}; reason: {reason_en})."})


def _without_value(rule, severity, field, change_de, change_en):
    label_de, label_en = _label(field, "de"), _label(field, "en")
    return _item(rule, severity, field, None, None,
                 {"de": f"{label_de} {change_de}.",
                  "en": f"{label_en} {change_en}."})


def _step_advice(rule, severity, field, delta, word_de, word_en, reason_de, reason_en, chassis):
    """Stufenfeld (Stabi/Fahrzeughöhe): Ziel = aktueller Wert ± 1 Stufe."""
    current = _num((chassis or {}).get(field))
    if current is not None:
        return _with_value(rule, severity, field, current, current + delta,
                           f"eine Stufe {word_de}", f"one step {word_en}",
                           reason_de, reason_en)
    return _without_value(rule, severity, field,
                          f"eine Stufe {word_de}", f"one step {word_en}")


def _delta_advice(rule, severity, field, delta, reason_de, reason_en, values):
    """Zielfeld mit Einheit (Druck, Bremsbalance): Ziel = aktueller Wert + delta."""
    current = _num((values or {}).get(field))
    unit = _unit(field)
    amount = _fmt(float(abs(delta)))
    word_de, word_en = ("erhöhen", "raise") if delta > 0 else ("senken", "lower")
    if current is not None:
        return _with_value(rule, severity, field, current, current + delta,
                           f"{word_de} um {amount} {unit}", f"{word_en} by {amount} {unit}",
                           reason_de, reason_en)
    return _without_value(rule, severity, field,
                          f"um {amount} {unit} {word_de}", f"{word_en} by {amount} {unit}")


STATE_WORDS = {
    "cold": {"de_word": "erhöhen", "en_word": "raise", "state_de": "Reifen zu kalt",
             "state_en": "tyres too cold"},
    "hot": {"de_word": "senken", "en_word": "lower", "state_de": "Reifen zu heiß",
            "state_en": "tyres too hot"},
}


def _pressure_window_advice(rule, severity, state, tires):
    words = STATE_WORDS.get(state, STATE_WORDS["hot"])
    out = []
    for field in ("pressure_front", "pressure_rear"):
        current = _num((tires or {}).get(field))
        delta = +0.1 if state == "cold" else -0.1
        if current is not None:
            out.append(_item(
                rule, severity, field, current, current + delta,
                {"de": f"{_label(field, 'de')}: {_fmt(current)} bar → {_fmt(current + delta)} bar "
                       f"({words['de_word']} um 0,1 bar; {words['state_de']}).",
                 "en": f"{_label(field, 'en')}: {_fmt(current)} bar → {_fmt(current + delta)} bar "
                       f"({words['en_word']} by 0.1 bar; {words['state_en']})."}))
        else:
            out.append(_item(
                rule, severity, field, None, None,
                {"de": f"{_label(field, 'de')} um 0,1 bar {words['de_word']} ({words['state_de']}).",
                 "en": f"{_label(field, 'en')} {words['en_word']} by 0.1 bar ({words['state_en']})."}))
    return out


def build_advice(findings, chassis=None, tires=None):
    """Priorisierte concrete Änderungsvorschläge aus Finding-Objekten.

    chassis/tires: gespeicherte Werte aus setups.json (optional). Ohne
    gespeicherte Werte bleibt der Hinweis eine Stufenangabe. Die
    Reihenfolge folgt den Fundstellen (analyze sortiert bereits high → low).
    """
    chassis = chassis or {}
    tires = tires or {}
    out = []
    for f in findings:
        data = getattr(f, "data", None) or {}
        rule, sev = f.rule, f.severity
        if rule == "understeer":
            out.append(_step_advice(rule, sev, "arb_front", -1, "weicher", "softer",
                                    "Untersteuern in Kurven", "understeer in corners", chassis))
            out.append(_delta_advice(rule, sev, "brake_bias", +2.0,
                                      "Untersteuern in Kurven", "understeer in corners", chassis))
        elif rule == "oversteer":
            out.append(_step_advice(rule, sev, "arb_rear", -1, "weicher", "softer",
                                    "Übersteuerneigung des Hecks", "rear oversteer tendency", chassis))
        elif rule == "aero_understeer":
            # 0.9.4.0: Abtriebsbalance zu hecklastig — mehr Abtrieb vorn
            # (oder weniger hinten, wenn Luftwiderstand zählt).
            out.append(_step_advice(rule, sev, "wing_front", +1, "höher", "higher",
                                    "hoher Lenkaufwand in Schnellkurven — Abtrieb vorn fehlt",
                                    "excess steering effort in fast corners — front downforce missing",
                                    chassis))
            out.append(_step_advice(rule, sev, "wing_rear", -1, "niedriger", "lower",
                                    "Alternative zu mehr Frontabtrieb: Heckflügel senken",
                                    "alternative to more front downforce: lower the rear wing",
                                    chassis))
        elif rule == "aero_oversteer":
            # 0.9.4.0: Heck in Schnellkurven unruhig — Abtrieb hinten fehlt.
            out.append(_step_advice(rule, sev, "wing_rear", +1, "höher", "higher",
                                    "Heck in Schnellkurven unruhig — Abtrieb hinten fehlt",
                                    "nervous rear in fast corners — rear downforce missing",
                                    chassis))
        elif rule == "brake_balance":
            direction = data.get("direction", "too_front")
            delta = -2.0 if direction == "too_front" else +2.0
            reason_de = ("vordere Bremsscheiben deutlich heißer als hintige"
                         if direction == "too_front"
                         else "hintere Bremsscheiben deutlich heißer als vordere")
            reason_en = ("front brake discs much hotter than rears"
                         if direction == "too_front"
                         else "rear brake discs much hotter than fronts")
            out.append(_delta_advice(rule, sev, "brake_bias", delta,
                                     reason_de, reason_en, chassis))
        elif rule == "tyre_temp_balance":
            direction = data.get("direction", "front_hot")
            field = "pressure_front" if direction == "front_hot" else "pressure_rear"
            reason_de = ("Vorderreifen deutlich heißer" if direction == "front_hot"
                         else "Hinterreifen deutlich heißer")
            reason_en = ("front tyres much hotter" if direction == "front_hot"
                         else "rear tyres much hotter")
            out.append(_delta_advice(rule, sev, field, -0.1, reason_de, reason_en, tires))
        elif rule == "tyre_temp_side":
            hot = data.get("hotter", "left")
            hot_de = "links" if hot == "left" else "rechts"
            hot_en = "left" if hot == "left" else "right"
            out.append(_item(rule, sev, None, None, None,
                             {"de": f"Reifendruck auf der heißeren Seite ({hot_de}) um 0,1 bar senken — "
                                    f"die Strecke belastet diese Seite stärker.",
                              "en": f"Lower tyre pressure on the hotter side ({hot_en}) by 0.1 bar — "
                                    f"the track loads that side more."}))
        elif rule == "tyre_temp_window":
            out.extend(_pressure_window_advice(rule, sev, data.get("state", "hot"), tires))
        elif rule == "bottoming":
            for field in ("ride_height_front", "ride_height_rear"):
                out.append(_step_advice(rule, sev, field, +1, "höher", "higher",
                                        "Fahrzeug schlägt auf Geraden durch",
                                        "car bottoms out on straights", chassis))
    return out


def advice_dicts(advice, lang="de"):
    """Maschinenlesbar (Persistenz immer Deutsch — wie finding_dicts)."""
    return [
        {
            "rule": a["rule"],
            "severity": a["severity"],
            "field": a["field"],
            "current": a["current"],
            "target": a["target"],
            "text": a["text"].get(lang, a["text"].get("de", "")),
        }
        for a in advice
    ]


def render_lines(advice, lang="de"):
    """Nummerierte Zeilen (ohne Kopfzeile) für Bericht/GUI."""
    return [f"{i}) {a['text'].get(lang, a['text'].get('de', ''))}"
            for i, a in enumerate(advice, 1)]
