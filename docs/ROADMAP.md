# NorthStar Platform — Roadmap

This document tracks the planned phases of the NorthStar Consulting AI Platform.

---

## Phases Overview

| Phase | Name                    | Status           |
|-------|-------------------------|------------------|
| 1     | Authentication          | ✅ Implemented    |
| 2     | Lead Generation Engine  | ✅ Implemented    |
| 3     | Outreach Engine         | 🔲 Planned       |
| 4     | Proposal Generator      | 🔲 Planned       |
| 5     | Market Intelligence     | 🔲 Planned       |
| 6     | React Dashboard         | 🔲 Planned       |
| 7     | Deployment & DevOps     | 🔲 Planned       |

---

## Phase 1 — Authentication ✅

**Goal:** Secure, token-based user authentication.

- User registration with bcrypt password hashing
- JWT access tokens (30-minute expiry) + JWT refresh tokens (7-day expiry)
- Endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`

---

## Phase 2 — Lead Generation Engine ✅

**Goal:** AI-assisted discovery, scoring, and storage of business leads.

- SerpAPI-based public web search for leads
- Rule-based lead scorer (0–100)
- Lead classifier: Hot (≥ 75) / Warm (≥ 45) / Cold (< 45)
- CRUD endpoints: `GET/POST /leads/`, `GET /leads/{id}`, `POST /leads/search`

---

## Phase 3 — Outreach Engine 🔲

**Goal:** AI-drafted, human-approved outreach messages for leads.

- Personalised email drafts with tone selection (executive / professional / casual)
- Follow-up message generation
- Human-approval gate before any send
- Outreach history and audit trail

See [`docs/OUTREACH_ENGINE.md`](OUTREACH_ENGINE.md) for full specification.

---

## Phase 4 — Proposal Generator 🔲

**Goal:** AI-powered consulting proposal drafts.

- Scope-of-work templating
- Pricing block builder
- PDF export
- Proposal management API + React UI

---

## Phase 5 — Market Intelligence Engine 🔲

**Goal:** Surface actionable market insights from public sources.

- Public search trend analysis
- Industry clustering (public data only)
- Competitor insights
- Opportunities summary
- Market AI agent

---

## Phase 6 — React Dashboard 🔲

**Goal:** Full-featured React frontend for the platform.

- Login UI
- Leads table with filtering and sort
- Outreach drafting and approval UI
- Proposal generation UI
- Market insights UI
- Sidebar navigation
- API service hooks

---

## Phase 7 — Deployment & DevOps 🔲

**Goal:** Production-ready containerised deployment.

- Docker + Docker Compose configuration
- Production build scripts
- Cloud deployment (Render / Fly.io / Railway)
- Environment variable management
- Health checks and monitoring

---

## Near-Term Milestones

| Milestone                           | Target       |
|-------------------------------------|--------------|
| Alembic migrations + Docker Compose | Phase 7 prep |
| Basic CI (GitHub Actions)           | Phase 7 prep |
| Phase 3 Outreach Engine MVP         | Phase 3      |
| Phase 6 React Dashboard MVP         | Phase 6      |
| Production deployment               | Phase 7      |
