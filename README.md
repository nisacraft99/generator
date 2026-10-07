# User Story → Testcase Generator

Streamlit-Anwendung, die aus Userstories und Akzeptanzkriterien manuelle Testfälle
generiert und die Ergebnisse automatisch bewertet. Jede Userstory wird in zwei
Varianten generiert: ohne und mit UI-Kontext (`data/ui_context.json`). Beide
Varianten verwenden denselben Prompt; der einzige Unterschied ist, ob die
UI-Datei Teil der Modelleingabe ist.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Benötigte Einstellungen:

| Name | Zweck | Ort |
|---|---|---|
| `OPENAI_API_KEY` | Zugriff auf die Modelle | Umgebungsvariable oder `.env` |
| `APP_PASSWORD` | Passwort der Anwendung | Umgebungsvariable oder `.streamlit/secrets.toml` |

## Aufbau

```
app.py                        Einstiegspunkt der Streamlit-Anwendung
data/
  bulk_userstories.json       Userstories mit Akzeptanzkriterien
  ui_context.json             UI-Kontext: Knoten und Beziehungen der Anwendung
  navigation_targets.json     Soll-Navigation je Userstory
prompts/
  generator_system.txt        System-Prompt der Testfallgenerierung
  judge_system.txt            System-Prompt des LLM-as-a-Judge
assets/style.css              Gestaltung der Oberfläche
testcase_generator/
  config.py                   Pfade, Modelle, Parameter, Varianten, Vokabular der Anwendung
  resources.py                OpenAI-Client, UI-Kontext, Soll-Navigation
  user_stories.py             Laden und Prüfen der Userstories
  ui_model.py                 Datenmodell des UI-Kontexts
  generation.py               Generierung, Verarbeitung der Modellantwort, Protokoll des Aufrufs
  evaluation/
    ac_coverage.py            Acceptance Criteria Coverage (LLM-as-a-Judge)
    role_coverage.py          Role Coverage
    navigation.py             Navigation Path Correctness, Target Node Coverage
    text_checks.py            ID-Text Consistency, Console Naming
    text.py                   Textaufbereitung für die regelbasierten Metriken
  experiment.py               Bulk-Lauf, Neuauswertung, Zusammenfassungen
  checkpoints.py              Zwischenstände eines Bulk-Laufs
  pdf_report.py               PDF-Export
  ui/                         Abschnitte der Oberfläche
tests/                        Automatische Tests
```

## Metriken

| Metrik | Varianten | Liest | Berechnung |
|---|---|---|---|
| Acceptance Criteria Coverage | beide | Schritt-Text | abgedeckte Kriterien / alle Kriterien |
| Role Coverage | beide | Schritt-Text | Rollen mit Login-Schritt / in der Userstory genannte Rollen |
| Console Naming | beide | Schritt-Text | Testfälle, die die richtige Konsole nennen / alle Testfälle |
| Navigation Path Correctness | mit UI-Kontext | `ui_node_id` | Testfälle mit korrektem Basispfad / bewertbare Testfälle |
| Target Node Coverage | mit UI-Kontext | `ui_node_id` | erreichte Zielknoten / alle Zielknoten der Userstory |
| ID-Text Consistency | mit UI-Kontext | `ui_node_id` und Schritt-Text | Testfälle ohne Widerspruch / Testfälle mit Knoten-ID |

Die exportierten Testfälle zeigen dem Tester nur Schritt und erwartetes Ergebnis,
nicht die `ui_node_id`. Deshalb gibt es neben den ID-basierten Metriken zwei, die
den Text prüfen.

### Acceptance Criteria Coverage

Ein zweites Modell (Judge) bekommt je ein Akzeptanzkriterium und alle Testfälle
einer Ausgabe und entscheidet „abgedeckt“ oder „nicht abgedeckt“. Die Userstory
erhält es als Kontext, damit Abkürzungen und Rollen im Kriterium verständlich
sind; beurteilt wird nur das eine Kriterium. Die Regeln stehen in
`prompts/judge_system.txt`.

Grenzen: Das Urteil stammt von einem Sprachmodell und kann falsch oder
uneinheitlich sein. Schlägt ein Judge-Aufruf fehl, bleibt die Ausgabe
unvollständig und wird nicht als 0 % gezählt.

### Role Coverage

Eine Rolle gilt als gefordert, wenn sie in Userstory oder Akzeptanzkriterien als
Akteur oder in einer Berechtigungsregel vorkommt („As a Manager“, „only a user
with the role director“). Sie gilt als abgedeckt, wenn ein Schritt ausdrücklich
mit ihr anmeldet („Log in as Manager“).

Grenzen: Geprüft wird nur der Login-Schritt, nicht ob die Rolle inhaltlich
richtig getestet wird.

### Navigation Path Correctness

Je Userstory legt `required_per_testcase` in `navigation_targets.json` den
Basispfad fest, zum Beispiel Coordination → Team Meeting → TM Detail. Ein
Testfall ist korrekt, wenn seine `ui_node_id`-Werte diesen Pfad vollständig und
in der richtigen Reihenfolge enthalten und keine unbekannte ID vorkommt. Weitere
Knoten davor, dazwischen oder danach sind erlaubt.

