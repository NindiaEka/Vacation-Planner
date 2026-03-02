# Solution Report – Autonomous Vacation Planner

## 1) Problem Statement
Build a proof-of-concept (PoC) vacation planner that:

1. Can autonomously generate travel plans based on preferences, calendar, and budget.
2. Can execute bookings when the user grants payment consent.
3. Uses Open Source GenAI (Llama 3 via Groq) in a practical way.

## 2) Approach & Design Decisions

### 2.1 Arsitektur
The solution is split into two layers (**decoupled architecture**):

- **Backend API (`app_backend.py`)**
  - Endpoint `POST /plan` for travel planning.
  - Endpoint `POST /book` for booking execution with consent validation.
  - Endpoint `GET /bookings/{transaction_id}` for booking status retrieval.

- **Frontend UI (`app_frontend.py`)**
  - Streamlit acts as a client: sends requests to backend, renders tier results, and handles booking confirmation.

### 2.2 Autonomous Planning Flow
1. The user sends preferences: destination, duration, budget, and preferred start date.
2. The planner reads user calendar data and checks date availability.
3. The system builds 3 tiers (`Hemat`, `Standard`, `Premium`) with budget scaling.
4. The LLM generates reasoning/justification for each option.
5. The frontend displays options, the user selects a tier, then provides payment consent for booking.

### 2.3 Booking Flow
1. The frontend sends `option_id`, `selected_tier`, and `user_consent` to `POST /book`.
2. The backend rejects requests without consent (`403`) and rejects `option_id` mismatch (`400`).
3. The backend calls `booking_tool` for transaction simulation, returns a `transaction_id`, and persists booking metadata in file-based storage.
4. The frontend automatically checks `GET /bookings/{transaction_id}` once after successful booking, with optional auto-refresh.

## 3) Tech Stack
- Python
- FastAPI (backend)
- Streamlit (frontend)
- LangChain + Groq (Llama 3)
- python-dotenv
- requests

## 4) Completed Implementation
- Autonomous itinerary planning using LLM + tools.
- Calendar and user preference integration (mock data).
- Travel pricing tiering with hierarchy rules and validation.
- Booking API with backend consent checks.
- Booking status retrieval endpoint.
- Setup and endpoint documentation in README.

## 5) Assumptions
- Calendar, preference, and payment data are still mock/simulated.
- External booking providers are not yet connected (flight/hotel/payment APIs).
- Booking persistence is currently file-based (`data/booking_store.json`), not yet migrated to a production-grade database.

## 6) Security & Risk Reference
Detailed vulnerabilities, attack scenarios, impact, mitigation strategy, and production monitoring are documented in:

- `docs/Vulnerabilities_and_Risks.md`

## 7) Conclusion
The PoC meets the core requirements: autonomous planning + consent-based conditional booking, with a decoupled backend/frontend architecture and clear operational documentation.

Next steps for production readiness:
- authentication & authorization,
- rate limiting,
- CORS policy,
- persistent storage untuk booking,
- observability dan alerting yang lebih ketat.
