from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app import UserPreferences, recommend_trips, sample_data

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "f1_tracker.db"
WEB_DIR = BASE_DIR / "web"


class DraftDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    FOREIGN KEY (draft_id) REFERENCES trip_drafts(id)
                )
                """
            )

    def create_draft(self, payload: dict) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO trip_drafts(created_at, updated_at, status, input_json) VALUES(?,?,?,?)",
                (now, now, "draft", json.dumps(payload)),
            )
            return int(cur.lastrowid)

    def get_draft(self, draft_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM trip_drafts WHERE id=?", (draft_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "status": row["status"],
                "input": json.loads(row["input_json"]),
            }

    def save_recommendation(self, draft_id: int, result: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recommendations(draft_id, generated_at, result_json) VALUES(?,?,?)",
                (draft_id, datetime.utcnow().isoformat(), json.dumps(result)),
            )

    def get_latest_recommendation(self, draft_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM recommendations WHERE draft_id=? ORDER BY generated_at DESC LIMIT 1",
                (draft_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "draft_id": draft_id,
                "generated_at": row["generated_at"],
                "recommendations": json.loads(row["result_json"]),
            }


def valid_choice(value: str, options: set[str], default: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in options:
        return cleaned
    return default


class Handler(BaseHTTPRequestHandler):
    db = DraftDB(DB_PATH)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            index_file = WEB_DIR / "index.html"
            return self._send_html(index_file.read_bytes())

        if path.startswith("/api/drafts/"):
            draft_id = int(path.split("/")[-1])
            draft = self.db.get_draft(draft_id)
            if not draft:
                return self._send_json({"error": "Draft not found"}, HTTPStatus.NOT_FOUND)
            return self._send_json(draft)

        if path.startswith("/api/recommendations/"):
            draft_id = int(path.split("/")[-1])
            rec = self.db.get_latest_recommendation(draft_id)
            if not rec:
                return self._send_json({"error": "Recommendation not found"}, HTTPStatus.NOT_FOUND)
            return self._send_json(rec)

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/drafts":
            payload = self._read_json_body()
            draft_id = self.db.create_draft(payload)
            return self._send_json({"draft_id": draft_id}, HTTPStatus.CREATED)

        if parsed.path == "/api/recommendations/generate":
            payload = self._read_json_body()
            draft_id = int(payload.get("draft_id", 0))
            draft = self.db.get_draft(draft_id)
            if not draft:
                return self._send_json({"error": "Draft not found"}, HTTPStatus.NOT_FOUND)

            user_input = draft["input"]
            user = UserPreferences(
                home_airport=user_input.get("home_airport", "LHR").upper(),
                budget_eur=max(1, int(user_input.get("budget_eur", 1200))),
                style=valid_choice(user_input.get("style", "balanced"), {"budget", "balanced", "premium"}, "balanced"),
                weather_preference=valid_choice(
                    user_input.get("weather_preference", "mixed"),
                    {"cool", "warm", "mixed"},
                    "mixed",
                ),
            )

            recs = recommend_trips(user, sample_data())
            serialized = []
            for item in recs:
                trip = asdict(item["trip"])
                trip["race_date"] = str(trip["race_date"])
                serialized.append(
                    {
                        "trip": trip,
                        "scores": item["scores"],
                        "experience_score": item["experience_score"],
                        "save_tips": item["save_tips"],
                        "splurge_tips": item["splurge_tips"],
                    }
                )

            self.db.save_recommendation(draft_id, serialized)
            return self._send_json({"draft_id": draft_id, "recommendations": serialized}, HTTPStatus.OK)

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def run() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8765), Handler)
    print("F1 tracker web app running at http://localhost:8765")
    server.serve_forever()


if __name__ == "__main__":
    run()
