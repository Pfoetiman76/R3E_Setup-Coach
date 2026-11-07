import re

CORNERS = ("fl", "fr", "rl", "rr")


def normalize(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


BASE_PATTERNS = {
    "time": [r"^time$", r"^sessiontime$", r"^racetime$", r"^elapsedtime$"],
    "lap_time": [r"^laptime$", r"^lastlaptime$", r"^prevlaptime$"],
    "speed": [r"^speed$", r"^gpsspeed$", r"^vehiclespeed$", r"^carspeed$", r"^velocity$"],
    "throttle": [r"^throttle$", r"^throttlepos(?:ition)?$", r"^accelerator(?:pos)?$", r"^apps$"],
    "brake": [r"^brake$", r"^brakepress(?:ure)?$", r"^brakepos(?:ition)?$"],
    "steer": [r"^steeringangle$", r"^steerangle$", r"^steer$", r"^steering$", r"^handwheelangle$"],
    "g_lat": [
        r"^glat$", r"^latg$", r"^gforcelat$", r"^gforcey$",
        r"^latacc(?:el(?:eration)?)?$", r"^lateralacc(?:el(?:eration)?)?$", r"^accellat$",
    ],
    "g_long": [
        r"^glong$", r"^longg$", r"^gforcelong$", r"^gforcex$",
        r"^longacc(?:el(?:eration)?)?$", r"^longitudinalacc(?:el(?:eration)?)?$", r"^accellong$",
    ],
}

CORNER_STEMS = {
    "tyre_temp": ["tyretemp", "tiretemp"],
    "tyre_press": ["tyrepress", "tirepress", "tp"],
    "brake_temp": ["braketemp", "brakedisktemp", "brakedisctemp"],
    "susp_travel": ["susptravel", "suspensiontravel", "wheely", "susppos", "rideheight"],
}


def _corner_regex(stem):
    c = "|".join(CORNERS)
    return re.compile(rf"^(?:{re.escape(stem)}({c})|(?:{c}){re.escape(stem)})([imo])?$")


CORNER_REGEXES = [(kind, [(stem, _corner_regex(stem)) for stem in stems])
                  for kind, stems in CORNER_STEMS.items()]


def _match_base(norm):
    for key, patterns in BASE_PATTERNS.items():
        for pat in patterns:
            if re.match(pat, norm):
                return key
    return None


def resolve(names):
    mapping = {}
    for i, name in enumerate(names):
        norm = normalize(name)
        if not norm:
            continue
        base = _match_base(norm)
        if base:
            mapping.setdefault(base, []).append(i)
            continue
        for kind, regexes in CORNER_REGEXES:
            for stem, rx in regexes:
                m = rx.match(norm)
                if m:
                    mapping.setdefault(f"{kind}_{m.group(1)}", []).append(i)
                    break
    return mapping
