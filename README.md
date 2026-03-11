# NorthStar Platform

AI-powered lead generation, outreach, and market intelligence platform.

## Architecture

```
northstar-platform/
├── backend/               # FastAPI Python backend
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config & security utilities
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   ├── utils/         # External API clients
│   │   ├── database.py    # DB engine & session
│   │   └── main.py        # FastAPI application entry point
│   ├── .env.example
│   └── requirements.txt
└── frontend/              # React TypeScript frontend
    ├── public/
    └── src/
        ├── components/    # Shared UI components (Sidebar)
        ├── hooks/         # Custom React hooks (useAuth)
        ├── pages/         # Page components (Login, Leads, Outreach)
        └── services/      # Axios API service layer
```

## Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Authentication System (JWT, registration, login) | ✅ Completed |
| 2 | Lead Generation Engine (scoring, classification, SerpAPI) | ✅ Completed |
| 3 | Outreach Engine (personalization, tone, follow-ups, approval workflow) | ✅ Completed |
| 4 | Proposal Generator | 🔜 Upcoming |
| 5 | Market Intelligence Engine | 🔜 Upcoming |
| 6 | React Dashboard (full) | 🔜 Upcoming |
| 7 | Deployment | 🔜 Upcoming |

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env          # fill in your values
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm start
```

The React app opens at `http://localhost:3000`.

## API Overview

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and receive JWT tokens |
| POST | `/auth/refresh` | Refresh access token |

### Leads
| Method | Path | Description |
|--------|------|-------------|
| GET | `/leads/` | List all leads |
| POST | `/leads/` | Create a new lead (auto-scored & classified) |
| GET | `/leads/{id}` | Get a single lead |
| PUT | `/leads/{id}` | Update a lead |
| DELETE | `/leads/{id}` | Delete a lead |
| GET | `/leads/search/public` | Search public sources via SerpAPI |

### Outreach (Phase 3)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/outreach/messages` | Generate a personalized draft message |
| GET | `/outreach/messages` | List all outreach messages |
| GET | `/outreach/messages/{id}` | Get message with follow-ups |
| PUT | `/outreach/messages/{id}` | Edit a draft message |
| POST | `/outreach/messages/{id}/approve` | Human-approve a draft for sending |
| POST | `/outreach/messages/{id}/sent` | Mark message as manually sent |
| POST | `/outreach/followups` | Generate a follow-up message |
| GET | `/outreach/messages/{id}/followups` | List follow-ups for a message |

## Lead Scoring

Leads are automatically scored (0–100) and classified on creation/update:

| Classification | Score |
|---------------|-------|
| 🔴 Hot | ≥ 75 |
| 🟡 Warm | ≥ 45 |
| 🔵 Cold | < 45 |

## Outreach Workflow

All automation is **human-approved**. The safe manual-send workflow is:

1. Generate a draft message (AI-personalized by tone: executive / professional / casual)
2. Review and edit the draft
3. **Approve** the draft (required human step)
4. Send the email manually in your email client
5. Mark the message as **sent** in NorthStar
6. Generate follow-ups as needed

NorthStar never sends emails automatically.

## Security Notes

- `.env` is git-ignored — never commit secrets.
- All search uses publicly accessible sources via SerpAPI.
- JWT tokens expire and rotate via refresh tokens.
