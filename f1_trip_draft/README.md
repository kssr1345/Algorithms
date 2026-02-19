# F1 Travel Tracker (Draft MVP)

If you are completely new, start here 👇

## Quick start (3 steps)

1. Open terminal in this repo.
2. Run:

```bash
python3 f1_trip_draft/app.py
```

3. Answer the questions (or just press `Enter` to use defaults).

That is it. The script will print your top F1-themed trip options.

## What the app asks you

- **Home airport code** (example: `LHR`)
- **Budget in EUR** (example: `1200`)
- **Travel style**
  - `budget` = save more money
  - `balanced` = mix of value + experience
  - `premium` = prioritize best F1 experience
- **Weather preference**
  - `cool`, `warm`, or `mixed`

## Understanding output

For each recommendation, you will see:

- estimated total cost,
- overall experience score,
- sub-scores (value, F1, weather, convenience, hotel rating),
- one **save money** tip,
- one **spend for experience** tip.

## What is implemented in this draft

1. Interactive CLI onboarding for beginners.
2. Recommendation scoring engine in `app.py`.
3. Weighted ranking for `budget` / `balanced` / `premium` styles.
4. Sample trip candidates: Monza, Suzuka, Barcelona.
5. Cost-aware filtering for highly over-budget trips.

## Scoring model

`Total = Value*w1 + F1Experience*w2 + WeatherFit*w3 + Convenience*w4 + Rating*w5`

Weight examples:

- **budget**: higher value weight.
- **balanced**: value and experience equally weighted.
- **premium**: higher F1 and quality weight.

## Current limitation

This is a **draft** with sample data (not live API data yet).

## Next steps (production version)

- Connect public holiday APIs.
- Connect weather + flight + hotel APIs.
- Add web UI (FastAPI + frontend).
- Add alerts for price drops and best booking window.
- Add account storage in PostgreSQL.