Löst ein Schritt laut UI-Datei einen Übergang aus (etwa der Klick auf einen
ID-Link), zählt der erreichte Bildschirm mit, auch wenn er keine eigene ID
trägt. Fehlende Vorgängerknoten werden nie ergänzt.

Grenzen:

- Testfälle, in denen eine Rolle ein Modul gar nicht öffnen darf, haben keinen
  Pfad zur Funktion und werden nicht bewertet. Diese Testfälle werden an
  Stichwörtern erkannt (`NO_ACCESS_ROLES`, `NO_ACCESS_AREA_WORDS` in `config.py`
  und Formulierungen in `navigation.py`). Die Erkennung kann Testfälle falsch
  einordnen. Der Wert `correctness_pct_without_skipping` gibt deshalb zusätzlich
  das Ergebnis über alle Testfälle an.
- Führt ein Button zurück auf einen Bildschirm des Basispfads, kann er den Pfad
  erfüllen, obwohl der Testfall den Bildschirm nicht regulär geöffnet hat.
- US-25 hat keinen Basispfad und wird nicht bewertet.

### Target Node Coverage

Je Userstory legt `required_across_story` die Zielknoten fest. Ein Zielknoten
gilt als erreicht, wenn er im Pfad mindestens eines Testfalls vorkommt, der kein
Berechtigungstest mit verweigertem Zugriff ist.

### ID-Text Consistency

Ein Schritt widerspricht seiner `ui_node_id`, wenn sein Text einen Knoten einer
anderen Konsole nennt und den eigenen nicht.

| `ui_node_id` | Schritt-Text | Ergebnis |
|---|---|---|
| `CONSOLE-C` (Coordination) | „Open Coordination.“ | konsistent |
| `CONSOLE-C` (Coordination) | „Open the console for team coordination.“ | konsistent, kein Knoten genannt |
| `CONSOLE-C` (Coordination) | „Open Operations.“ | Widerspruch |
| `EL-TM-ACTION-ID` | „Click the SM Action ID Link.“ | Widerspruch |

Eine freie Umschreibung ist also nie ein Fehler. Knotennamen werden als ganze
Wörter und mit Groß- und Kleinschreibung gesucht, weil Namen wie „Calendar“ oder
„Performance“ auch gewöhnliche Wörter sind.

Grenzen: Verwechslungen innerhalb derselben Konsole werden nicht erkannt.

### Console Naming

Geprüft wird, ob der Text irgendeines Schritts eines Testfalls den Namen der
Konsole nennt, mit der der Basispfad beginnt. Die `ui_node_id` wird nicht
gelesen. Damit ist dies die einzige Navigationsmetrik, die für beide Varianten
gleich berechnet wird, und die Grundlage für den Vergleich der Navigation mit
und ohne UI-Kontext.

Grenzen: Der Name der Konsole steht in keiner Userstory (außer in US-25, die
die Navigationsleiste selbst beschreibt). Ohne UI-Kontext kann das Modell ihn
nur erraten. Die Metrik misst also genau dieses fehlende Wissen und nicht die
Qualität der Navigation insgesamt.

## Nachvollziehbarkeit

Der Checkpoint eines Bulk-Laufs enthält:

- unter `settings` die Modelle, Parameter und Prüfsummen (SHA-256) von Prompts,
  UI-Kontext und Soll-Navigation;
- je Lauf unter `generation` Zeitpunkt, angefragtes und antwortendes Modell,
  Temperatur, Tokenverbrauch, Zahl der Versuche und die unveränderte
  Modellantwort;
- je Judge-Urteil Zeitpunkt, Modell, Urteil und Begründung.

## Wo man was ändert

- **Prompts:** die beiden Textdateien in `prompts/`.
- **Modelle und Parameter:** `testcase_generator/config.py`.
- **Userstories, UI-Kontext, Soll-Navigation:** die Dateien in `data/`.

## Bulk-Lauf und Checkpoints

Ein Bulk-Lauf generiert jede Userstory je Variante mehrfach und wertet alle
Ausgaben aus. Der Zwischenstand wird nach jeder Generierung und jedem
Judge-Aufruf in `.bulk_checkpoints/` gespeichert. Ein abgebrochener Lauf setzt
dort fort, ohne bezahlte Aufrufe zu wiederholen.

Was nach einer Änderung passiert:

| Geändert | Folge beim nächsten Lauf |
|---|---|
| Userstories, UI-Kontext, Generator-Prompt, Generator-Modell oder -Parameter | neuer Checkpoint, alles wird neu generiert |
| Judge-Prompt oder Judge-Modell | Generierungen bleiben, alle Kriterien werden neu beurteilt |
| Soll-Navigation oder Auswertungslogik | Generierungen und Urteile bleiben, Metriken werden neu berechnet |

Gespeicherte Läufe lassen sich über die Oberfläche hochladen und ohne neue
Generierung anzeigen oder erneut auswerten. Das gilt auch für Checkpoints
früherer Fassungen der Anwendung.

## Tests

```bash
pip install pytest
pytest
```

Die Tests laufen ohne API-Zugriff; das Modell wird durch feste Antworten ersetzt.
