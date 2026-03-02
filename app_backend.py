"""FastAPI backend for Autonomous Vacation Planner.

Run:
- uvicorn app_backend:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import sys
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from agents.planner import VacationPlanner  # noqa: E402
from tools.booking_tool import execute_booking  # noqa: E402


class PlanRequest(BaseModel):
    destination: str = Field(..., min_length=2)
    duration_days: int = Field(..., ge=1, le=30)
    budget_rupiah: int = Field(..., gt=0)
    preferred_start_date: Optional[date] = None


class TierOption(BaseModel):
    id: str
    label: str
    tier: str
    start_date: str
    end_date: str
    nights: int
    flight: str
    flight_class: str
    flight_price: int
    hotel: str
    hotel_price: int
    total_price: int
    justification: str
    flight_discount_applied: bool
    days_until_departure: int


class PlanResponse(BaseModel):
    destination: str
    duration_days: int
    budget_rupiah: int
    requested_start_date: Optional[str]
    effective_start_date: Optional[str]
    date_warning: Optional[str]
    reasoning: str
    tiers: list[TierOption]


class BookRequest(BaseModel):
    option_id: str = Field(..., min_length=1)
    user_consent: bool = Field(...)
    selected_tier: Optional[dict] = None


class BookResponse(BaseModel):
    booking_status: str
    transaction_id: str


class BookingRecord(BaseModel):
    booking_status: str
    transaction_id: str
    option_id: str
    selected_tier: dict
    created_at: str


app = FastAPI(title="Vacation Planner Backend", version="1.0.0")
planner = VacationPlanner()
BOOKING_STORE: dict[str, dict] = {}
BOOKING_STORE_PATH = ROOT_DIR / "data" / "booking_store.json"


def _load_booking_store() -> dict[str, dict]:
    try:
        if not BOOKING_STORE_PATH.exists():
            return {}
        with open(BOOKING_STORE_PATH, "r", encoding="utf-8") as file:
            raw = json.load(file)
        if isinstance(raw, dict):
            return {str(key): value for key, value in raw.items() if isinstance(value, dict)}
    except Exception:
        pass
    return {}


def _save_booking_store(store: dict[str, dict]) -> None:
    BOOKING_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKING_STORE_PATH, "w", encoding="utf-8") as file:
        json.dump(store, file, ensure_ascii=False, indent=2)


BOOKING_STORE.update(_load_booking_store())


def _build_user_request(destination: str, duration_days: int, budget_rupiah: int) -> str:
    return f"I want a vacation to {destination} for {duration_days} days with budget {budget_rupiah}"


def _ensure_unique_justifications(options: list[dict]) -> list[dict]:
    seen: set[str] = set()
    updated_options: list[dict] = []

    for option in options:
        current = dict(option)
        reason = str(current.get("justification", "")).strip()
        normalized = reason.lower()
        if normalized in seen:
            label = current.get("label", "Tier")
            start_date = current.get("start_date", "-")
            current["justification"] = f"{reason} ({label} is scheduled to start on {start_date})."
            normalized = str(current["justification"]).lower()
        seen.add(normalized)
        updated_options.append(current)

    return updated_options


def _to_tier_option(option: dict, fallback_days: int) -> TierOption:
    return TierOption(
        id=str(option.get("id", "")),
        label=str(option.get("label", "")),
        tier=str(option.get("tier", "")),
        start_date=str(option.get("start_date", "")),
        end_date=str(option.get("end_date", "")),
        nights=int(option.get("calendar_gap_days", fallback_days)),
        flight=str(option.get("flight", "")),
        flight_class=str(option.get("flight_class", "")),
        flight_price=int(option.get("flight_price", 0)),
        hotel=str(option.get("hotel", "")),
        hotel_price=int(option.get("hotel_price", 0)),
        total_price=int(option.get("total_price", 0)),
        justification=str(option.get("justification", "")),
        flight_discount_applied=bool(option.get("flight_discount_applied", False)),
        days_until_departure=int(option.get("days_until_departure", 0)),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": os.getenv("LLM_MODEL", "llama-3-8b-instant")}


@app.post("/plan", response_model=PlanResponse)
def plan_trip(payload: PlanRequest) -> PlanResponse:
    try:
        user_request = _build_user_request(
            destination=payload.destination,
            duration_days=payload.duration_days,
            budget_rupiah=payload.budget_rupiah,
        )

        itinerary = planner.plan_itinerary(
            user_request,
            preferred_start_date=payload.preferred_start_date.isoformat() if payload.preferred_start_date else None,
        )

        options = _ensure_unique_justifications(itinerary.get("travel_options", []))
        tiers = [_to_tier_option(option, fallback_days=payload.duration_days) for option in options]
        resolved_days = itinerary.get("days")
        resolved_budget = itinerary.get("budget")

        return PlanResponse(
            destination=str(itinerary.get("destination", payload.destination)),
            duration_days=int(resolved_days if resolved_days is not None else payload.duration_days),
            budget_rupiah=int(resolved_budget if resolved_budget is not None else payload.budget_rupiah),
            requested_start_date=itinerary.get("requested_start_date"),
            effective_start_date=itinerary.get("effective_start_date"),
            date_warning=itinerary.get("date_warning"),
            reasoning=str(itinerary.get("reasoning", "")),
            tiers=tiers,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {exc}") from exc


@app.post("/book", response_model=BookResponse)
def book_trip(payload: BookRequest) -> BookResponse:
    if not payload.user_consent:
        raise HTTPException(status_code=403, detail="User consent is required to execute booking.")

    selected_tier = payload.selected_tier or {}
    selected_option_id = str(selected_tier.get("id", payload.option_id))
    if selected_option_id != payload.option_id:
        raise HTTPException(status_code=400, detail="option_id mismatch with selected_tier.id")

    booking_result = execute_booking(
        itinerary={
            "selected_option_id": payload.option_id,
            "selected_tier": selected_tier,
        },
        permission=payload.user_consent,
    )

    if booking_result.get("status") != "success":
        raise HTTPException(status_code=500, detail="Booking failed to complete.")

    transaction_id = str(booking_result.get("transaction_id", ""))
    if not transaction_id:
        raise HTTPException(status_code=500, detail="Booking response missing transaction_id.")

    normalized_transaction_id = transaction_id.strip()
    BOOKING_STORE[normalized_transaction_id] = {
        "booking_status": "Success",
        "transaction_id": normalized_transaction_id,
        "option_id": payload.option_id,
        "selected_tier": selected_tier,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_booking_store(BOOKING_STORE)

    return BookResponse(
        booking_status="Success",
        transaction_id=normalized_transaction_id,
    )


@app.get("/bookings/{transaction_id}", response_model=BookingRecord)
def get_booking(transaction_id: str) -> BookingRecord:
    normalized_transaction_id = transaction_id.strip()
    booking = BOOKING_STORE.get(normalized_transaction_id)
    if not booking:
        BOOKING_STORE.update(_load_booking_store())
        booking = BOOKING_STORE.get(normalized_transaction_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return BookingRecord(**booking)
