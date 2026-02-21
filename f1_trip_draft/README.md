# PlanWise Travel Planner

`PlanWise Travel Planner` is the new product name.

## What's improved
- Removed race/F1 visual branding and redesigned with a clean, neutral travel-planning UI.
- Added clear visual hierarchy, spacing, readable typography, and accessibility-focused color contrast.
- Kept airport/place listing and multi-currency budget support.

## Core capabilities
- `GET /api/metadata` returns:
  - supported airports
  - destination places
  - supported currencies
- Multi-currency budget input (`budget_amount` + `currency`) with EUR normalization for internal scoring.
- Live data integrations:
  - Holidays: `date.nager.at`
  - Weather: `open-meteo.com`
  - FX: `frankfurter.app`

## Run
```bash
python3 f1_trip_draft/webapp.py
```
Open: `http://localhost:8765`

## APIs
- `GET /api/metadata`
- `POST /api/drafts`
- `GET /api/drafts`
- `POST /api/recommendations/generate`
- `GET /api/recommendations/{draft_id}`
