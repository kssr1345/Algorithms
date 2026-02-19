# F1 Travel Tracker (Draft MVP)

This is a draft prototype for an app that recommends F1-themed trips by combining:

- public holiday windows,
- month + weather suitability,
- flight + hotel costs,
- and budget strategy guidance (save vs splurge).

## What is implemented in this draft

1. **Recommendation scoring engine** in `app.py`.
2. **Weighted ranking** for budget/balanced/premium traveler profiles.
3. **Sample trip candidates** for Monza, Suzuka, and Barcelona.
4. **Cost-aware filtering** that avoids strongly over-budget recommendations.
5. **Actionable save/splurge tips** attached to each recommendation.

## Scoring model

For each candidate trip:

`Total = Value*w1 + F1Experience*w2 + WeatherFit*w3 + Convenience*w4 + Rating*w5`

Where weights depend on user style:

- **budget**: prioritize value,
- **balanced**: equal value and experience,
- **premium**: prioritize F1 experience + rating.

## Run locally

```bash
python3 f1_trip_draft/app.py
```

Expected output: top-ranked recommendations with total cost, experience score, subscores, and one save/splurge suggestion.

## Next steps to turn draft into full app

- Integrate real APIs for holiday calendar, weather, flights, and hotels.
- Add an HTTP API (e.g., FastAPI) and frontend dashboard.
- Implement price tracking alerts and booking-window recommendations.
- Add explainability endpoint: "Why this trip is ranked #1".
- Add user accounts and persistence (PostgreSQL).
