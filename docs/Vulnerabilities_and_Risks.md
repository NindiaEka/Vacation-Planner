# Vulnerabilities & Risks

This document is written based on the **current implementation that truly exists in the codebase**, not the ideal target state.

| ID | Vulnerability | Attack Scenario | Impact | Mitigation Strategy | Production Monitoring | Current Implementation Status |
|---|---|---|---|---|---|---|
| V-01 | Backend API is publicly accessible | External actors/bots can send large volumes of direct requests to `/plan` or `/book` without using the Streamlit UI. | Increased LLM cost, slower service, and faster quota exhaustion. | Cost-aware baseline: enable static API key + basic per-IP rate limiting. Next stage: JWT + WAF. | Monitor request volume per IP, HTTP 429 rate, and daily token cost spikes. Trigger alerts when requests/minute exceed baseline. | **Not implemented yet**: backend currently has no auth, rate limiting, or specific CORS policy. |
| V-02 | User input can influence AI logic | Users craft misleading prompts that push the model to ignore budget or tier rules. | Itinerary output may drift from business constraints. | Cost-aware baseline: input sanitization + rule-based output validation before response. Next stage: dedicated moderation/guardrail model. | Monitor invalid-output ratio, budget outliers, and deterministic fallback frequency. | **Partially implemented**: fallback and structural tier validation exist, but explicit anti prompt-injection controls are incomplete. |
| V-03 | Booking can be triggered via manipulated payloads | Users modify browser payload to force booking without valid consent. | Booking can be processed without proper authorization intent. | Cost-aware baseline: backend validation for consent + `option_id` (already exists). Next stage: user/session auth and signed requests. | Monitor 403/400 ratio on `/book`, `option_id` mismatch frequency, and repeated booking attempts from the same client. | **Partially implemented**: consent=false is rejected (403) and option mismatch is rejected (400); user/session auth is not implemented. |
| V-04 | Error responses may leak technical details | Exception details may be returned to clients during failures. | Internal app structure and runtime details may be exposed. | Cost-aware baseline: global error handler with generic client messages + controlled server-side logging. Next stage: centralized logging + redaction policy. | Monitor HTTP 500 count, sample error responses (without sensitive data), and scan logs for sensitive keywords. | **Partially implemented**: `/plan` is wrapped with `HTTPException`, but global sanitization and secure logging policy are incomplete. |
| V-05 | Booking history uses file-based persistence (no DB yet) | File corruption, concurrent writes, or host-level file loss can impact booking history integrity. | Transaction traceability can be partially lost and audit quality is limited. | Cost-aware baseline: file persistence with periodic backup and integrity checks (implemented). Next stage: persistent DB + immutable audit trail. | Monitor booking lookup failures, JSON load/save errors, record integrity checks, and backup freshness. | **Partially implemented**: booking records are persisted to `data/booking_store.json`; database-grade durability/concurrency controls are not implemented yet. |

## Controls Already Present in Code

- Request schema validation via Pydantic on FastAPI endpoints.
- `POST /book` validates `user_consent` (403 when consent is not provided).
- `POST /book` validates `option_id` against `selected_tier.id` (400 on mismatch).
- `GET /bookings/{transaction_id}` endpoint exists for stored booking status checks.
- Booking records are persisted to `data/booking_store.json` and loaded by backend startup/read path.

## Priority Next Improvements

1. Add authentication + authorization for backend endpoints.
2. Add rate limiting for high-cost endpoints (`/plan`, `/book`).
3. Apply CORS allowlist for official frontend origin only.
4. Add global secure error handling and safe logging policy.
5. Move booking storage from memory to a persistent database.
