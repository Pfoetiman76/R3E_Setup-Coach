from dataclasses import dataclass, field

CORNERS = ("fl", "fr", "rl", "rr")
TYRE_IDEAL = (75.0, 100.0)


@dataclass
class Finding:
    rule: str
    category: str
    severity: str
    text: dict
    actions: list = field(default_factory=list)


@dataclass
class Ctx:
    min_speed: float = 40.0


def _running_mask(session, min_speed):
    speed = session.col("speed")
    if not speed:
        return [True] * len(session)
    return [(s is not None and s >= min_speed) for s in speed]


def _avg(vals, mask=None):
    if mask is not None:
        sel = [v for v, m in zip(vals, mask) if m and v is not None]
    else:
        sel = [v for v in vals if v is not None]
    return sum(sel) / len(sel) if sel else None


def rule_tyre_temps(session, ctx):
    out = []
    if not all(session.has(f"tyre_temp_{c}") for c in CORNERS):
        return out
    mask = _running_mask(session, ctx.min_speed)
    t = {c: _avg(session.col(f"tyre_temp_{c}"), mask) for c in CORNERS}
    if any(v is None for v in t.values()):
        return out
    front = (t["fl"] + t["fr"]) / 2
    rear = (t["rl"] + t["rr"]) / 2
    left = (t["fl"] + t["rl"]) / 2
    right = (t["fr"] + t["rr"]) / 2
    overall = (front + rear) / 2
    if front - rear > 5:
        out.append(Finding(
            "tyre_temp_balance", "tyres", "high",
            {"de": f"Vorderreifen deutlich heißer als Hinterreifen (vorne {front:.1f} °C, hinten {rear:.1f} °C) — zu viel Grip vorne / Schlupf hinten.",
             "en": f"Front tyres much hotter than rears (front {front:.1f} °C, rear {rear:.1f} °C) — too much front grip / rear slip."},
            [{"de": "Frontflügel eine Stufe zurück oder Heckflügel eine Stufe hoch (R3E-Menü: Aero).",
              "en": "Lower front wing one step or raise rear wing one step (R3E menu: Aero)."},
             {"de": "Reifendruck vorne um 0,1 bar senken.",
              "en": "Lower front tyre pressure by 0.1 bar."}]))
    elif rear - front > 5:
        out.append(Finding(
            "tyre_temp_balance", "tyres", "high",
            {"de": f"Hinterreifen deutlich heißer als Vorderreifen (hinten {rear:.1f} °C, vorne {front:.1f} °C) — Heck rutscht / zu wenig Heck-Abstützung.",
             "en": f"Rear tyres much hotter than fronts (rear {rear:.1f} °C, front {front:.1f} °C) — rear sliding / not enough rear support."},
            [{"de": "Heckflügel eine Stufe hoch oder Frontflügel eine Stufe zurück (R3E-Menü: Aero).",
              "en": "Raise rear wing one step or lower front wing one step (R3E menu: Aero)."},
             {"de": "Reifendruck hinten um 0,1 bar senken.",
              "en": "Lower rear tyre pressure by 0.1 bar."}]))
    if abs(left - right) > 4:
        hot_de = "links" if left > right else "rechts"
        hot_en = "left" if left > right else "right"
        out.append(Finding(
            "tyre_temp_side", "tyres", "medium",
            {"de": f"Reifentemperatur links/rechts ungleich ({left:.1f} °C vs. {right:.1f} °C) — Strecke belastet eine Seite stärker.",
             "en": f"Left/right tyre temp imbalance ({left:.1f} °C vs. {right:.1f} °C) — the track loads one side more."},
            [{"de": f"Druck auf der heißeren Seite ({hot_de}) um 0,1 bar senken.",
              "en": f"Lower pressure on the hotter side ({hot_en}) by 0.1 bar."}]))
    if overall < TYRE_IDEAL[0]:
        out.append(Finding(
            "tyre_temp_window", "tyres", "medium",
            {"de": f"Reifen insgesamt zu kalt (Ø {overall:.1f} °C, Ziel {TYRE_IDEAL[0]:.0f}–{TYRE_IDEAL[1]:.0f} °C).",
             "en": f"Tyres too cold overall (avg {overall:.1f} °C, target {TYRE_IDEAL[0]:.0f}–{TYRE_IDEAL[1]:.0f} °C)."},
            [{"de": "Reifendruck rundum um 0,1 bar erhöhen.",
              "en": "Raise tyre pressure all round by 0.1 bar."},
             {"de": "Negativen Sturz leicht erhöhen (R3E-Menü: Fahrwerk).",
              "en": "Increase negative camber slightly (R3E menu: Suspension)."}]))
    elif overall > TYRE_IDEAL[1]:
        out.append(Finding(
            "tyre_temp_window", "tyres", "medium",
            {"de": f"Reifen insgesamt zu heiß (Ø {overall:.1f} °C, Ziel {TYRE_IDEAL[0]:.0f}–{TYRE_IDEAL[1]:.0f} °C).",
             "en": f"Tyres too hot overall (avg {overall:.1f} °C, target {TYRE_IDEAL[0]:.0f}–{TYRE_IDEAL[1]:.0f} °C)."},
            [{"de": "Reifendruck rundum um 0,1 bar senken.",
              "en": "Lower tyre pressure all round by 0.1 bar."}]))
    return out


