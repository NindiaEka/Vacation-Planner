"""Travel option generation with autonomous calendar and budget scaling.

References:
- data/user_calendar.json (calendar availability source)
- src/tools/flight_search.py (mock flight pricing/search)
- src/tools/hotel_booking.py (mock hotel pricing/booking)
"""

import json
import os
from datetime import date, timedelta
from typing import Optional

from tools import flight_search, hotel_booking


def _derive_spendable_budget(total_budget: int) -> tuple[int, int]:
    safe_total = max(int(total_budget), 1_500_000)
    reserve_budget = max(int(safe_total * 0.15), 750_000)
    max_allowed_reserve = int(safe_total * 0.30)
    reserve_budget = min(reserve_budget, max_allowed_reserve)
    spendable_budget = max(safe_total - reserve_budget, int(safe_total * 0.60))
    return spendable_budget, reserve_budget


def _load_calendar_availability() -> set[date]:
    calendar_path = os.getenv("USER_CALENDAR_PATH", "data/user_calendar.json")
    try:
        with open(calendar_path, "r", encoding="utf-8") as file:
            raw_calendar = json.load(file)
    except Exception:
        raw_calendar = {}

    available_dates: set[date] = set()
    for raw_date, status in raw_calendar.items():
        if str(status).lower() != "available":
            continue
        try:
            available_dates.add(date.fromisoformat(raw_date))
        except ValueError:
            continue
    return available_dates


def _parse_anchor_date(preferred_start_date: Optional[str | date]) -> date:
    if isinstance(preferred_start_date, date):
        return preferred_start_date
    if isinstance(preferred_start_date, str):
        try:
            return date.fromisoformat(preferred_start_date)
        except ValueError:
            pass
    return date.today()


def _find_first_three_gaps(available_dates: set[date], gap_days: int, anchor_date: date) -> list[tuple[date, date]]:
    sorted_candidates = sorted(d for d in available_dates if d >= anchor_date)
    gaps: list[tuple[date, date]] = []

    for start_date in sorted_candidates:
        is_consecutive_gap = all((start_date + timedelta(days=offset)) in available_dates for offset in range(gap_days))
        if is_consecutive_gap:
            end_date = start_date + timedelta(days=gap_days - 1)
            gaps.append((start_date, end_date))
        if len(gaps) == 3:
            return gaps

    fallback_start = sorted_candidates[-1] + timedelta(days=1) if sorted_candidates else anchor_date
    while len(gaps) < 3:
        end_date = fallback_start + timedelta(days=gap_days - 1)
        gaps.append((fallback_start, end_date))
        fallback_start = fallback_start + timedelta(days=gap_days)
    return gaps


def _target_total_by_tier(total_budget: int, tier_name: str) -> int:
    if tier_name == "hemat":
        return int(total_budget * 0.40)
    if tier_name == "standard":
        return int(total_budget * 0.70)

    premium_floor = int(total_budget * 0.85)
    premium_ceiling = int(total_budget * 0.95)
    premium_target = int(total_budget * 0.90)
    return max(premium_floor, min(premium_target, premium_ceiling))


def _scale_prices_to_target(
    flight_price: int,
    hotel_price: int,
    target_total: int,
    minimum_hotel_total: int,
) -> tuple[int, int, int]:
    raw_total = max(flight_price + hotel_price, 1)
    scaled_flight = int(flight_price * target_total / raw_total)
    scaled_hotel = target_total - scaled_flight

    if scaled_hotel < minimum_hotel_total:
        scaled_hotel = minimum_hotel_total
        scaled_flight = max(target_total - scaled_hotel, int(target_total * 0.2))

    total_price = scaled_flight + scaled_hotel
    return scaled_flight, scaled_hotel, total_price


def _apply_flight_class_and_discount(
    base_flight_price: int,
    flight_class: str,
    departure_date: date,
    destination: str,
) -> tuple[int, bool, int, int]:
    class_multiplier_map = {
        "economy": 1.0,
        "business": 2.7,
    }
    normalized_class = flight_class.lower()
    class_multiplier = class_multiplier_map.get(normalized_class, 1.0)

    economy_anchor = max(int(base_flight_price), 1_800_000)
    class_floor_before_discount = economy_anchor
    if normalized_class == "business":
        class_floor_before_discount = max(int(economy_anchor * 2.5), 4_500_000)

    class_adjusted_price = max(int(base_flight_price * class_multiplier), class_floor_before_discount)

    days_until_departure = max((departure_date - date.today()).days, 0)
    discount_applied = days_until_departure > 14
    if discount_applied:
        class_adjusted_price = int(class_adjusted_price * 0.9)

    minimum_fare = _minimum_flight_price(destination=destination, flight_class=flight_class)
    class_adjusted_price = max(class_adjusted_price, minimum_fare)

    return class_adjusted_price, discount_applied, days_until_departure, class_floor_before_discount


