# PlanWise F1 Weekend Planner

A dark, Formula-1 themed travel planning web app inspired by modern motorsport UI aesthetics.

## What this version adds
- Full dark F1-themed frontend redesign.
- Live F1 feed integration (next race) via Ergast-compatible APIs.
- Existing real-time data remains in place:
  - Public holidays (`date.nager.at`)
  - Weather (`open-meteo.com`)
  - FX conversion (`frankfurter.app`)

## Run
```bash
python3 f1_trip_draft/webapp.py
```
Open: `http://localhost:8765`

## APIs
- `GET /api/metadata` (airports, places, currencies, live F1 next race)
- `POST /api/drafts`
- `GET /api/drafts`
- `POST /api/recommendations/generate`
- `GET /api/recommendations/{draft_id}`

## Notes
If a live provider fails, the app gracefully falls back and marks status in the UI context pills.
