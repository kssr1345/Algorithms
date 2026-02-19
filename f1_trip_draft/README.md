# F1 Travel Tracker (Website + Backend Draft)

This draft now includes:
- a simple **website frontend**,
- a **Python backend**,
- a **database** that stores user input drafts and recommendation snapshots.

## 1) Run the website

```bash
python3 f1_trip_draft/webapp.py
```

Then open: `http://localhost:8765`

## 2) How to use

1. Fill in your profile (airport, budget, style, weather).
2. Click **Save Draft + Generate**.
3. The app will:
   - save your input in the database as a draft,
   - generate F1 trip recommendations,
   - show the ranked results on the page.

## 3) Database behavior (draft copy)

Database file: `f1_trip_draft/f1_tracker.db`

Stored tables:
- `trip_drafts`: user-entered draft profile data
- `recommendations`: generated recommendation snapshots by draft

This supports your requirement to keep user data and draft copies.

## 4) Project files

- `f1_trip_draft/webapp.py` — HTTP server + API endpoints + SQLite storage
- `f1_trip_draft/web/index.html` — website frontend UI
- `f1_trip_draft/app.py` — core recommendation logic (scoring/ranking)

## 5) API endpoints

- `POST /api/drafts` - save draft input
- `GET /api/drafts/{id}` - fetch saved draft
- `POST /api/recommendations/generate` - generate recommendations for a draft
- `GET /api/recommendations/{draft_id}` - fetch latest recommendations for a draft

## 6) About Python + C++

Current draft uses Python end-to-end.

Planned C++ usage (next step):
- move only heavy ranking/optimization loops to C++ for performance,
- keep APIs, database, and orchestration in Python.

This keeps development simple now and still allows high-performance scaling later.
