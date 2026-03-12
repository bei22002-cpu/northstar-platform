# NorthStar Platform — System Architecture

This document outlines the technical architecture for the NorthStar Consulting AI Platform. It includes all backend and frontend components implemented to date (Phase 1 and Phase 2), as well as the planned system modules.

---

## 1. Overview

NorthStar is a modular AI-driven consulting platform consisting of:

- A **FastAPI** backend (Python)
- A **PostgreSQL** database
- A **React** frontend (to be built in Phase 6)
- AI-powered subsystems for:
  - Authentication
  - Lead generation (public web search)
  - Outreach (safe, human-approved messaging)
  - Proposal generation
  - Market intelligence
  - Dashboard and analytics

All modules are built with clean separation of concerns and follow a scalable folder structure.

---

## 2. Backend Architecture (FastAPI)

### 2.1 Folder Structure

```
backend/
├── .env.example
├── requirements.txt
└── app/
    ├── main.py                  # FastAPI application entry point
    ├── core/
    │   ├── config.py            # Environment variable loading
    │   ├── database.py          # SQLAlchemy engine + session
    │   └── security.py          # Password hashing, JWT creation/decoding
    ├── models/
    │   ├── user.py              # SQLAlchemy User ORM model
    │   └── lead.py              # SQLAlchemy Lead ORM model
    ├── schemas/
    │   ├── user.py              # Pydantic schemas (UserCreate, UserOut, Token…)
    │   └── lead.py              # Pydantic schemas (LeadCreate, LeadOut…)
    ├── services/
    │   ├── auth_service.py      # User lookup, creation, authentication, token issuing
    │   ├── lead_score.py        # Rule-based lead scoring (0–100)
    │   ├── lead_classifier.py   # Score → classification (hot / warm / cold)
    │   └── lead_scraper.py      # SerpAPI-based public web scraping
    ├── api/
    │   ├── auth_router.py       # POST /auth/register, /auth/login, /auth/refresh
    │   └── leads_router.py      # GET/POST /leads, GET /leads/{id}, POST /leads/search
    └── utils/
        └── serpapi_client.py    # Thin HTTP wrapper around SerpAPI
```

### 2.2 Database (PostgreSQL)

| Table   | Key Columns                                                                 |
|---------|-----------------------------------------------------------------------------|
| `users` | `id`, `email` (unique), `hashed_password`, `full_name`, `is_active`, `created_at` |
| `leads` | `id`, `company_name`, `contact_name`, `email`, `website`, `industry`, `score`, `classification`, `source`, `notes`, `created_at` |

Database sessions are managed per-request via a FastAPI dependency (`get_db`).

### 2.3 Authentication (Phase 1)

- **Password hashing** — bcrypt via `passlib`
- **JWT access tokens** — signed with `HS256`, expire in 30 minutes
- **JWT refresh tokens** — signed with a separate secret, expire in 7 days
- **Endpoints**

  | Method | Path              | Description                        |
  |--------|-------------------|------------------------------------|
  | POST   | `/auth/register`  | Create a new user account          |
  | POST   | `/auth/login`     | Authenticate and receive tokens    |
  | POST   | `/auth/refresh`   | Exchange refresh token for new tokens |

### 2.4 Lead Generation Engine (Phase 2)

- **Lead Scraper** (`lead_scraper.py`) — queries SerpAPI using only publicly available web search results; no private or restricted data sources are used.
- **Lead Scorer** (`lead_score.py`) — assigns a numeric score (0–100) based on data completeness signals (website, email, contact name, industry, notes).
- **Lead Classifier** (`lead_classifier.py`) — maps the numeric score to a tier:
  - **Hot** — score ≥ 75
  - **Warm** — score ≥ 45
  - **Cold** — score < 45
- **Endpoints**

  | Method | Path              | Description                                   |
  |--------|-------------------|-----------------------------------------------|
  | GET    | `/leads/`         | List all persisted leads (paginated)           |
  | POST   | `/leads/`         | Manually create a lead (auto-scored)           |
  | GET    | `/leads/{id}`     | Retrieve a single lead by ID                  |
  | POST   | `/leads/search`   | Search public web, score, and import leads    |

---

## 3. Planned Modules

### Phase 3 — Outreach Engine
- Message personalization AI
- Tone selection (executive / professional / casual)
- Follow-up generator
- Safe manual-send workflow (all messages require human approval before sending)
- Outreach API + React UI

### Phase 4 — Proposal Generator
- AI-powered proposal drafts
- Scope-of-work templating
- Pricing block builder
- PDF export
- Proposal API + UI

### Phase 5 — Market Intelligence Engine
- Public search trends analysis
- Industry clustering (public info only)
- Competitor insights
- Opportunities summary
- Market AI agent

### Phase 6 — React Dashboard
- Login UI
- Leads table
- Outreach UI
- Proposal generation UI
- Market insights UI
- Sidebar navigation
- API service hooks

### Phase 7 — Deployment
- Docker configuration
- Production build scripts
- Cloud deployment instructions (Render / Fly.io / Railway)
- Environment variable setup

---

## 4. Technology Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Backend API    | FastAPI (Python 3.11+)              |
| ORM            | SQLAlchemy                          |
| Database       | PostgreSQL                          |
| Auth tokens    | python-jose (JWT HS256)             |
| Password hash  | passlib[bcrypt]                     |
| External search| SerpAPI (public web only)           |
| HTTP client    | httpx                               |
| Frontend (planned) | React                           |
| Deployment (planned) | Docker + cloud PaaS           |

---

## 5. Security & Compliance Notes

- All automation is **human-approved** — no automated message sending.
- Lead discovery uses only **publicly accessible** sources via SerpAPI.
- Secrets (`.env`) are excluded from version control via `.gitignore`.
- JWT secrets are loaded from environment variables and never hardcoded in production.
