"""Planner agent for Autonomous Vacation Planner.

References:
- src/data/user_calendar.py (calendar access)
- src/tools/travel_tool.py (tier generation and autonomous justifications)
- src/tools/booking_tool.py (booking execution with permission)
- Groq Llama model: llama-3-8b-instant / llama-3-70b-versatile
"""

import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.calendar_tool import check_calendar
from tools.travel_tool import search_travel_options
from tools.booking_tool import execute_booking
from data.user_calendar import get_calendar

load_dotenv()


def _parse_user_request(text: str) -> tuple[str, int, Optional[int]]:
    destination_match = re.search(
        r"(?:ke|to)\s+([A-Za-z][A-Za-z\s-]*?)(?=\s+\d+\s*(?:hari|days?)|\s+(?:budget|anggaran)\b|$)",
        text,
        re.IGNORECASE,
    )
    days_match = re.search(r"(\d+)\s*(?:hari|days?)", text, re.IGNORECASE)
    budget_match = re.search(
        r"(?:budget|anggaran)\s*(?:rp\s*)?([\d\.,]+)\s*(jt|juta)?",
        text,
        re.IGNORECASE,
    )

    destination = destination_match.group(1).strip() if destination_match else "Bali"
    days = int(days_match.group(1)) if days_match else 3
    if budget_match:
        raw_budget = budget_match.group(1).replace(".", "").replace(",", ".")
        unit = (budget_match.group(2) or "").lower()
        parsed_value = float(raw_budget)
        if unit in {"jt", "juta"}:
            budget = int(parsed_value * 1_000_000)
        else:
            budget = int(parsed_value)
    else:
        budget = None
    return destination, days, budget


