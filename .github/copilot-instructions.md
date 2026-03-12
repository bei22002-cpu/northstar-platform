# NorthStar Platform — Copilot Instructions

## Overview

NorthStar is a modular AI-driven consulting platform with a **FastAPI/Python backend** and a **React/TypeScript frontend**. The backend handles authentication (JWT), lead generation, and outreach message generation. The frontend is a Vite-based React SPA.

---

## Repository Layout

```
northstar-platform/
├── .github/
│   └── copilot-instructions.md
├── backend/
│   ├── .env.example            # Copy to .env before running
│   ├── requirements.txt        # Python dependencies (pip)
│   ├── app/
│   │   ├── main.py             # FastAPI entry point — registers all routers
│   │   ├── core/
│   │   │   ├── config.py       # Env-var loading (DATABASE_URL, JWT_SECRET, …)
│   │   │   ├── database.py     # SQLAlchemy engine + Base + get_db (USE THIS, not app/database.py)
│   │   │   └── security.py     # bcrypt hashing, JWT create/decode
│   │   ├── models/             # SQLAlchemy ORM models (User, Lead, Outreach)
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── services/           # Business logic (auth_service, lead_score, outreach_writer, …)
│   │   ├── api/                # FastAPI routers (auth_router, leads_router, outreach_router)
│   │   └── utils/              # Thin HTTP wrappers (serpapi_client)
│   └── tests/
│       └── test_outreach_service.py   # Standalone unit tests (no DB, no HTTP)
├── frontend/
│   ├── index.html              # Vite entry point
│   ├── vite.config.js          # Proxy: /auth /leads /outreach /health → localhost:8000
│   ├── package.json
│   └── src/
│       ├── main.jsx            # React root mount
│       ├── App.tsx             # Router + auth guard (useAuth hook)
│       ├── lib/api.js          # Centralised fetch wrapper — use this for all API calls
│       ├── hooks/              # useAuth (JWT in localStorage)
│       ├── pages/              # LoginPage, LeadsPage, OutreachPage
│       ├── components/         # Sidebar and shared UI
│       └── services/           # (reserved for future service-layer abstractions)
├── ARCHITECTURE.md             # Full architecture reference
└── README.md
```

---

## Key Conventions

### Backend
- **Always** import `Base` and `get_db` from `app.core.database` — not from `app.database` (a legacy duplicate).
- All SQLAlchemy models must inherit from `app.core.database.Base`.
- Pydantic v2 is in use (`model_config`, `model_validator`, `field_validator`).
- JWT access tokens expire in 30 min; refresh tokens in 7 days.
- Do **not** hardcode secrets — read them from env vars via `app.core.config`.
- New routers must be registered in `app/main.py` via `app.include_router(...)`.

### Frontend
- Use native `fetch` via `src/lib/api.js` for all API calls — **no axios**.
- Environment variables must use `import.meta.env.VITE_*` prefix.
- The Vite dev server proxies `/auth`, `/leads`, `/outreach`, and `/health` to `http://localhost:8000`.
- `App.tsx` is the router root; add new routes there.

---

## Build & Run

### Backend

```bash
cd backend

# 1. Copy env file and fill in values
cp .env.example .env

# 2. Install dependencies (Python 3.11+)
pip install -r requirements.txt

# 3. Start the API server
uvicorn app.main:app --reload --port 8000
```

Swagger UI is available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend

# 1. Install dependencies (Node 18+)
npm install

# 2. Start dev server (proxies API calls to localhost:8000)
npm run dev
# → http://localhost:5173

# 3. Production build
npm run build
```

---

## Running Tests

```bash
cd backend

# Run all tests (no DB or external services required)
pytest tests/ -v
```

Tests are standalone unit tests using `unittest.mock`. No database or HTTP connections are needed.

---

## Environment Variables

| Variable             | Description                              | Default (dev)                                  |
|----------------------|------------------------------------------|------------------------------------------------|
| `DATABASE_URL`       | PostgreSQL connection string             | `postgresql+psycopg2://username:password@localhost/northstar_db` |
| `JWT_SECRET`         | HS256 signing secret for access tokens  | `change-me-in-production`                      |
| `JWT_REFRESH_SECRET` | HS256 signing secret for refresh tokens | `change-refresh-in-production`                 |
| `SERPAPI_KEY`        | SerpAPI key for lead search             | _(empty — lead search disabled without it)_    |
| `CORS_ORIGINS`       | Comma-separated allowed origins          | `http://localhost:3000`                        |

---

## API Endpoints

| Method | Path                  | Auth Required | Description                            |
|--------|-----------------------|---------------|----------------------------------------|
| GET    | `/`                   | No            | Health check                           |
| POST   | `/auth/register`      | No            | Create user account                    |
| POST   | `/auth/login`         | No            | Authenticate, receive JWT tokens       |
| POST   | `/auth/refresh`       | No            | Exchange refresh token for new tokens  |
| GET    | `/leads/`             | Yes           | List all leads (paginated)             |
| POST   | `/leads/`             | Yes           | Manually create a lead (auto-scored)   |
| GET    | `/leads/{id}`         | Yes           | Retrieve a single lead                 |
| POST   | `/leads/search`       | Yes           | Web search, score, and import leads    |
| POST   | `/outreach/generate`  | Yes           | Generate outreach message for a lead   |
| POST   | `/outreach/followups` | Yes           | Generate 3 follow-up messages          |

---

## Technology Stack

| Layer     | Technology                     | Version    |
|-----------|--------------------------------|------------|
| Backend   | FastAPI                        | ~0.135     |
| ORM       | SQLAlchemy                     | ~2.0       |
| Database  | PostgreSQL + psycopg2          | any        |
| Auth      | python-jose (JWT HS256)        | ~3.5       |
| Passwords | passlib[bcrypt]                | ~1.7       |
| HTTP      | httpx                          | ~0.28      |
| Frontend  | React + React Router           | 18 / 6     |
| Bundler   | Vite + @vitejs/plugin-react    | ~5.2       |
| Runtime   | Python 3.11+ / Node 18+        |            |
