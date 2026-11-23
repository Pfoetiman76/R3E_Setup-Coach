# R3E Setup-Coach

Analysiert **Telemetrie aus RaceRoom (R3E)** und leitet daraus **konkrete Setup-Empfehlungen** ab — z. B. zu Aero, Reifendruck, Bremsbalance, Fahrwerk und Fahrverhalten. **Ab Version 0.8.0 vollständig eigenständig:** Der Coach zeichnet die Telemetrie selbst über die offizielle R3E-Shared-Memory-Schnittstelle auf. MoTeC i2, CSV-Exporte und die R2M-Bridge werden nicht mehr benötigt.

## Schnellstart (Quelle)

```bash
# Telemetrie aus RaceRoom aufzeichnen (Strg+C beendet und speichert)
python -m r3e_coach record

# Beispiel-Aufzeichnung analysieren
python -m r3e_coach examples/beispiel.coachlog
python -m r3e_coach examples/beispiel.coachlog --lang en   # englische Ausgabe
python -m r3e_coach examples/beispiel.coachlog --json      # maschinenlesbares JSON
```

Installationspaket (Windows): Die neueste `R3E-Setup-Coach-Setup-…exe` steht unter [Releases](https://github.com/Pfoetiman76/R3E_Setup-Coach/releases). Die App aktualisiert sich über den Knopf in der Statusleiste selbstständig.

```bash
r3e-coach examples/beispiel.coachlog
r3e-coach record --hz 25 --wait
```

## Eigene Aufzeichnung statt MoTeC/R2M (ab 0.8.0)

Der Coach liest die offizielle Shared-Memory-Schnittstelle von RaceRoom (`$R3E`, Strukturversion 3.6, pack(1)) direkt aus — 50 Mal pro Sekunde. Daraus entsteht eine eigene, lesbare Logdatei pro Sitzung (`.coachlog`, Textformat mit Kopfdaten). Das löst auch das bekannte R2M-Problem: **ESC ins Menü oder ein Sessionwechsel beendet eine Aufzeichnung nicht mehr abrupt**, sondern schließt die Datei sauber und beginnt bei Rückkehr auf die Strecke automatisch eine neue.

- Strecke/Layout/Fahrzeug stehen automatisch im Log (auch für die Analyse und `setups.json`).
- Zielordner standardmäßig: `Dokumente\R3E Setup-Coach\recordings`. Dort liegt zusätzlich `coach-diagnose.txt` (ab 0.9.2): ein Protokoll aller Ereignisse mit Uhrzeit (RaceRoom erkannt, Zustandswechsel, geschriebene Dateien, Fehler) — hilfreich, wenn die App während der Fahrt im VR-Headset nicht sichtbar ist.
- **Ab 0.9.3** sucht die Schnittstelle den Shared Memory in drei Namensräumen (`Local\$R3E`, `$R3E`, `Global\$R3E`), und `coach-diagnose.txt` protokolliert, über welchen Weg die Verbindung zustande kam. Beim Auto-Update werden die Nutzerdaten (`.r3e-coach.json`, `setups.json`) zusätzlich nach `%TEMP%` gesichert und nach dem Kopieren zurückgeholt — ein Fehlschlagen der xcopy-Ausschlussliste kann die Konfiguration nicht mehr überschreiben; das Update-Paket enthält zudem keine Standard-Config mehr.
- **GUI: automatische Aufzeichnung ab 0.8.1** — die App startet den Rekorder von selbst und wartet auf RaceRoom; ein manueller Start ist nicht mehr nötig (Haken „Automatisch aufzeichnen", persistiert als `auto_record`).
- Alte R2M/MoTeC-CSV-Dateien werden nicht mehr gelesen; `bridge`-Kommando und MoTeC-Parser sind entfernt.

```bash
r3e-coach record --out "D:\Aufnahmen" --hz 50
```

## CLI-Übersicht

```bash
r3e-coach analyze examples/beispiel.coachlog --json
r3e-coach analyze examples/beispiel.coachlog --save             # Strecke/Fahrzeug aus dem Log
r3e-coach analyze examples/beispiel.coachlog --sheet zettel.txt # Setup-Zettel als Textdatei
r3e-coach analyze examples/beispiel.coachlog --sheet            # Standardordner + Dateiname-Vorschlag
r3e-coach setups --key "Sachsenring|Sachsenring|Audi R8 LMS Ultra 2016"
r3e-coach times --track "Sachsenring" --vehicle "Audi R8 LMS Ultra 2016"
r3e-coach update --check
```

## Grafische Oberfläche

```bash
r3e-coach gui
```

Die Oberfläche hat drei Bereiche: **1) Aufzeichnen** (die Aufzeichnung beginnt **automatisch, sobald RaceRoom läuft** — wie in PitBoss genügt das Starten der App; der Haken „Automatisch aufzeichnen" ist standardmäßig gesetzt und wird in der Config gespeichert, der Zielordner ist einstellbar; jede fertige Sitzung wird als `.coachlog` gesichert und automatisch im Reiter 2 eingetragen), **2) Telemetrie analysieren** (Log per Dialog wählen, Strecke/Layout/Fahrzeug füllen sich aus dem Log; der Bericht erscheint im Fenster, mit „Analysieren und speichern" landet die Analyse in der Setup-Sammlung) und **3) Setups** (gespeicherte Setups mit Zielzeit, Best-/Ø-Zeiten aus R3E-Resultate und Detailansicht; Doppelklick öffnet den Eintrag, Zielzeit und Notizen sind editierbar).