def _minimum_flight_price(destination: str, flight_class: str) -> int:
    normalized_destination = destination.strip().lower()
    normalized_class = flight_class.strip().lower()

    class_default_minimum = {
        "economy": 1_800_000,
        "business": 4_500_000,
    }
    minimum_price = class_default_minimum.get(normalized_class, 1_800_000)

    if normalized_destination in {"padang", "lombok"}:
        if normalized_class == "business":
            return max(minimum_price, 4_500_000)
        return max(minimum_price, 1_800_000)
    return minimum_price


def _normalize_hotel_total_price(raw_hotel_price: int, requested_nights: int, tier: str) -> int:
    nights = max(int(requested_nights), 1)
    tier_min_per_night = {
        "hemat": 300_000,
        "standard": 550_000,
        "premium": 1_200_000,
    }
    minimum_per_night = tier_min_per_night.get(tier, 300_000)
    quoted_per_night = max(int(raw_hotel_price / nights), minimum_per_night)
    return quoted_per_night * nights


def _validate_and_enforce_flight_hierarchy(
    options: list[dict],
    destination: str,
    requested_days: int,
    total_budget: int,
) -> list[dict]:
    standard_option = next((item for item in options if item.get("tier") == "standard"), None)
    premium_option = next((item for item in options if item.get("tier") == "premium"), None)

    if not standard_option or not premium_option:
        return options

    standard_flight_price = int(standard_option.get("flight_price", 0))
    required_premium_floor = max(
        int(standard_flight_price * 2.5),
        _minimum_flight_price(destination=destination, flight_class="Business"),
    )
    current_premium_flight = int(premium_option.get("flight_price", 0))

    if current_premium_flight < required_premium_floor:
        increase_needed = required_premium_floor - current_premium_flight
        current_hotel = int(premium_option.get("hotel_price", 0))
        minimum_hotel_total = max(int(requested_days), 1) * 250_000
        reducible_hotel = max(current_hotel - minimum_hotel_total, 0)
        moved_budget = min(reducible_hotel, increase_needed)

        premium_option["flight_price"] = current_premium_flight + moved_budget
        premium_option["hotel_price"] = current_hotel - moved_budget

        remaining_gap = increase_needed - moved_budget
        if remaining_gap > 0:
            premium_option["flight_price"] = int(premium_option.get("flight_price", 0)) + remaining_gap

        premium_option["total_price"] = int(premium_option.get("flight_price", 0)) + int(premium_option.get("hotel_price", 0))
        premium_option["hierarchy_adjusted"] = True
        premium_option["hierarchy_note"] = (
            "Premium flight price was automatically adjusted to be at least 2.5x Standard based on pricing validation."
        )
    else:
        premium_option["hierarchy_adjusted"] = False
        premium_option["hierarchy_note"] = "Premium flight price already meets the minimum 2.5x Standard validation."

    standard_hotel_price = int(standard_option.get("hotel_price", 0))
    current_premium_hotel = int(premium_option.get("hotel_price", 0))
    premium_luxury_floor = max(
        int(requested_days) * 1_200_000,
        standard_hotel_price + max(int(requested_days) * 75_000, 75_000),
    )
    premium_flight_price = int(premium_option.get("flight_price", 0))
    affordable_hotel_cap = max(int(total_budget) - premium_flight_price, int(requested_days) * 250_000)

    feasible_premium_hotel_floor = min(premium_luxury_floor, affordable_hotel_cap)

    if current_premium_hotel < feasible_premium_hotel_floor:
        premium_option["hotel_price"] = feasible_premium_hotel_floor
        premium_option["total_price"] = int(premium_option.get("flight_price", 0)) + feasible_premium_hotel_floor
        base_note = str(premium_option.get("hierarchy_note", "")).strip()
        premium_option["hierarchy_note"] = (
            f"{base_note} Premium hotel price was also raised to maintain luxury tier hierarchy."
        ).strip()

    if int(premium_option.get("total_price", 0)) > int(total_budget):
        reduced_hotel = max(int(total_budget) - int(premium_option.get("flight_price", 0)), int(requested_days) * 250_000)
        premium_option["hotel_price"] = reduced_hotel
        premium_option["total_price"] = int(premium_option.get("flight_price", 0)) + reduced_hotel
        base_note = str(premium_option.get("hierarchy_note", "")).strip()
        premium_option["hierarchy_note"] = (
            f"{base_note} Premium pricing was adjusted to stay within total budget cap."
        ).strip()

    return options


