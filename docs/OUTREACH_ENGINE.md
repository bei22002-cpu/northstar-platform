# Phase 3 — Outreach Engine (Specification)

This document specifies the design for the NorthStar Outreach Engine, to be built in Phase 3.

---

## 1. Purpose

The Outreach Engine enables consultants to craft personalised outreach messages directed at leads discovered by the Phase 2 Lead Generation Engine.

**Key goals:**

- Generate AI-drafted outreach messages tailored to each lead's industry, score tier, and context.
- Support multiple tones (executive / professional / casual).
- Enforce a **human-approval gate** — no message is ever sent without explicit user confirmation.
- Provide follow-up generation and scheduling hints.

---

## 2. User Stories

| ID  | As a …        | I want to …                                              | So that …                                      |
|-----|---------------|----------------------------------------------------------|------------------------------------------------|
| U1  | Consultant    | Generate a draft outreach email for a hot lead           | I can personalise and send it quickly          |
| U2  | Consultant    | Choose a tone (executive / professional / casual)        | My message matches the recipient's context     |
| U3  | Consultant    | Review and edit the draft before it is sent              | I maintain full control over outgoing messages |
| U4  | Consultant    | Mark a message as approved                               | It is queued for sending via my email client   |
| U5  | Consultant    | Generate a follow-up for an unanswered message           | I can re-engage stale leads systematically     |
| U6  | Team lead     | View outreach history per lead                           | I have an audit trail for compliance           |

---

## 3. Constraints

- **Human-approved sending only.** The platform generates and stores drafts; it never sends messages autonomously.  All sending requires an explicit "Approve & Send" action from an authenticated user.
- Lead discovery uses only **publicly accessible** information via SerpAPI (no restricted data sources).
- Drafts and outreach history must be stored and auditable.

---

## 4. Data Model Proposal

### `outreach_messages` table

| Column          | Type      | Notes                                              |
|-----------------|-----------|----------------------------------------------------|
| `id`            | Integer   | Primary key                                        |
| `lead_id`       | Integer   | Foreign key → `leads.id`                           |
| `created_by`    | Integer   | Foreign key → `users.id`                           |
| `tone`          | String    | `executive` / `professional` / `casual`            |
| `subject`       | String    | Suggested email subject line                       |
| `body`          | Text      | AI-generated draft body                            |
| `status`        | String    | `draft` / `approved` / `sent` / `archived`        |
| `approved_at`   | DateTime  | Set when user approves; NULL while in draft        |
| `sent_at`       | DateTime  | Set when user confirms send; NULL until then       |
| `created_at`    | DateTime  | Auto-set on creation                               |

---

## 5. API Endpoints

| Method | Path                                   | Description                                     |
|--------|----------------------------------------|-------------------------------------------------|
| POST   | `/outreach/`                           | Generate a draft message for a lead             |
| GET    | `/outreach/`                           | List all outreach messages (filterable by status)|
| GET    | `/outreach/{id}`                       | Retrieve a single message                       |
| PATCH  | `/outreach/{id}/approve`               | Mark a draft as approved (requires auth)        |
| PATCH  | `/outreach/{id}/sent`                  | Mark an approved message as sent (requires auth)|
| DELETE | `/outreach/{id}`                       | Archive / delete a draft                        |
| GET    | `/outreach/lead/{lead_id}`             | All messages associated with a specific lead    |

**Request body for `POST /outreach/`:**

```json
{
  "lead_id": 42,
  "tone": "professional",
  "context_hint": "We help mid-market firms reduce infrastructure costs."
}
```

**Response:**

```json
{
  "id": 7,
  "lead_id": 42,
  "tone": "professional",
  "subject": "Quick question about infrastructure efficiency at Acme Corp",
  "body": "Hi Jane, ...",
  "status": "draft",
  "created_at": "2026-03-12T09:00:00Z"
}
```

---

## 6. Workflow

```
Lead (hot/warm/cold)
       │
       ▼
[POST /outreach/]  ──AI draft generation──▶  Draft stored (status=draft)
       │
       ▼
Consultant reviews / edits draft in UI
       │
       ▼
[PATCH /outreach/{id}/approve]  ──▶  status=approved, approved_at set
       │
       ▼
Consultant sends via their own email client / CRM integration
       │
       ▼
[PATCH /outreach/{id}/sent]  ──▶  status=sent, sent_at set
```

---

## 7. Safety & Compliance Notes

- **No autonomous sending.** The API never sends emails; it only generates and stores drafts.
- All state transitions (`draft → approved → sent`) require an authenticated user action.
- Outreach history is immutable after `status=sent`; only archival is permitted.
- AI-generated drafts must be clearly labelled in the UI to prevent inadvertent unreviewed sends.
- PII in drafts (contact names, emails) is sourced only from leads already stored in the platform.