**„Empfohlene nächste Schritte“** (ab 0.7.0): Der Bericht endet mit priorisierten, konkreten Hinweisen — z. B. „Stabi vorne: 4 → 3“ statt nur „Untersteuern“. Sind Werte des aktuellen Setups in `setups.json` gespeichert (Fahrwerk/Reifen im Reiter 3), nennt der Coach das konkrete Ziel, sonst eine gerichtete Stufenänderung. **Ab 0.9.4.0 auch Aero:** Benötigt das Auto in Schnellkurven (ab 160 km/h) deutlich mehr Lenkwinkel pro g als in Langsamkurven (bis 110 km/h), erscheinen priorisierte Flügel-Hinweise („Frontflügel: 6 → 7“); ein unruhiges Heck in Schnellkurven empfiehlt mehr Heckflügel. Die Setup-Felder `wing_front`/`wing_rear` sind in `setups.json` neu.

**Setup-Zettel** (ab 0.9.0): Der Knopf „Setup-Zettel …“ im Reiter „Telemetrie analysieren“ erzeugt eine druckfertige Garage-Checkliste je Fahrzeug und Strecke — Fahrzeug/Strecke/Layout, Datum, die priorisierten Einstellungen als abhakbare Punkte und ein Prüfhinweis. Der Zettel wird als `.txt` gespeichert (Ziel per Dialog wählbar, Vorschlagsname aus Strecke/Layout/Fahrzeug). CLI: `analyze --sheet <datei>` (ohne Pfad: `<App-Ordner>\sheets` mit automatischem Namen). Der Zettel ist die verlässliche Alternative zum direkten Schreiben von RaceRoom-`.svm`-Dateien, deren Binärformat undokumentiert ist.

## Setup-Sammlung (setups.json)

Analysen werden unter `Strecke|Layout|Fahrzeug` gespeichert (Findings maschinenlesbar, immer deutsch), inklusive Quelle, Datum und optionalen Notizen. Änderungen der Setup-Werte (Stabi, Fahrzeughöhe, Bremsbalance, Reifendruck) erzeugen eine Historie je Eintrag.

```json
{
  "Sachsenring|Sachsenring|Audi R8": {
    "target_lap_ms": 83500,
    "notes": "Weicher Stabi vorne hat Untersteuern reduziert",
    "chassis": { "arb_front": 3, "brake_bias": 52 },
    "tires": { "pressure_front": 1.7 }
  }
}
```

## Zeiten aus R3E-Resultate (nur lesend)

Best-/Ø-Zeiten kommen aus der `results.db` von R3E-Resultate (gleiches Datenkonzept):

```bash
r3e-coach times                          # alle bekannten Kombinationen
r3e-coach times --track Sachsenring      # Best/Ø für eine Kombination
```

## Auto-Update (ab 0.6.0)

Der Knopf „Update installieren“ in der Statusleiste lädt das neueste GitHub-Release, prüft die Version, legt das Update im Staging-Ordner `<App-Ordner>.update` ab, startet `apply-update.cmd` und beendet sich. Konfiguration, Setup-Sammlung und Marker-Dateien bleiben erhalten (ab 0.9.3 zusätzlich per `%TEMP%`-Sicherung abgesichert); die Exe wird durch Umbenennen ersetzt und beim nächsten Start aufgeräumt. Der Fenstertitel zeigt die aktive Version.

## Veröffentlichung (ab 0.9.3.1 vollautomatisch)

Versionen sind vierstellig (`vx.y.z.w`, fortlaufender Build-Zähler). Sobald `main` eine Version aus `pyproject.toml` enthält, für die es noch kein Release gibt, baut der Workflow `auto-release` die Assets selbst und legt Tag **und** Release automatisch an. Ein manueller Schritt ist nicht mehr nötig; die Inbetriebnahme beschränkt sich darauf, die Versionsnummer an den drei Stellen (`pyproject.toml`, `r3e_coach/__init__.py`, `installer/setup.iss`) zu erhöhen und auf `main` zu mergen.

## Komponenten

| Modul | Aufgabe |
| --- | --- |
| `r3e_shared.py` | ctypes-Abtrag der R3E-Shared-Memory-Struktur v3.6 (`$R3E`), Einheiten-Umrechnung |
| `recorder.py` | Aufzeichnung als eigener Thread: Zustandsmaschine (Warten/Menü/Pause/Box/Aufzeichnung), Sitzungstrennung, `.coachlog` pro Sitzung |
| `logdata.py` | Lesen/Schreiben von `.coachlog`; direkter Import in `telemetry.Session` |
| `telemetry.py`/`channels.py` | Kanal-Normalisierung (viele Namensvarianten) und Session-Objekt |
| `rules.py` | Regelwerk: Reifentemperatur-Balance, Unter-/Übersteuern, Bremsen, Fahrhöhe, Konsistenz |
| `advice.py` | Priorisierte, konkrete Setup-Hinweise (mit Zielwerten aus `setups.json`) |
| `store.py` | `setups.json`-Datenmodell (`schema_version` 1) |
| `queries.py` | Lesender Zugriff auf `results.db` von R3E-Resultate |
| `updater.py` | Release-Prüfung, Download und Staging-basierter Selbsttausch |

## Entwicklung

```bash
pip install -e .[test]
python -m pytest -q
```

- `installer/setup.iss` (Inno Setup) baut die Windows-Installation; Version zentral über `MyAppVersion`.
- `tools/gen_icon.py` erzeugt `assets/app.ico` (Exe/Verknüpfung) und `assets/app.png` (Qt-Fenster-/Taskleisten-Icon — Qt kann PNG-in-ICO nicht laden).
- Tests laufen unter Linux ohne RaceRoom: Shared-Memory-Zugriffe sind über injizierbare Byte-Puffer testbar.