def _build_tier_justification(
    tier_label: str,
    destination: str,
    budget: int,
    reserve_budget: int,
    total_price: int,
    start_date: date,
    end_date: date,
    flight_discount_applied: bool,
) -> str:
    if tier_label.lower() == "premium" and flight_discount_applied:
        return (
            "Although flight tickets are cheaper due to early booking, the Premium total cost remains high "
            "because we selected the best 5-star resort for the user's requested destination. "
            f"Schedule {start_date.isoformat()} to {end_date.isoformat()} with an estimate of Rp{total_price:,} "
            f"from a budget of Rp{budget:,} for {destination}, while keeping Rp{reserve_budget:,} reserved "
            "for local transport, meals, and souvenirs."
        )

    return (
        f"{tier_label} is scheduled from {start_date.isoformat()} to {end_date.isoformat()} "
        f"because calendar availability is fully open, and the estimate of Rp{total_price:,} "
        f"is aligned with a total budget of Rp{budget:,} for the trip to {destination}, "
        f"while still leaving Rp{reserve_budget:,} as an on-ground expense reserve."
    )


def _apply_hotel_category_labels(options: list[dict], destination: str, requested_days: int) -> list[dict]:
    standard_option = next((item for item in options if item.get("tier") == "standard"), None)
    premium_option = next((item for item in options if item.get("tier") == "premium"), None)

    standard_hotel_price = int(standard_option.get("hotel_price", 0)) if standard_option else 0
    premium_hotel_price = int(premium_option.get("hotel_price", 0)) if premium_option else 0
    nights = max(int(requested_days), 1)
    premium_5star_floor = max(nights * 1_200_000, standard_hotel_price + 1)

    for option in options:
        tier = str(option.get("tier", "")).lower()
        option_nights = max(int(option.get("calendar_gap_days", requested_days)), 1)
        option_hotel_price = int(option.get("hotel_price", 0))
        per_night_price = int(option_hotel_price / option_nights)

        if tier == "hemat":
            option["hotel"] = f"2-3 Star Hotel in {destination} ({option_nights} nights) - budget"
        elif tier == "standard":
            if per_night_price >= 550_000:
                option["hotel"] = f"4-Star Hotel in {destination} ({option_nights} nights) - standard"
            else:
                option["hotel"] = f"2-3 Star Hotel in {destination} ({option_nights} nights) - standard"
        elif tier == "premium":
            if premium_hotel_price >= premium_5star_floor and per_night_price >= 1_200_000:
                option["hotel"] = f"5-Star Resort in {destination} ({option_nights} nights) - premium"
            elif option_hotel_price >= standard_hotel_price and per_night_price >= 550_000:
                option["hotel"] = f"4-Star Premium Hotel in {destination} ({option_nights} nights) - premium"
            else:
                option["hotel"] = f"2-3 Star Hotel in {destination} ({option_nights} nights) - premium (budget-constrained)"

    return options


