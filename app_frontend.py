"""Streamlit frontend client for Autonomous Vacation Planner.

Run:
- streamlit run app_frontend.py

Backend prerequisite:
- uvicorn app_backend:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from datetime import date

import requests
import streamlit as st
import streamlit.components.v1 as components

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


def _render_tier_cards(tiers: list[dict], itinerary_days: int) -> None:
    selected_option_id = st.session_state.get("selected_option_id")
    columns = st.columns(3)

    for idx, option in enumerate(tiers[:3]):
        with columns[idx]:
            tier_name = option.get("label", "Option")
            is_selected = selected_option_id == option.get("id")

            st.markdown(f"### {tier_name}")
            st.metric("💰 Total", f"Rp{int(option.get('total_price', 0)):,}")
            st.markdown(
                f"🗓️ {option.get('start_date', '-')} → {option.get('end_date', '-')} "
                f"({int(option.get('nights', itinerary_days))} nights)"
            )
            st.markdown(f"✈️ {option.get('flight', '-')}")
            st.markdown(f"💸 Round-trip Flight Price: Rp{int(option.get('flight_price', 0)):,}")
            if option.get("flight_discount_applied"):
                st.success(
                    "🏷️ Early Booking -10% • "
                    f"departure in {int(option.get('days_until_departure', 0))} days"
                )
            st.markdown(f"🏨 {option.get('hotel', '-')}")
            st.markdown(f"💸 Hotel: Rp{int(option.get('hotel_price', 0)):,}")
            st.caption(str(option.get("justification", "")))

            if st.button(
                f"Select {tier_name}",
                key=f"select_{option.get('id', idx)}",
                type="secondary" if is_selected else "primary",
            ):
                st.session_state["selected_option_id"] = option.get("id")
                st.session_state["selected_tier"] = option
                st.session_state["payment_permission"] = False
                st.session_state.pop("booking_result", None)
                st.session_state.pop("booking_status_detail", None)
                st.session_state["auto_refresh_booking"] = False
                st.rerun()


def _fetch_booking_status(backend_url: str, transaction_id: str) -> None:
    try:
        response = requests.get(f"{backend_url.rstrip('/')}/bookings/{transaction_id}", timeout=30)
        response.raise_for_status()
        st.session_state["booking_status_detail"] = response.json()
        st.session_state["booking_status_error"] = None
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            st.session_state["booking_status_error"] = "Transaction not found in backend."
        else:
            st.session_state["booking_status_error"] = f"Failed to check booking status: {exc}"
    except requests.RequestException as exc:
        st.session_state["booking_status_error"] = f"Failed to reach backend while checking booking: {exc}"


def main() -> None:
    st.set_page_config(page_title="Autonomous Vacation Planner (Client)", page_icon="✈️", layout="wide")
    st.markdown("# ✈️ Autonomous Vacation Planner")
    st.caption("Frontend Streamlit Client • Backend FastAPI (Llama 3/Groq)")

    if "payment_permission" not in st.session_state:
        st.session_state["payment_permission"] = False
    if "selected_option_id" not in st.session_state:
        st.session_state["selected_option_id"] = None
    if "auto_refresh_booking" not in st.session_state:
        st.session_state["auto_refresh_booking"] = False

    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)

    destination = st.text_input("Destination", value="Lombok")
    duration_days = st.number_input("Duration (days/nights)", min_value=1, max_value=30, value=5, step=1)
    budget_rupiah = st.number_input(
        "Budget (Rupiah)",
        min_value=1_000_000,
        max_value=500_000_000,
        value=15_000_000,
        step=500_000,
    )
    preferred_start_date = st.date_input("Preferred start date", value=date.today())

    if st.button("Generate Itinerary", type="primary"):
        payload = {
            "destination": destination,
            "duration_days": int(duration_days),
            "budget_rupiah": int(budget_rupiah),
            "preferred_start_date": preferred_start_date.isoformat(),
        }

        try:
            response = requests.post(f"{backend_url.rstrip('/')}/plan", json=payload, timeout=30)
            response.raise_for_status()
            itinerary = response.json()
            st.session_state["itinerary"] = itinerary
            st.session_state["selected_option_id"] = None
            st.session_state["selected_tier"] = None
            st.session_state["payment_permission"] = False
            st.session_state.pop("booking_result", None)
            st.session_state.pop("booking_status_detail", None)
            st.session_state["auto_refresh_booking"] = False
        except requests.RequestException as exc:
            st.error(f"Failed to reach backend: {exc}")

    itinerary = st.session_state.get("itinerary")
    if not itinerary:
        return

    if itinerary.get("date_warning"):
        st.warning(str(itinerary.get("date_warning")))

    if itinerary.get("effective_start_date"):
        st.caption(
            f"Effective start date: {itinerary.get('effective_start_date')} "
            f"(user requested: {itinerary.get('requested_start_date') or '-'})"
        )

    st.markdown("## 🧭 Planner Summary")
    st.write(str(itinerary.get("reasoning", "")))

    tiers = itinerary.get("tiers", [])
    if tiers:
        st.markdown("## 💰 Choose a Travel Package")
        _render_tier_cards(tiers=tiers, itinerary_days=int(itinerary.get("duration_days", duration_days)))

        selected_tier = st.session_state.get("selected_tier")
        if selected_tier:
            st.success(
                f"Selected package: {selected_tier.get('label')} • Rp{int(selected_tier.get('total_price', 0)):,}"
            )
    else:
        st.info("No tier options returned from backend yet.")

    st.markdown("## 📦 Selected Option Details")
    st.json(st.session_state.get("selected_tier") or {})

    can_book = bool(st.session_state.get("selected_option_id")) and bool(st.session_state.get("selected_tier"))
    st.checkbox(
        "I authorize payment data usage for booking",
        key="payment_permission",
    )
    payment_permission = bool(st.session_state.get("payment_permission"))

    if st.button("Confirm & Book", type="primary", disabled=not can_book or not payment_permission):
        selected_tier = st.session_state.get("selected_tier", {})
        book_payload = {
            "option_id": selected_tier.get("id", ""),
            "user_consent": payment_permission,
            "selected_tier": selected_tier,
        }
        try:
            response = requests.post(f"{backend_url.rstrip('/')}/book", json=book_payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            st.session_state["booking_result"] = {
                "status": str(data.get("booking_status", "")),
                "transaction_id": str(data.get("transaction_id", "")),
                "selected_tier": selected_tier,
            }
            st.session_state["booking_status_detail"] = None
            st.session_state["booking_status_error"] = None
            transaction_id = str(data.get("transaction_id", "")).strip()
            if transaction_id:
                _fetch_booking_status(backend_url=backend_url, transaction_id=transaction_id)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                st.error("Booking denied: user consent has not been provided.")
            else:
                st.error(f"Booking failed: {exc}")
        except requests.RequestException as exc:
            st.error(f"Failed to reach backend during booking: {exc}")

    booking_result = st.session_state.get("booking_result")
    if booking_result and booking_result.get("status", "").lower() == "success":
        st.success(
            f"✅ Booking processed successfully. Transaction ID: {booking_result.get('transaction_id')}"
        )

        transaction_id = str(booking_result.get("transaction_id", "")).strip()
        st.checkbox(
            "Auto-refresh status every 5 seconds",
            key="auto_refresh_booking",
        )
        if st.session_state.get("auto_refresh_booking") and transaction_id:
            _fetch_booking_status(backend_url=backend_url, transaction_id=transaction_id)
            st.caption("Auto-refresh is active. Status updates every 5 seconds.")
            components.html(
                """
                <script>
                    setTimeout(function () {
                        window.parent.location.reload();
                    }, 5000);
                </script>
                """,
                height=0,
            )

        booking_status_error = st.session_state.get("booking_status_error")
        if booking_status_error:
            st.error(str(booking_status_error))

        booking_status_detail = st.session_state.get("booking_status_detail")
        if booking_status_detail:
            st.markdown("### 📄 Booking Status Details")
            st.json(booking_status_detail)
    elif not can_book:
        st.caption("Select a tier first to enable booking.")
    elif not payment_permission:
        st.caption("Enable payment authorization to proceed with booking.")


if __name__ == "__main__":
    main()
