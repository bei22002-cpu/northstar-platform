# Architecture

## Overview

NorthStar Platform is a full-stack AI-powered consulting lead and outreach platform.

```
frontend/   React (Vite) SPA
backend/    FastAPI (Python) REST API
docs/       Documentation
```

---

## Backend

**Framework:** FastAPI  
**Database:** SQLAlchemy ORM — SQLite by default (dev), PostgreSQL in production  
**Auth:** JWT Bearer tokens (HS256) via `python-jose`

### Key modules

| Path | Responsibility |
|------|----------------|
| `app/main.py` | FastAPI app, CORS, router registration |
| `app/database.py` | SQLAlchemy engine, session, `Base` |
| `app/core/config.py` | Environment configuration |
| `app/core/security.py` | Password hashing, JWT creation/decoding |
| `app/api/deps.py` | `get_current_user` auth dependency |
| `app/api/auth_router.py` | `POST /auth/register`, `POST /auth/login` |
| `app/api/leads_router.py` | `GET/POST /leads`, `GET/DELETE /leads/{id}` |
| `app/api/outreach_router.py` | `POST /outreach/generate`, `POST /outreach/followups` |
| `app/models/user.py` | User ORM model |
| `app/models/lead.py` | Lead ORM model |
| `app/schemas/` | Pydantic request/response schemas |
| `app/services/auth_service.py` | User creation and authentication logic |
| `app/services/outreach_writer.py` | Outreach content generation (template + LLM) |

---

## Frontend

**Framework:** React 18 + Vite  
**Routing:** React Router v6  
**Styling:** Inline CSS (no external CSS framework required)

### Key modules

| Path | Responsibility |
|------|----------------|
| `src/lib/api.js` | Fetch wrapper with JWT Bearer auth |
| `src/App.jsx` | Route definitions, auth guard |
| `src/pages/Login.jsx` | Login / register page |
| `src/pages/Outreach.jsx` | Main outreach generation page |
| `src/components/OutreachForm.jsx` | Form: lead selector, tone, focus, extra context |
| `src/components/MessageOutput.jsx` | Displays and copy-enables generated content |

---

## Phase status

| Phase | Name | Status |
|-------|------|--------|
| Phase 1 | Authentication (JWT) | ✅ Implemented |
| Phase 2 | Lead Engine | ✅ Implemented |
| Phase 3 | Outreach Engine | ✅ Implemented |
