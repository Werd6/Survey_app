# BeeWare Survey App (Toga)

This repo contains the core source files for a BeeWare (Toga) mobile survey app. It shows one agree/disagree question at a time, saves answers locally across restarts, and displays results after completion.

## Run with BeeWare (recommended)

1. Install prerequisites (macOS):
   - Xcode (for iOS), Android Studio (for Android)
   - Python 3.10–3.12
   - `pipx`: `python3 -m pip install --user pipx && pipx ensurepath`
   - `briefcase`: `pipx install briefcase`

2. Create a new Briefcase app skeleton:
   ```bash
   briefcase new
   ```
   - Choose a Toga app
   - Fill in metadata (App Name: Survey, Bundle: org.example, Formal Name: Survey, etc.)

3. Copy this repo's `src/survey_app/` into the generated project's `src/<your_app_package>/` (or rename the package there to `survey_app`). Ensure the `main()` in `src/survey_app/__init__.py` is used by `pyproject.toml` as the app factory.

4. Run locally for desktop preview:
   ```bash
   briefcase dev
   ```

5. Android build:
   ```bash
   briefcase create android
   briefcase build android
   briefcase run android
   ```

6. iOS build:
   ```bash
   briefcase create iOS
   # Then open the Xcode project generated under `iOS/` and run
   ```

## Source layout

- `src/survey_app/__init__.py` — `main()` returning `SurveyApp`
- `src/survey_app/app.py` — UI, controller, persistence wiring
- `src/survey_app/questions.py` — hardcoded questions list
- `src/survey_app/storage.py` — JSON load/save helpers

## Data format

Answers are stored at `app.paths.data / responses.json` as:
```json
{
  "q1": ["Cats are better than dogs", true],
  "q2": ["Pineapple belongs on pizza", false]
}
```

## Notes
- To change questions, edit `src/survey_app/questions.py`.
- Use the Results screen’s Restart button to clear saved answers.