def rule_handling(session, ctx):
    out = []
    if not (session.has("steer") and session.has("g_lat")):
        return out
    speed = session.col("speed")
    steer = session.col("steer")
    glat = session.col("g_lat")
    n = min(len(steer), len(glat))
    corner = []
    for i in range(n):
        s = speed[i] if i < len(speed) and speed[i] is not None else ctx.min_speed
        if s >= ctx.min_speed and glat[i] is not None and abs(glat[i]) >= 0.8:
            corner.append(i)
    if len(corner) < 20:
        return out
    mean_steer = sum(abs(steer[i]) for i in corner if steer[i] is not None) / len(corner)
    corrections = 0
    prev_d = None
    prev_s = None
    for i in corner:
        s = steer[i]
        if s is None:
            continue
        if prev_s is not None:
            d = s - prev_s
            if prev_d is not None and prev_d * d < 0 and abs(d) > 0.5:
                corrections += 1
            prev_d = d
        prev_s = s
    time = session.col("time")
    duration_min = ((time[-1] - time[0]) / 60.0) if len(time) > 1 and time[0] is not None and time[-1] is not None else 1.0
    corrections_per_min = corrections / max(duration_min, 1e-9)
    if mean_steer > 12:
        out.append(Finding(
            "understeer", "handling", "high",
            {"de": f"Auffälliges Untersteuern in Kurven (mittlerer Lenkwinkel {mean_steer:.1f}° bei >0,8 g).",
             "en": f"Clear understeer in corners (mean steering angle {mean_steer:.1f}° at >0.8 g)."},
            [{"de": "Frontflügel eine Stufe hoch (R3E-Menü: Aero).",
              "en": "Raise front wing one step (R3E menu: Aero)."},
             {"de": "Stabi vorne eine Stufe weicher oder Federn vorne weicher (R3E-Menü: Fahrwerk).",
              "en": "Soften front anti-roll bar one step or front springs (R3E menu: Suspension)."},
             {"de": "Bremsbalance 1–2 % nach vorne (R3E-Menü: Bremsen).",
              "en": "Move brake balance 1–2 % forward (R3E menu: Brakes)."}]))
    elif corrections_per_min > 6:
        out.append(Finding(
            "oversteer", "handling", "medium",
            {"de": f"Viele Lenkkorrekturen in Kurven ({corrections_per_min:.1f}/min) — Heck neigt zum Übersteuern.",
             "en": f"Many steering corrections in corners ({corrections_per_min:.1f}/min) — rear tends to oversteer."},
            [{"de": "Heckflügel eine Stufe hoch (R3E-Menü: Aero).",
              "en": "Raise rear wing one step (R3E menu: Aero)."},
             {"de": "Stabi hinten weicher oder Differential öffnen (R3E-Menü: Fahrwerk/Getriebe).",
              "en": "Soften rear anti-roll bar or open the differential (R3E menu: Suspension/Drivetrain)."}]))
    return out


