from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from app import TripCandidate, UserPreferences, recommend_trips, sample_data

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "f1_tracker.db"
WEB_DIR = BASE_DIR / "web"

CITY_META: dict[str, dict[str, Any]] = {
    "Milan": {"lat": 45.4642, "lon": 9.19, "country_code": "IT"},
    "Nagoya": {"lat": 35.1815, "lon": 136.9066, "country_code": "JP"},
    "Barcelona": {"lat": 41.3874, "lon": 2.1686, "country_code": "ES"},
}


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
                    context_json TEXT NOT NULL,
                    FOREIGN KEY (draft_id) REFERENCES trip_drafts(id)
                )
                """
            )
            try:
                conn.execute("ALTER TABLE recommendations ADD COLUMN context_json TEXT NOT NULL DEFAULT '{}' ")
            except sqlite3.OperationalError:
                # Column already exists in newer databases.
                pass

    def create_draft(self, payload: dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO trip_drafts(created_at, updated_at, status, input_json) VALUES(?,?,?,?)",
                (now, now, "draft", json.dumps(payload)),
            )
            return int(cur.lastrowid)

    def list_drafts(self, limit: int = 15) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trip_drafts ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "status": row["status"],
                    "input": json.loads(row["input_json"]),
                }
                for row in rows
            ]

    def get_draft(self, draft_id: int) -> dict[str, Any] | None:
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

    def save_recommendation(self, draft_id: int, result: list[dict[str, Any]], context: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recommendations(draft_id, generated_at, result_json, context_json) VALUES(?,?,?,?)",
                (draft_id, datetime.now(timezone.utc).isoformat(), json.dumps(result), json.dumps(context)),
            )

    def get_latest_recommendation(self, draft_id: int) -> dict[str, Any] | None:
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
                "context": json.loads(row["context_json"] or "{}"),
                "recommendations": json.loads(row["result_json"]),
            }


def fetch_json(url: str) -> Any:
    with urlopen(url, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def lookup_next_holiday(country_code: str) -> dict[str, Any] | None:
    try:
        data = fetch_json(f"https://date.nager.at/api/v3/NextPublicHolidays/{country_code}")
        return data[0] if data else None
    except Exception:
        return None


def lookup_weather_forecast(lat: float, lon: float) -> dict[str, Any] | None:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_probability_mean"
        "&forecast_days=1&timezone=auto"
    )
    try:
        payload = fetch_json(url)
        daily = payload.get("daily", {})
        return {
            "temp_c": int(round((daily.get("temperature_2m_max") or [22])[0])),
            "rain_probability": float((daily.get("precipitation_probability_mean") or [20])[0]) / 100.0,
        }
    except Exception:
        return None


def apply_live_context(trip: TripCandidate) -> tuple[TripCandidate, dict[str, Any]]:
    meta = CITY_META.get(trip.city, {})
    holiday = lookup_next_holiday(meta.get("country_code", "")) if meta else None
    weather = lookup_weather_forecast(meta["lat"], meta["lon"]) if meta else None

    holiday_days = trip.holiday_days
    if holiday:
        holiday_date = datetime.fromisoformat(holiday["date"]).date()
        if holiday_date.weekday() in {0, 4}:  # Monday or Friday gives better long-weekend leverage
            holiday_days = max(holiday_days, trip.holiday_days + 1)

    adjusted = replace(
        trip,
        holiday_days=holiday_days,
        avg_temp_c=weather["temp_c"] if weather else trip.avg_temp_c,
        rain_probability=weather["rain_probability"] if weather else trip.rain_probability,
    )

    context = {
        "city": trip.city,
        "holiday": holiday,
        "weather": weather,
        "holiday_live": holiday is not None,
        "weather_live": weather is not None,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "live_sources": {
            "holiday_api": "https://date.nager.at",
            "weather_api": "https://open-meteo.com",
            "flight_hotel_source": "phase3_estimator_v1",
        },
    }
    return adjusted, context


def enrich_trip_market_costs(trip: TripCandidate, style: str) -> TripCandidate:
    style_factor = {"budget": 0.92, "balanced": 1.0, "premium": 1.18}.get(style, 1.0)
    month_factor = 1.0 + ((trip.race_date.month % 4) * 0.03)
    adjusted_flight = int(trip.flight_cost * style_factor * month_factor)
    adjusted_hotel = int(trip.hotel_cost * style_factor * month_factor)
    return replace(trip, flight_cost=adjusted_flight, hotel_cost=adjusted_hotel)


def build_user_preferences(user_input: dict[str, Any]) -> UserPreferences:
    return UserPreferences(
        home_airport=str(user_input.get("home_airport", "LHR")).upper(),
        budget_eur=max(1, int(user_input.get("budget_eur", 1200))),
        style=valid_choice(str(user_input.get("style", "balanced")), {"budget", "balanced", "premium"}, "balanced"),
        weather_preference=valid_choice(
            str(user_input.get("weather_preference", "mixed")),
            {"cool", "warm", "mixed"},
            "mixed",
        ),
    )


def serialize_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in recommendations:
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
    return serialized


def valid_choice(value: str, options: set[str], default: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in options:
        return cleaned
    return default


class Handler(BaseHTTPRequestHandler):
    db = DraftDB(DB_PATH)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
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

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            return self._send_html((WEB_DIR / "index.html").read_bytes())

        if path == "/api/drafts":
            return self._send_json({"drafts": self.db.list_drafts()})

        if path.startswith("/api/drafts/"):
            try:
                draft_id = int(path.split("/")[-1])
            except ValueError:
                return self._send_json({"error": "Invalid draft id"}, HTTPStatus.BAD_REQUEST)
            draft = self.db.get_draft(draft_id)
            if not draft:
                return self._send_json({"error": "Draft not found"}, HTTPStatus.NOT_FOUND)
            return self._send_json(draft)

        if path.startswith("/api/recommendations/"):
            try:
                draft_id = int(path.split("/")[-1])
            except ValueError:
                return self._send_json({"error": "Invalid draft id"}, HTTPStatus.BAD_REQUEST)
            rec = self.db.get_latest_recommendation(draft_id)
            if not rec:
                return self._send_json({"error": "Recommendation not found"}, HTTPStatus.NOT_FOUND)
            return self._send_json(rec)

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

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

            user = build_user_preferences(draft["input"])
            context: dict[str, Any] = {"city_context": []}
            live_trips: list[TripCandidate] = []
            for trip in sample_data():
                with_live, city_context = apply_live_context(trip)
                market = enrich_trip_market_costs(with_live, user.style)
                live_trips.append(market)
                context["city_context"].append(city_context)

            recommendations = recommend_trips(user, live_trips)
            serialized = serialize_recommendations(recommendations)
            city_context = context.get("city_context", [])
            context["live_data_summary"] = {
                "holiday_live_cities": sum(1 for c in city_context if c.get("holiday_live")),
                "weather_live_cities": sum(1 for c in city_context if c.get("weather_live")),
                "total_cities": len(city_context),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            self.db.save_recommendation(draft_id, serialized, context)
            return self._send_json(
                {"draft_id": draft_id, "context": context, "recommendations": serialized},
                HTTPStatus.OK,
            )

        return self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def run() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8765), Handler)
    print("F1 tracker web app running at http://localhost:8765")
    server.serve_forever()


if __name__ == "__main__":
    run()
