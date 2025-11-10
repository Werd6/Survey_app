# Survey App - Mobile Question & Answer App

A mobile survey app built with BeeWare (Toga) that supports multiple question sets, tracks contradictions and requirements between answers, and provides a TruthWeb visualization.

## Features

- **Multiple Question Sets**: Select from different question sets (e.g., Superheroes, Food)
- **Contradiction Detection**: Automatically detects when you agree with contradictory statements
- **Contradiction Resolution**: Interactive flow to resolve contradictory answers
- **TruthWeb Visualization**: Graphical representation of your answers showing contradictions (red) and requirements (green)
- **Persistent Storage**: Answers are saved locally and persist across app restarts
- **Interactive Graph**: Click on nodes in the TruthWeb to see question details

## Building and Running

### Prerequisites
- Python 3.10–3.12
- `pipx`: `python3 -m pip install --user pipx && pipx ensurepath`
- `briefcase`: `pipx install briefcase`
- Android Studio (for Android builds)

### Build for Android

```bash
# Create Android project
briefcase create android

# Build APK
briefcase build android

# Run on emulator or device
briefcase run android
```

### Run locally (desktop preview)

```bash
briefcase dev
```

## Source layout

- `survey_app/__init__.py` — `main()` returning `SurveyApp`
- `survey_app/app.py` — UI, controller, persistence wiring, contradiction resolution
- `survey_app/questions.py` — Question sets with relationships (contradicts, requires)
- `survey_app/storage.py` — JSON load/save helpers
- `survey_app/truth_web.py` — TruthWeb visualization (deprecated, now in app.py)

## Data format

Answers are stored per question set at `app.paths.data / responses_{question_set_name}.json` as:
```json
{
  "q1": ["Question text", true],
  "q2": ["Question text", false]
}
```

## Notes

- To add new question sets, edit `survey_app/questions.py` and add to `QUESTION_SETS` dictionary
- To modify questions, edit `survey_app/questions.py`
- Use the Results screen's Restart button to clear saved answers
- The TruthWeb visualization shows contradictions as red lines and requirements as green lines
