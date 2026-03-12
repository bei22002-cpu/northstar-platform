# Roadmap

## ✅ Phase 1 — Authentication

- JWT-based registration and login (`POST /auth/register`, `POST /auth/login`)
- Password hashing with bcrypt
- Bearer token auth dependency reusable by all protected routes

## ✅ Phase 2 — Lead Engine

- Lead ORM model: `company_name`, `website`, `industry`, `description`, `score`, `status`, `date_discovered`
- CRUD endpoints: `GET /leads`, `POST /leads`, `GET /leads/{id}`, `DELETE /leads/{id}`
- All endpoints protected by Phase 1 auth

## ✅ Phase 3 — Outreach Engine

- Template-based (deterministic) outreach generation, no external LLM required
- `POST /outreach/generate` — returns personalised subject + body
- `POST /outreach/followups` — returns 3-step follow-up sequence
- Extension point for OpenAI generation (`LLM_PROVIDER=openai`)
- React UI: lead selector, tone/focus pickers, generate + copy-to-clipboard
- Auth-protected; content generated only — no email sending
- 31 unit tests covering all tone × service_focus combinations

## 🔲 Phase 4 — Prospecting (future)

- Automated lead discovery from web/news sources
- Lead scoring pipeline
- CRM integration (HubSpot, Salesforce)

## 🔲 Phase 5 — Analytics (future)

- Outreach performance tracking
- Lead pipeline dashboard
- Conversion metrics
