# NorthStar Platform — System Architecture

This document outlines the technical architecture for the NorthStar Consulting AI Platform. It includes all backend and frontend components implemented to date (Phases 1-4), as well as the planned system modules.

---

## 1. Overview

NorthStar is a modular AI-driven consulting platform consisting of:

- A **FastAPI** backend (Python)
- A **PostgreSQL** database
- A **React** frontend (TypeScript, Vite, mobile-responsive)
- AI-powered subsystems for:
  - Authentication
  - Lead generation (public web search)
  - Outreach (safe, human-approved messaging)
  - AI engine collaboration & communication
  - Autonomous funding identification & token management
  - Research-driven funding strategy discovery
  - User rewards & engagement tracking
  - Business idea submission & AI analysis

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
    │   ├── lead.py              # SQLAlchemy Lead ORM model
    │   ├── ai_engine.py         # AIEngine + TokenBalance ORM models
    │   ├── engine_message.py    # EngineMessage ORM model
    │   ├── funding.py           # FundingRequest ORM model
    │   ├── research.py          # ResearchInsight ORM model
    │   ├── business_idea.py     # BusinessIdea ORM model
    │   └── reward.py            # RewardTransaction ORM model
    ├── schemas/
    │   ├── user.py              # Pydantic schemas (UserCreate, UserOut, Token…)
    │   ├── lead.py              # Pydantic schemas (LeadCreate, LeadOut…)
    │   ├── ai_engine.py         # AIEngine schemas (Create, Update, Out)
    │   ├── engine_message.py    # EngineMessage schemas
    │   ├── funding.py           # FundingRequest schemas
    │   ├── research.py          # ResearchInsight schemas
    │   ├── business_idea.py     # BusinessIdea schemas
    │   └── reward.py            # Reward schemas
    ├── services/
    │   ├── auth_service.py      # User lookup, creation, authentication, token issuing
    │   ├── lead_score.py        # Rule-based lead scoring (0–100)
    │   ├── lead_classifier.py   # Score → classification (hot / warm / cold)
    │   ├── lead_scraper.py      # SerpAPI-based public web scraping
    │   ├── engine_communication.py  # AI engine messaging protocol
    │   ├── funding_strategy.py      # Autonomous funding identification & token mgmt
    │   ├── research_service.py      # Research mechanism for funding options
    │   └── reward_service.py        # User rewards & engagement tracking
    ├── api/
    │   ├── auth_router.py       # POST /auth/register, /auth/login, /auth/refresh
    │   ├── leads_router.py      # GET/POST /leads, GET /leads/{id}, POST /leads/search
    │   ├── ai_engines_router.py     # AI engine CRUD, messaging, collaboration
    │   ├── funding_router.py        # Funding requests, token management, analysis
    │   ├── research_router.py       # Research insights, top opportunities, reports
    │   ├── rewards_router.py        # Reward balance, transactions, leaderboard
    │   └── business_ideas_router.py # Business idea submission & AI analysis
    └── utils/
        └── serpapi_client.py    # Thin HTTP wrapper around SerpAPI