def search_travel_options(destination="Bali", days=3, budget=None, preferred_start_date: Optional[str | date] = None):
    """
    Mock: Generate 3 flight + hotel combinations that fit the budget.
    """
    if budget is None:
        raise ValueError("budget is required")

    requested_days = max(int(days), 1)
    safe_budget = max(int(budget), 1_500_000)
    spendable_budget, reserve_budget = _derive_spendable_budget(safe_budget)
    tier_config = [
        {"name": "hemat", "label": "Budget", "flight_class": "Economy"},
        {"name": "standard", "label": "Standard", "flight_class": "Economy"},
        {"name": "premium", "label": "Premium", "flight_class": "Business"},
    ]
    anchor_date = _parse_anchor_date(preferred_start_date)
    available_dates = _load_calendar_availability()
    available_gaps = _find_first_three_gaps(
        available_dates=available_dates,
        gap_days=requested_days,
        anchor_date=anchor_date,
    )
    options = []

    for index, config in enumerate(tier_config, start=1):
        tier = config["name"]
        start_date, end_date = available_gaps[index - 1]
        travel_date = start_date.isoformat()
        target_total = _target_total_by_tier(total_budget=spendable_budget, tier_name=tier)
        flight_class = config["flight_class"]

        flight = flight_search.search(
            destination=destination,
            date=travel_date,
            budget=target_total,
            tier=tier,
        )
        hotel = hotel_booking.book(
            destination=destination,
            date=travel_date,
            budget=target_total,
            days=requested_days,
            tier=tier,
        )

        base_flight_price = int(flight.get("price", 0))
        flight_price, flight_discount_applied, days_until_departure, flight_price_floor_before_discount = _apply_flight_class_and_discount(
            base_flight_price=base_flight_price,
            flight_class=flight_class,
            departure_date=start_date,
            destination=destination,
        )
        hotel_price = _normalize_hotel_total_price(
            raw_hotel_price=int(hotel.get("price", 0)),
            requested_nights=requested_days,
            tier=tier,
        )
        minimum_hotel_total = requested_days * 250_000
        flight_price, hotel_price, total_price = _scale_prices_to_target(
            flight_price=flight_price,
            hotel_price=hotel_price,
            target_total=target_total,
            minimum_hotel_total=minimum_hotel_total,
        )

        minimum_route_fare = _minimum_flight_price(destination=destination, flight_class=flight_class)
        if flight_price < minimum_route_fare:
            fare_delta = minimum_route_fare - flight_price
            flight_price = minimum_route_fare
            hotel_price = max(hotel_price - fare_delta, minimum_hotel_total)
            total_price = flight_price + hotel_price

        if tier == "premium":
            standard_reference = next(
                (item for item in options if item.get("tier") == "standard"),
                None,
            )
            if standard_reference:
                required_business_floor = max(
                    int(int(standard_reference.get("flight_price", 0)) * 2.5),
                    _minimum_flight_price(destination=destination, flight_class="Business"),
                    int(flight_price_floor_before_discount * 0.9),
                )
                if flight_price < required_business_floor:
                    extra_flight_budget = required_business_floor - flight_price
                    flight_price = required_business_floor
                    hotel_price = max(hotel_price - extra_flight_budget, minimum_hotel_total)
                    total_price = flight_price + hotel_price

        if tier == "premium":
            minimum_premium_hotel = int(target_total * 0.65)
            if hotel_price < minimum_premium_hotel:
                hotel_price = minimum_premium_hotel
                flight_price = max(target_total - hotel_price, int(target_total * 0.15))
                total_price = flight_price + hotel_price

        display_tier = str(config["label"]).lower()

        options.append(
            {
                "id": f"option-{index}",
                "label": config["label"],
                "tier": tier,
                "flight_class": flight_class,
                "flight_discount_applied": flight_discount_applied,
                "days_until_departure": days_until_departure,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "calendar_gap_days": requested_days,
                "flight": f"{flight.get('flight')} - {flight_class} - Round Trip",
                "hotel": f"Hotel in {destination} ({requested_days} nights) - {display_tier}",
                "flight_price": flight_price,
                "hotel_price": hotel_price,
                "total_price": total_price,
                "justification": _build_tier_justification(
                    tier_label=config["label"],
                    destination=destination,
                    budget=safe_budget,
                    reserve_budget=reserve_budget,
                    total_price=total_price,
                    start_date=start_date,
                    end_date=end_date,
                    flight_discount_applied=flight_discount_applied,
                ),
            }
        )

    options = _validate_and_enforce_flight_hierarchy(
        options=options,
        destination=destination,
        requested_days=requested_days,
        total_budget=spendable_budget,
    )

    standard_option = next((item for item in options if item.get("tier") == "standard"), None)
    premium_option = next((item for item in options if item.get("tier") == "premium"), None)
    if standard_option and premium_option:
        standard_hotel_price = int(standard_option.get("hotel_price", 0))
        premium_hotel_price = int(premium_option.get("hotel_price", 0))
        if premium_hotel_price < standard_hotel_price:
            required_gap = standard_hotel_price - premium_hotel_price
            premium_flight_price = int(premium_option.get("flight_price", 0))
            business_floor = _minimum_flight_price(destination=destination, flight_class="Business")
            reducible_flight = max(premium_flight_price - business_floor, 0)
            transferred_budget = min(required_gap, reducible_flight)

            if transferred_budget > 0:
                premium_option["flight_price"] = premium_flight_price - transferred_budget
                premium_option["hotel_price"] = premium_hotel_price + transferred_budget
                premium_option["total_price"] = int(premium_option.get("flight_price", 0)) + int(premium_option.get("hotel_price", 0))
                premium_option["hierarchy_adjusted"] = True
                base_note = str(premium_option.get("hierarchy_note", "")).strip()
                premium_option["hierarchy_note"] = (
                    f"{base_note} Premium hotel was adjusted to be at least comparable with Standard when budget allows."
                ).strip()

    options = _apply_hotel_category_labels(
        options=options,
        destination=destination,
        requested_days=requested_days,
    )

    return {
        "destination": destination,
        "days": requested_days,
        "budget": safe_budget,
        "reserve_budget": reserve_budget,
        "spendable_budget": spendable_budget,
        "options": options,
    }
