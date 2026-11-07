# R3E Setup-Coach

Analysiert **MoTeC-i2-Telemetrie (CSV-Export)** und leitet daraus **Setup-Empfehlungen für RaceRoom (R3E)** ab — z. B. zu Aero, Reifendruck, Bremsbalance, Fahrwerk und Fahrverhalten.

Reine Python-Standardbibliothek, keine externen Abhängigkeiten.

## Schnellstart

```bash
# Telemetrie in MoTeC i2 exportieren: Datei → Export → CSV (mit Kanal-Header)
python -m r3e_coach mein-log.csv
python -m r3e_coach mein-log.csv --lang en          # englische Ausgabe
python -m r3e_coach mein-log.csv --json             # maschinenlesbares JSON
python -m r3e_coach mein-log.csv --min-speed 60     # Schwelle für Fahrmanöver anpassen
```

Beispiel-Log liegt unter `examples/beispiel_motec_i2.csv`:

```bash
python -m r3e_coach examples/beispiel_motec_i2.csv
```

Als installierbares Paket steht außerdem der Befehl `r3e-coach` zur Verfügung:

```bash
pip install .
r3e-coach mein-log.csv
```

## Unterstützte Kanäle

Kanalnamen werden robust per Alias-Matching erkannt (Groß-/Kleinschreibung und Sonderzeichen egal). Sinnvoll sind u. a.:

| Zweck | typische MoTeC-Namen |
|---|---|
| Zeit / Rundenzeit | `Time`, `Lap Time` |
| Geschwindigkeit | `Speed`, `GPS Speed` |
| Gas / Bremse | `Throttle`, `Brake` |
| Lenkwinkel, Längs-/Querbeschleunigung | `Steering_Angle`, `G_Lat`, `G_Long` |
| Reifentemperatur je Ecke | `Tyre Temp FL/FR/RL/RR` (auch `_I/_M/_O` — werden gemittelt) |
| Bremsentemperatur je Ecke | `Brake Temp FL/FR/RL/RR` |
| Federweg je Ecke | `Susp Travel FL/FR/RL/RR`, `WheelY …` |

Fehlende Kanäle werden übersprungen — jede Regel arbeitet nur mit den vorhandenen Daten.

## Was analysiert wird

- **Reifen:** Temperatur-Balance vorne/hinten und links/rechts, absolutes Temperaturniveau (Ziel ~75–100 °C) → Druck-/Aero-Empfehlungen
- **Fahrverhalten:** Lenkwinkel und Lenkkorrekturen in Kurven → Unter-/Übersteuern → Aero-, Stabi-, Bremsbalance-Empfehlungen
- **Bremsen:** Bremsentemperaturen + mutmaßliche Blockierer → Bremsbalance
- **Fahrwerk:** minimaler Federweg auf Geraden → Durchschlagen → Höhe/Federn
- **Konsistenz:** Streuung zwischen Best- und Mittellap

## Wichtiger Hinweis

Die Schwellen sind **Heuristiken** aus Telemetrie-Erfahrung, keine Garantien. Coach-Ausgaben immer mit Streckenkenntnis und eigenem Gefühl abgleichen und Änderungen **eine nach der anderen** testen. Das Tool liest nur Daten — es verändert nichts am Fahrzeug.

## Entwicklung

```bash
pip install -e .[test]
pytest
```
