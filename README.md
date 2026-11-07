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

## Bridge-Exe automatisch starten (RaceRoom → MoTeC)

Damit MoTeC i2 überhaupt Daten von RaceRoom bekommt, läuft üblicherweise ein kleines Bridge-Exe. Der Coach kann es starten, überwachen und per **Strg+C kontrolliert beenden**:

```bash
r3e-coach bridge --exe "C:\Tools\R3E_MoTeC_Bridge.exe"
r3e-coach bridge --exe "C:\Tools\R3E_MoTeC_Bridge.exe" --args -- --port 5566
```

Damit der Pfad nicht jedes Mal eingegeben werden muss, legt eine Config an (wird automatisch aus dem aktuellen Verzeichnis geladen, wenn sie `.r3e-coach.json` heißt, sonst per `--config`):

```json
{
  "bridge_exe": "C:\\Tools\\R3E_MoTeC_Bridge.exe",
  "bridge_args": ["--port", "5566"],
  "bridge_cwd": "C:\\Tools"
}
```

```bash
r3e-coach bridge            # nutzt ./.r3e-coach.json
r3e-coach bridge --config "C:\Users\Du\r3e-coach.json"
```

Ablauf: `r3e-coach bridge` starten → RaceRoom starten → in MoTeC i2 loggen → fahren → Strg+C beendet die Bridge sauber. Danach die CSV exportieren und analysieren:

```bash
r3e-coach "C:\MoTeC\i2\Exports\mein-log.csv"
```

Tipp: Für ganz ohne Handgriffe kann die Bridge auch über einen Windows-Autostart-Eintrag oder den Taskplaner beim Login gestartet werden.

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