def rule_brakes(session, ctx):
    out = []
    if not session.has("brake") or not all(session.has(f"brake_temp_{c}") for c in CORNERS):
        return out
    speed = session.col("speed")
    brake = session.col("brake")
    g_long = session.col("g_long")
    n = len(brake)
    mask = []
    lockups = 0
    for i in range(n):
        s = speed[i] if i < len(speed) and speed[i] is not None else ctx.min_speed
        b = brake[i] is not None and brake[i] > 0.5 and s >= ctx.min_speed
        mask.append(b)
        if (brake[i] is not None and brake[i] > 0.9 and s >= ctx.min_speed
                and i < len(g_long) and g_long[i] is not None and g_long[i] < -0.9):
            lockups += 1
    tf = {c: _avg(session.col(f"brake_temp_{c}"), mask) for c in CORNERS}
    if any(v is None for v in tf.values()):
        return out
    front = (tf["fl"] + tf["fr"]) / 2
    rear = (tf["rl"] + tf["rr"]) / 2
    diff = front - rear
    if diff > 60 or (diff > 30 and lockups > 5):
        sev = "high" if lockups > 5 else "medium"
        out.append(Finding(
            "brake_balance", "brakes", sev,
            {"de": f"Bremsbalance zu weit vorne (vorn {front:.0f} °C, hinten {rear:.0f} °C" + (f", {lockups} mutmaßliche Blockierer" if lockups else "") + ").",
             "en": f"Brake balance too far forward (front {front:.0f} °C, rear {rear:.0f} °C" + (f", {lockups} suspected lock-ups" if lockups else "") + ")."},
            [{"de": "Bremsbalance 1–2 % nach hinten verschieben (R3E-Menü: Bremsen).",
              "en": "Move brake balance 1–2 % rearward (R3E menu: Brakes)."},
             {"de": "Bremsdruck vorn reduzieren, falls verstellbar.",
              "en": "Reduce front brake pressure if adjustable."}]))
    elif rear - front > 60:
        out.append(Finding(
            "brake_balance", "brakes", "medium",
            {"de": f"Bremsbalance zu weit hinten (hinten {rear:.0f} °C, vorn {front:.0f} °C) — lange Bremswege, Instabilität.",
             "en": f"Brake balance too far rearward (rear {rear:.0f} °C, front {front:.0f} °C) — long stopping distances, instability."},
            [{"de": "Bremsbalance 1–2 % nach vorne verschieben (R3E-Menü: Bremsen).",
              "en": "Move brake balance 1–2 % forward (R3E menu: Brakes)."}]))
    return out


def rule_ride_height(session, ctx):
    out = []
    cols = {c: session.col(f"susp_travel_{c}") for c in CORNERS if session.has(f"susp_travel_{c}")}
    if not cols:
        return out
    throttle = session.col("throttle")
    glat = session.col("g_lat")
    speed = session.col("speed")
    n = min((len(c) for c in cols.values()), default=0)
    straight_vals = []
    for i in range(n):
        th = throttle[i] if i < len(throttle) else None
        g = glat[i] if i < len(glat) else None
        s = speed[i] if i < len(speed) and speed[i] is not None else ctx.min_speed
        if th is not None and th > 0.95 and s >= ctx.min_speed and (g is None or abs(g) < 0.2):
            for c in cols.values():
                if i < len(c) and c[i] is not None:
                    straight_vals.append(c[i])
    if not straight_vals:
        return out
    min_travel = min(straight_vals)
    if min_travel <= 2.0:
        out.append(Finding(
            "bottoming", "suspension", "medium",
            {"de": f"Federweg auf Geraden nahe dem Anschlag (min. {min_travel:.1f} mm) — Fahrzeug schlägt durch.",
             "en": f"Suspension travel on straights near the bump stop (min {min_travel:.1f} mm) — car bottoms out."},
            [{"de": "Fahrzeughöhe vorn/hinten je eine Stufe erhöhen (R3E-Menü: Fahrwerk).",
              "en": "Raise ride height front/rear by one step (R3E menu: Suspension)."},
             {"de": "Federn eine Stufe härter, falls die Höhe nicht weiter angehoben werden soll.",
              "en": "Stiffen springs one step if ride height should stay as is."}]))
    return out


def rule_consistency(session, ctx):
    out = []
    if not session.has("lap_time"):
        return out
    laps = []
    prev = None
    for v in session.col("lap_time"):
        if v is not None and v > 10 and v != prev:
            laps.append(v)
        if v is not None:
            prev = v
    if len(laps) < 3:
        return out
    best = min(laps)
    med = sorted(laps)[len(laps) // 2]
    delta = (med - best) / best * 100.0
    if delta > 1.0:
        out.append(Finding(
            "consistency", "consistency", "low",
            {"de": f"Rundenzeiten schwanken um {delta:.1f} % zwischen Best- ({best:.2f} s) und Mittellap ({med:.2f} s).",
             "en": f"Lap times vary by {delta:.1f} % between best ({best:.2f} s) and median lap ({med:.2f} s)."},
            [{"de": "Setup-Schritte einzeln testen und nur beibehalten, wenn die Streuung sinkt.",
              "en": "Test setup changes one at a time and keep them only if the spread shrinks."}]))
    return out


RULES = [rule_tyre_temps, rule_handling, rule_brakes, rule_ride_height, rule_consistency]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def analyze(session, ctx=None):
    ctx = ctx or Ctx()
    findings = []
    for rule in RULES:
        findings.extend(rule(session, ctx))
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 3))
    return findings
