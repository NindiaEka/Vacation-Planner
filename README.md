# ✈️ Autonomous Travel Planner

An autonomous travel assistant that plans vacations based on user calendar, preferences, and budget.

## High-Level Architecture

The system uses a **Decoupled Architecture**:

- **Backend (FastAPI)**: Handles AI reasoning (Llama 3 via Groq), calendar validation, pricing tiering, and booking APIs.
- **Frontend (Streamlit)**: Interactive UI for user input, tier visualization, payment consent, and booking status.
- **AI Engine**: Llama 3 (Groq) as the reasoning engine.

## Setup

### 1) Clone the repository

```bash
git clone https://github.com/NindiaEka/Vacation-Planner.git
```

### 2) Install dependencies (uv-only)

```bash
uv sync
```

Optional (without uv):

```bash
pip install -r requirements.txt
```

### 4) Configure API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

## Run

Run the app in two separate terminals.

### Terminal 1: Backend API

```bash
uv run python -m uvicorn app_backend:app --host 0.0.0.0 --port 8000 --reload
```

Alternative (Windows PowerShell with existing `.venv`):

```powershell
E:/Data/AssistX/vacation-planner/.venv/Scripts/python.exe -m uvicorn app_backend:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend UI

```bash
uv run streamlit run app_frontend.py
```

Alternative (Windows PowerShell with existing `.venv`):

```powershell
E:/Data/AssistX/vacation-planner/.venv/Scripts/python.exe -m streamlit run app_frontend.py --server.address 127.0.0.1 --server.port 8501
```

## Backend Endpoints

- `GET /health`
  - Service health check.
- `POST /plan`
  - Input: destination, duration, budget, preferred start date.
  - Output: 3 tier options (`Hemat`, `Standard`, `Premium`) with reasoning and justification.
- `POST /book`
  - Input: `option_id`, `user_consent`, `selected_tier`.
  - Consent validation + booking simulation.
- `GET /bookings/{transaction_id}`
  - Retrieve booking transaction status details.

## Local Access

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Streamlit UI: `http://localhost:8501`

## Project Structure

- `app_backend.py`: FastAPI backend
- `app_frontend.py`: Streamlit frontend client
- `src/agents/planner.py`: Planner agent
- `src/tools/`: Travel, calendar, flight, hotel, booking tools
- `src/data/`: User data loaders
- `data/`: Mock user data (`user_calendar.json`, `user_preferences.json`)
- `docs/`: Solution and risk documentation

## Vulnerabilities & Risks

See the dedicated document at `docs/Vulnerabilities_and_Risks.md`.

## Notes

- Travel data is currently simulated/mock.
- Booking is simulated via `src/tools/booking_tool.py`.
- Booking status is persisted to file-based storage at `data/booking_store.json` (baseline persistence, not yet a database).
- Frontend performs an automatic booking-status fetch immediately after a successful `Confirm & Book`.