# Phase 3 — Outreach Engine

## Overview

The Outreach Engine is a **human-in-the-loop** content generator that produces personalised cold-outreach emails and a 3-step follow-up sequence from an existing Lead record.

> **No email is sent.** The engine generates text only and returns it to the UI for the user to review, edit, and send manually.

---

## Architecture

```
Frontend (React)
    └── /outreach page
        ├── OutreachForm  ← selects lead, tone, service focus
        └── MessageOutput ← displays + copy-to-clipboard

Backend (FastAPI)
    └── /outreach router
        ├── POST /outreach/generate   ← returns subject + body
        └── POST /outreach/followups  ← returns 3 follow-ups

        Both endpoints:
        • require JWT Bearer auth (Phase 1)
        • load Lead from DB by ID (Phase 2 model)
        • call outreach_writer service
```

---

## Backend API

### Authentication

All outreach endpoints require a valid JWT Bearer token obtained from `POST /auth/login`.

```
Authorization: Bearer <access_token>
```

---

### `POST /outreach/generate`

Generate a personalised subject line and outreach email body.

**Request body**

| Field           | Type                                          | Required | Description                              |
|-----------------|-----------------------------------------------|----------|------------------------------------------|
| `lead_id`       | int                                           | ✓        | ID of the Lead record in the database    |
| `tone`          | `"executive"` \| `"professional"` \| `"casual"` | ✓      | Writing tone                             |
| `service_focus` | `"operations"` \| `"strategy"` \| `"scaling"`   | ✓      | Consulting focus area                    |
| `extra_context` | string                                        | —        | Optional additional context to include   |

**Response body**

```json
{
  "subject": "Helping Acme Corp with Operational Efficiency",
  "message": "I hope this message finds you well.\n\n..."
}
```

**Error responses**

| Code | Description                     |
|------|---------------------------------|
| 401  | Missing or invalid token        |
| 404  | Lead not found                  |
| 422  | Invalid request body            |

---

### `POST /outreach/followups`

Generate a 3-step follow-up email sequence.

**Request body**

| Field           | Type                                          | Required |
|-----------------|-----------------------------------------------|----------|
| `lead_id`       | int                                           | ✓        |
| `tone`          | `"executive"` \| `"professional"` \| `"casual"` | ✓      |
| `service_focus` | `"operations"` \| `"strategy"` \| `"scaling"`   | ✓      |

**Response body**

```json
{
  "followup_1": "Hi again,\n\nI wanted to follow up...",
  "followup_2": "Hi,\n\nSharing a brief case study...",
  "followup_3": "Hi,\n\nI'll keep this short..."
}
```

---

## Generation Modes

### Template mode (default, `LLM_PROVIDER=template`)

Fully deterministic. No external services required. Appropriate for development and production deployments where LLM integration is not yet set up.

Templates vary by `tone` × `service_focus` (9 unique combinations for the subject, body, and follow-ups each).

### OpenAI mode (`LLM_PROVIDER=openai`)

Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=<key>` in the backend `.env` file.  
Uses `gpt-4o-mini` via the `openai` Python library. Falls back to template mode on error.

---

## Frontend

The React Outreach page is accessible at `/outreach` after authentication.

### Features

- **Lead selector** — fetches all leads from `GET /leads`.
- **Add lead** — inline form to create a lead without leaving the page.
- **Tone selector** — Professional / Executive / Casual.
- **Service focus selector** — Operations / Strategy / Scaling.
- **Extra context** — optional free-text field included in the generated message.
- **Generate** — calls both `/outreach/generate` and `/outreach/followups` in parallel.
- **Copy to clipboard** — individual Copy buttons for subject, body, and each follow-up.

### Token storage

The JWT access token is stored in `localStorage` as `access_token` and attached as a Bearer header on all API calls.

---

## Security constraints

| Constraint | Detail |
|------------|--------|
| No email sending | The outreach endpoints return text only. No SMTP, SES, or third-party email integration exists. |
| No web scraping | Lead data must be created explicitly; no automated scraping. |
| Auth required | Both endpoints return `401` without a valid token. |
| `.env` not committed | All secrets live in `.env` (gitignored). See `backend/.env.example`. |

---

## Running locally

```bash
# Backend
cd backend
cp .env.example .env          # edit secrets as needed
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`, register an account, add a lead, and generate outreach.

---

## Tests

```bash
cd backend
pytest tests/ -v
```

31 unit tests cover all tone × service_focus combinations for both the message and followup generators.