```

### 2.2 Database (PostgreSQL)

| Table   | Key Columns                                                                 |
|---------|-----------------------------------------------------------------------------|
| `users` | `id`, `email` (unique), `hashed_password`, `full_name`, `is_active`, `created_at` |
| `leads` | `id`, `company_name`, `contact_name`, `email`, `website`, `industry`, `score`, `classification`, `source`, `notes`, `created_at` |
| `ai_engines` | `id`, `name`, `specialization`, `status`, `token_balance`, `tokens_consumed`, `is_active`, `description`, `last_heartbeat` |
| `engine_messages` | `id`, `sender_engine_id`, `receiver_engine_id`, `message_type`, `subject`, `body`, `is_read`, `metadata` |
| `funding_requests` | `id`, `engine_id`, `funding_type`, `title`, `description`, `amount_requested`, `amount_secured`, `status`, `justification`, `projected_roi`, `operational_cost` |
| `token_balances` | `id`, `engine_id`, `amount`, `transaction_type`, `description` |
| `research_insights` | `id`, `engine_id`, `category`, `title`, `summary`, `source_url`, `viability`, `relevance_score`, `tags` |
| `business_ideas` | `id`, `user_id`, `title`, `description`, `industry`, `target_market`, `budget_range`, `status`, `ai_analysis`, `funding_strategy` |
| `reward_transactions` | `id`, `user_id`, `reward_type`, `tokens_earned`, `description` |

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

### Phase 3 — Outreach Engine (Implemented)
- Message personalization AI
- Tone selection (executive / professional / casual)
- Follow-up generator
- Safe manual-send workflow (all messages require human approval before sending)
- Outreach API + React UI

### Phase 4 — AI Engine Collaboration & Funding (Implemented)
- **AI Engine Management** — register, monitor, and manage multiple AI engines with different specializations (funding, market research, strategy, outreach, analytics, operations)
- **Engine Communication Protocol** — direct and broadcast messaging between engines for sharing funding strategies, collaboration proposals, and status updates
- **Autonomous Funding Identification** — algorithms that analyze token burn rate, estimate remaining runway, and suggest funding strategies (grants, sponsorships, partnerships, crowdfunding, subscriptions, ad revenue)
- **Research Mechanism** — funding options discovery with viability assessment, relevance scoring, and pre-built research templates
- **Business Idea Submission** — users submit ideas with industry preferences, budgets, and target markets; AI generates analysis and funding strategies
- **Reward System** — token-based user engagement rewards with tier progression (Bronze/Silver/Gold/Platinum), leaderboard, and revenue models
- **Mobile-Responsive Frontend** — all new pages use responsive design with hamburger menu navigation on mobile

  **AI Engines Endpoints:**

  | Method | Path | Description |
  |--------|------|-------------|
  | GET | `/ai-engines/` | List all registered engines |
  | POST | `/ai-engines/` | Register a new engine |
  | GET | `/ai-engines/{id}` | Get engine details |
  | PATCH | `/ai-engines/{id}` | Update engine |
  | POST | `/ai-engines/{id}/heartbeat` | Update engine heartbeat |
  | POST | `/ai-engines/messages` | Send inter-engine message |
  | GET | `/ai-engines/messages/history` | Get communication history |
  | GET | `/ai-engines/{id}/messages` | Get messages for an engine |
  | POST | `/ai-engines/{id}/broadcast-insight` | Broadcast funding insight |
  | POST | `/ai-engines/{sender}/collaborate/{receiver}` | Propose collaboration |

  **Funding Endpoints:**

  | Method | Path | Description |
  |--------|------|-------------|
  | GET | `/funding/requests` | List funding requests |
  | POST | `/funding/requests` | Create funding request |
  | PATCH | `/funding/requests/{id}` | Update request status |
  | GET | `/funding/tokens/{engine_id}/history` | Token transaction history |
  | POST | `/funding/tokens/{engine_id}/debit` | Debit tokens |
  | GET | `/funding/analysis/{engine_id}` | Funding needs analysis |

  **Research Endpoints:**

  | Method | Path | Description |
  |--------|------|-------------|
  | GET | `/research/insights` | List research insights |
  | POST | `/research/insights` | Create insight |
  | GET | `/research/top-opportunities` | Top funding opportunities |
  | GET | `/research/report` | Generate funding report |
  | GET | `/research/templates` | Get research templates |

  **Business Ideas Endpoints:**

  | Method | Path | Description |
  |--------|------|-------------|
  | GET | `/business-ideas/` | List business ideas |
  | POST | `/business-ideas/` | Submit idea for AI analysis |
  | GET | `/business-ideas/{id}` | Get idea details |
  | PATCH | `/business-ideas/{id}` | Update idea |
  | DELETE | `/business-ideas/{id}` | Delete idea |
  | GET | `/business-ideas/industries/list` | Available industries |

  **Rewards Endpoints:**

  | Method | Path | Description |
  |--------|------|-------------|
  | GET | `/rewards/balance/{user_id}` | User reward balance |
  | POST | `/rewards/award` | Award tokens |
  | POST | `/rewards/spend` | Spend tokens |
  | GET | `/rewards/transactions/{user_id}` | Transaction history |
  | GET | `/rewards/leaderboard` | Top users leaderboard |
  | GET | `/rewards/revenue-models` | Revenue model options |

### Phase 5 — Market Intelligence Engine
- Public search trends analysis
- Industry clustering (public info only)
- Competitor insights
- Opportunities summary
- Market AI agent

### Phase 6 — Deployment
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
| Frontend       | React + TypeScript + Vite           |
| Mobile CSS     | Responsive inline styles + media queries |
| Deployment (planned) | Docker + cloud PaaS           |

---

## 5. Security & Compliance Notes

- All automation is **human-approved** — no automated message sending.
- Lead discovery uses only **publicly accessible** sources via SerpAPI.
- Secrets (`.env`) are excluded from version control via `.gitignore`.
- JWT secrets are loaded from environment variables and never hardcoded in production.
