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
  config.py                   Pfade, Modelle, Parameter, Varianten
  resources.py                Laden der Eingabedateien, OpenAI-Client
  ui_model.py                 Datenmodell des UI-Kontexts
  generation.py               Generierung und Verarbeitung der Modellantwort
  evaluation/
    ac_coverage.py            Acceptance Criteria Coverage (LLM-as-a-Judge)
    role_coverage.py          Role Coverage
    navigation.py             Navigation Path Correctness, Target Node Coverage
    text.py                   Textaufbereitung für die regelbasierten Metriken
  experiment.py               Bulk-Lauf, Neuauswertung, Zusammenfassungen
  checkpoints.py              Zwischenstände eines Bulk-Laufs
  pdf_report.py               PDF-Export
  ui/                         Abschnitte der Oberfläche
tests/                        Automatische Tests
```

## Metriken

| Metrik | Varianten | Berechnung |
|---|---|---|
| Acceptance Criteria Coverage | beide | Ein zweites Modell beurteilt je Akzeptanzkriterium, ob es durch die Testfälle abgedeckt ist. |
| Role Coverage | beide | Anteil der in der Userstory genannten Rollen, für die ein Login-Schritt vorkommt. |
| Navigation Path Correctness | mit UI-Kontext | Anteil der Testfälle, deren `ui_node_id`-Pfad den Basispfad (`required_per_testcase`) in der richtigen Reihenfolge enthält. |
| Target Node Coverage | mit UI-Kontext | Anteil der Zielknoten (`required_across_story`), die mindestens ein Testfall erreicht. |

## Wo man was ändert

- **Prompts:** die beiden Textdateien in `prompts/`. Nach einer Änderung des
  Judge-Prompts `JUDGE_VERSION` in `config.py` erhöhen, damit gespeicherte
  Urteile nicht wiederverwendet werden.
- **Modelle und Parameter:** `testcase_generator/config.py`.
- **Userstories, UI-Kontext, Soll-Navigation:** die Dateien in `data/`.

## Bulk-Lauf und Checkpoints

Ein Bulk-Lauf generiert jede Userstory je Variante mehrfach und wertet alle
Ausgaben aus. Der Zwischenstand wird nach jeder Generierung und jedem
Judge-Aufruf in `.bulk_checkpoints/` gespeichert. Ein abgebrochener Lauf setzt
dort fort, ohne bezahlte Aufrufe zu wiederholen.

Ein Checkpoint wird an Userstories, Wiederholungszahl und Modellnamen
wiedererkannt. UI-Kontext, Soll-Navigation und Prompts gehören nicht dazu:
Nach einer Änderung daran den Checkpoint in der Oberfläche löschen
(„Clear saved checkpoint“), sonst wird der alte Lauf fortgesetzt.

Gespeicherte Läufe lassen sich über die Oberfläche hochladen und ohne neue
Generierung erneut auswerten.

## Tests

```bash
pip install pytest
pytest
```

Die Tests laufen ohne API-Zugriff; das Modell wird durch feste Antworten ersetzt.