def _load_preferences() -> dict:
    pref_path = os.getenv("USER_PREFERENCES_PATH", "data/user_preferences.json")
    try:
        with open(pref_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _recommend_destination(preferences: dict, requested_destination: str) -> str:
    if requested_destination:
        return requested_destination

    likes = str(preferences.get("suka", "")).lower()
    if likes == "pantai":
        return "Bali"
    if likes == "gunung":
        return "Bandung"

    preferred = preferences.get("preferred_destinations", [])
    if preferred and isinstance(preferred, list):
        return preferred[0]
    return "Bali"


def _build_selection_reasoning(base_reasoning: str, selected_option: dict) -> str:
    option_label = selected_option.get("label", "Selected option")
    total_price = selected_option.get("total_price", 0)
    start_date = selected_option.get("start_date", "-")
    end_date = selected_option.get("end_date", "-")
    tier_reason = selected_option.get("justification", "")
    return (
        f"{base_reasoning}\n\n"
        f"User selection update: {option_label} from {start_date} to {end_date} "
        f"with estimated total Rp{total_price:,}. {tier_reason}"
    )


def _parse_preferred_start_date(value: Optional[str | date | datetime]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _is_consecutive_available(available_dates: set[date], start_date: date, days: int) -> bool:
    return all((start_date + timedelta(days=offset)) in available_dates for offset in range(days))


def _find_nearest_available_start(
    raw_calendar: dict,
    preferred_start_date: date,
    days: int,
) -> Optional[date]:
    available_dates: set[date] = set()
    for raw_date, status in raw_calendar.items():
        if str(status).lower() != "available":
            continue
        try:
            available_dates.add(date.fromisoformat(raw_date))
        except ValueError:
            continue

    if not available_dates:
        return None

    valid_candidates = sorted(
        d for d in available_dates if _is_consecutive_available(available_dates, d, max(days, 1))
    )
    if not valid_candidates:
        valid_candidates = sorted(available_dates)

    return min(valid_candidates, key=lambda d: (abs((d - preferred_start_date).days), d))


def _fallback_tier_reason(option: dict, total_budget: int) -> str:
    tier = str(option.get("tier", "")).lower()
    start_date = option.get("start_date", "-")
    end_date = option.get("end_date", "-")
    total_price = int(option.get("total_price", 0))

    if tier == "hemat":
        return (
            f"Budget tier is chosen from {start_date} to {end_date} for cost efficiency, "
            f"prioritizing dates with clear calendar availability and an estimated total around Rp{total_price:,} "
            f"from a budget of Rp{total_budget:,}."
        )
    if tier == "standard":
        return (
            f"Standard tier is placed from {start_date} to {end_date} as the best compromise "
            f"between travel comfort and price, with an estimate of Rp{total_price:,}."
        )
    if option.get("flight_discount_applied"):
        return (
            "Although flight tickets are cheaper due to early booking, the Premium total remains high "
            "because we selected the best 5-star resort for the requested destination. "
            f"Schedule {start_date} to {end_date} with an estimate of Rp{total_price:,} "
            f"from a budget of Rp{total_budget:,}."
        )
    return (
        f"Premium tier is scheduled from {start_date} to {end_date} for a luxury experience with "
        f"high-end amenities, while maximizing budget usage to around 90% "
        f"(estimated Rp{total_price:,} from Rp{total_budget:,})."
    )


def _apply_autonomous_tier_reasons(
    llm: ChatGroq,
    travel_options: list[dict],
    destination: str,
    days: int,
    budget: int,
) -> list[dict]:
    if not travel_options:
        return travel_options

    option_payload = [
        {
            "tier": option.get("tier"),
            "label": option.get("label"),
            "start_date": option.get("start_date"),
            "end_date": option.get("end_date"),
            "total_price": option.get("total_price"),
            "calendar_gap_days": option.get("calendar_gap_days"),
        }
        for option in travel_options
    ]

    reasoning_prompt = (
        "You are an autonomous travel planner. Provide unique and specific reasons for each tier. "
        "Reply ONLY with a valid JSON object using keys: hemat, standard, premium.\n"
        "Reasoning rules:\n"
        "- hemat: focus on budget efficiency and cost-effective dates.\n"
        "- standard: focus on balance between comfort and price.\n"
        "- premium: focus on luxury, 5-star amenities, and near-maximum budget usage around 90%.\n"
        "- if premium flight gets early-booking discount, explain that total cost stays high due to 5-star resort selection.\n"
        "- each reason must include dates and the corresponding tier price amount.\n"
        f"Context: destination={destination}, duration={days} days, total_budget={budget}.\n"
        f"Tier data: {json.dumps(option_payload, ensure_ascii=False)}"
    )

    reason_by_tier: dict[str, str] = {}
    try:
        response = llm.invoke(reasoning_prompt)
        content = getattr(response, "content", str(response))
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            reason_by_tier = {str(key).lower(): str(value) for key, value in parsed.items()}
    except Exception:
        reason_by_tier = {}

    enriched_options = []
    for option in travel_options:
        tier_name = str(option.get("tier", "")).lower()
        reason = reason_by_tier.get(tier_name) or _fallback_tier_reason(option, total_budget=budget)
        updated_option = dict(option)
        updated_option["justification"] = reason
        enriched_options.append(updated_option)
    return enriched_options


def _build_consistent_planner_summary(destination: str, days: int, budget: int, travel_options: list[dict]) -> str:
    lines = [
        f"Autonomous plan to {destination} for {days} days with total budget Rp{budget:,}.",
    ]
    for option in travel_options:
        nights = option.get("calendar_gap_days", days)
        lines.append(
            f"- {option.get('label')}: {option.get('start_date')} s/d {option.get('end_date')}, "
            f"duration {nights} nights, estimate Rp{option.get('total_price', 0):,}. "
            f"Round-trip flight price Rp{option.get('flight_price', 0):,}, hotel {option.get('hotel')}. "
            f"Reason: {option.get('justification', '')}"
        )
    return "\n".join(lines)


def _contains_non_idr_currency(text: str) -> bool:
    lowered = text.lower()
    return "usd" in lowered or "$" in text or "dollar" in lowered


class VacationPlanner:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model=os.getenv("LLM_MODEL", "llama-3-8b-instant"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
        )

    def plan_itinerary(self, user_request: str, preferred_start_date: Optional[str | date | datetime] = None) -> dict:
        requested_destination, days, budget = _parse_user_request(user_request)
        preferences = _load_preferences()
        destination = _recommend_destination(preferences, requested_destination)
        parsed_preferred_start = _parse_preferred_start_date(preferred_start_date)
        raw_calendar = get_calendar()

        effective_start_date = parsed_preferred_start
        date_warning = None
        if parsed_preferred_start:
            nearest_available = _find_nearest_available_start(
                raw_calendar=raw_calendar,
                preferred_start_date=parsed_preferred_start,
                days=days,
            )
            if nearest_available is None:
                date_warning = (
                    "The selected date is not available in the calendar. "
                    "Planner continues from your requested date because there is no available slot in the calendar data."
                )
            elif nearest_available != parsed_preferred_start:
                effective_start_date = nearest_available
                date_warning = (
                    f"Requested date {parsed_preferred_start.isoformat()} is unavailable. "
                    f"Nearest available alternative that still fits budget: {nearest_available.isoformat()}."
                )

        calendar = check_calendar(days=days, start_date=effective_start_date)
        if budget is None:
            return {
                "destination": destination,
                "days": days,
                "budget": None,
                "calendar": calendar,
                "requested_start_date": parsed_preferred_start.isoformat() if parsed_preferred_start else None,
                "effective_start_date": effective_start_date.isoformat() if effective_start_date else None,
                "date_warning": date_warning,
                "travel": {},
                "travel_options": [],
                "selected_option_id": None,
                "reasoning": (
                    "Budget was not found in the request. "
                    "Please include budget (example: budget 15000000 or budget 15 million) "
                    "so the planner can tailor hotel and flight options."
                ),
            }

        travel = search_travel_options(
            destination=destination,
            days=days,
            budget=budget,
            preferred_start_date=effective_start_date,
        )
        travel_options = travel.get("options", [])
        travel_options = _apply_autonomous_tier_reasons(
            llm=self.llm,
            travel_options=travel_options,
            destination=destination,
            days=days,
            budget=budget,
        )

        reasoning_prompt = (
            "Rewrite the following itinerary summary in English without changing any date/price facts. "
            "Use ONLY Indonesian Rupiah (Rp) currency format and never convert any amount to USD or other currencies. "
            "Do not add conversion rates, exchange-rate commentary, or equivalent values in other currencies.\n"
            f"{_build_consistent_planner_summary(destination, days, budget, travel_options)}"
        )
        try:
            reasoning = self.llm.invoke(reasoning_prompt)
            reasoning_text = getattr(reasoning, "content", str(reasoning))
        except Exception as exc:
            error_text = str(exc)
            if "invalid_api_key" in error_text or "401" in error_text:
                reasoning_text = (
                    "Groq API key is invalid, so LLM reasoning is unavailable. "
                    "The app still shows itinerary output based on mock tools."
                )
            else:
                reasoning_text = (
                    "LLM is temporarily unavailable, itinerary is shown from mock tools. "
                    f"Error details: {error_text}"
                )

        if "LLM is temporarily unavailable" in reasoning_text or "Groq API key is invalid" in reasoning_text:
            reasoning_text = _build_consistent_planner_summary(destination, days, budget, travel_options)

        if _contains_non_idr_currency(reasoning_text):
            reasoning_text = _build_consistent_planner_summary(destination, days, budget, travel_options)

        if date_warning:
            reasoning_text = f"⚠️ {date_warning}\n\n{reasoning_text}"

        return {
            "destination": destination,
            "days": days,
            "budget": budget,
            "calendar": calendar,
            "requested_start_date": parsed_preferred_start.isoformat() if parsed_preferred_start else None,
            "effective_start_date": effective_start_date.isoformat() if effective_start_date else None,
            "date_warning": date_warning,
            "travel": {},
            "travel_options": travel_options,
            "selected_option_id": None,
            "reasoning": reasoning_text,
        }

    def update_itinerary_option(self, itinerary: dict, option_id: str) -> dict:
        travel_options = itinerary.get("travel_options", [])
        selected_option = next((opt for opt in travel_options if opt.get("id") == option_id), None)

        if not selected_option and travel_options:
            selected_option = travel_options[0]

        if not selected_option:
            return itinerary

        updated = dict(itinerary)
        updated["travel"] = selected_option
        updated["selected_option_id"] = selected_option.get("id")
        updated["reasoning"] = _build_selection_reasoning(
            itinerary.get("reasoning", "Itinerary generated successfully."),
            selected_option,
        )
        return updated

    def confirm_and_book(self, itinerary: dict, permission: bool = True) -> dict:
        return execute_booking(itinerary, permission=permission)
