from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Dict


@dataclass
class UserPreferences:
    home_airport: str
    budget_eur: int
    style: str  # budget, balanced, premium
    weather_preference: str  # cool, warm, mixed


@dataclass
class TripCandidate:
    name: str
    country: str
    city: str
    race_date: date
    holiday_days: int
    avg_temp_c: int
    rain_probability: float
    flight_cost: int
    hotel_cost: int
    local_cost: int
    hotel_rating: float
    flight_hours: float
    transfer_minutes: int
    f1_experience_points: int

    @property
    def total_cost(self) -> int:
        return self.flight_cost + self.hotel_cost + self.local_cost


def weather_fit(pref: str, temp: int, rain_probability: float) -> float:
    rain_penalty = max(0.0, rain_probability - 0.25) * 25
    if pref == "cool":
        temp_score = max(0, 100 - abs(temp - 18) * 4)
    elif pref == "warm":
        temp_score = max(0, 100 - abs(temp - 27) * 4)
    else:
        temp_score = max(0, 100 - abs(temp - 22) * 3)
    return max(0, temp_score - rain_penalty)


def value_score(total_cost: int, exp_points: int) -> float:
    if total_cost <= 0:
        return 0.0
    ratio = exp_points / total_cost
    return min(100.0, ratio * 2500)


def convenience_score(hours: float, transfer_minutes: int, holiday_days: int) -> float:
    travel_penalty = (hours * 6) + (transfer_minutes / 6)
    holiday_bonus = holiday_days * 7
    return max(0.0, min(100.0, 85 + holiday_bonus - travel_penalty))


def rating_quality(hotel_rating: float) -> float:
    return max(0.0, min(100.0, (hotel_rating / 5.0) * 100))


def style_weights(style: str) -> Dict[str, float]:
    if style == "budget":
        return {"value": 0.35, "f1": 0.2, "weather": 0.15, "convenience": 0.15, "rating": 0.15}
    if style == "premium":
        return {"value": 0.15, "f1": 0.35, "weather": 0.15, "convenience": 0.15, "rating": 0.2}
    return {"value": 0.25, "f1": 0.25, "weather": 0.2, "convenience": 0.15, "rating": 0.15}


def recommend_trips(user: UserPreferences, trips: List[TripCandidate]) -> List[Dict]:
    weights = style_weights(user.style)
    recommendations = []

    for trip in trips:
        if trip.total_cost > user.budget_eur * 1.25:
            # skip aggressively over-budget options for a cleaner draft output
            continue

        scores = {
            "value": value_score(trip.total_cost, trip.f1_experience_points),
            "f1": min(100.0, float(trip.f1_experience_points)),
            "weather": weather_fit(user.weather_preference, trip.avg_temp_c, trip.rain_probability),
            "convenience": convenience_score(trip.flight_hours, trip.transfer_minutes, trip.holiday_days),
            "rating": rating_quality(trip.hotel_rating),
        }

        weighted_total = (
            scores["value"] * weights["value"]
            + scores["f1"] * weights["f1"]
            + scores["weather"] * weights["weather"]
            + scores["convenience"] * weights["convenience"]
            + scores["rating"] * weights["rating"]
        )

        recommendations.append(
            {
                "trip": trip,
                "scores": scores,
                "experience_score": round(weighted_total, 2),
                "save_tips": [
                    "Book flight mid-week and arrive Thursday to cut fare spikes.",
                    "Choose hotels 3-7 km from circuit with public transport access.",
                ],
                "splurge_tips": [
                    "Upgrade race-day seat (best ROI for core F1 experience).",
                    "Book one premium activity: simulator, paddock tour, or track walk.",
                ],
            }
        )

    recommendations.sort(key=lambda x: x["experience_score"], reverse=True)
    return recommendations


def sample_data() -> List[TripCandidate]:
    return [
        TripCandidate(
            name="Monza Long Weekend",
            country="Italy",
            city="Milan",
            race_date=date(2026, 9, 6),
            holiday_days=3,
            avg_temp_c=24,
            rain_probability=0.28,
            flight_cost=260,
            hotel_cost=420,
            local_cost=230,
            hotel_rating=4.4,
            flight_hours=2.1,
            transfer_minutes=55,
            f1_experience_points=88,
        ),
        TripCandidate(
            name="Suzuka Experience Week",
            country="Japan",
            city="Nagoya",
            race_date=date(2026, 4, 5),
            holiday_days=5,
            avg_temp_c=19,
            rain_probability=0.34,
            flight_cost=920,
            hotel_cost=620,
            local_cost=350,
            hotel_rating=4.6,
            flight_hours=13.2,
            transfer_minutes=120,
            f1_experience_points=96,
        ),
        TripCandidate(
            name="Barcelona Spring GP",
            country="Spain",
            city="Barcelona",
            race_date=date(2026, 5, 31),
            holiday_days=4,
            avg_temp_c=23,
            rain_probability=0.2,
            flight_cost=210,
            hotel_cost=390,
            local_cost=200,
            hotel_rating=4.3,
            flight_hours=2.0,
            transfer_minutes=50,
            f1_experience_points=84,
        ),
    ]


def print_recommendations(recos: List[Dict]) -> None:
    print("Top F1-themed trip recommendations\n")
    for idx, item in enumerate(recos[:3], start=1):
        trip = item["trip"]
        print(f"{idx}. {trip.name} ({trip.city}, {trip.country})")
        print(f"   Total cost: €{trip.total_cost} | Experience score: {item['experience_score']}")
        print(
            f"   Subscores -> Value: {item['scores']['value']:.1f}, "
            f"F1: {item['scores']['f1']:.1f}, Weather: {item['scores']['weather']:.1f}, "
            f"Convenience: {item['scores']['convenience']:.1f}, Rating: {item['scores']['rating']:.1f}"
        )
        print(f"   Save: {item['save_tips'][0]}")
        print(f"   Splurge: {item['splurge_tips'][0]}\n")


def main() -> None:
    user = UserPreferences(
        home_airport="LHR",
        budget_eur=1200,
        style="balanced",
        weather_preference="mixed",
    )
    recommendations = recommend_trips(user, sample_data())
    print_recommendations(recommendations)


if __name__ == "__main__":
    main()
