# Cornerstone AI — SaaS Platform

A monetizable web application that lets users sign up, pick a plan, and chat with an AI agent powered by Claude. Includes user authentication, usage metering, Stripe billing, and an admin dashboard.

## Features

- **User Authentication** — Email/password signup and login with JWT tokens
- **Tiered Plans** — Free ($0), Pro ($29/mo), Enterprise ($99/mo)
- **AI Chat** — Real-time chat with Claude (Haiku, Sonnet, Opus based on plan)
- **Usage Metering** — Token counting with monthly limits per plan
- **Stripe Billing** — Checkout sessions, subscription management, webhooks
- **Admin Dashboard** — User management, revenue tracking, usage analytics
- **Conversation History** — Persistent conversations stored in SQLite
- **Cost Tracking** — Per-request cost calculation and display

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn sqlalchemy python-dotenv anthropic pyjwt jinja2 python-multipart
```

Optional (for Stripe payments):
```bash
pip install stripe
```

### 2. Configure environment

```bash
cp agent_saas/.env.example agent_saas/.env
```

Edit `agent_saas/.env` and add your Anthropic API key(s). Stripe keys are optional — the platform works without them (users just can't upgrade to paid plans via Stripe).

### 3. Run the server

```bash
uvicorn agent_saas.app:app --port 8000 --reload
```

Open http://localhost:8000

### 4. Default admin account

On first startup, an admin account is created:
- **Email:** admin@cornerstone.ai
- **Password:** admin123

Change these in your `.env` file (`ADMIN_EMAIL` and `ADMIN_PASSWORD`).

## Plans & Pricing

| Plan | Price | Tokens/Month | Models | Key Features |
|------|-------|-------------|--------|--------------|
| Free | $0 | 50,000 | Haiku | Basic AI chat |
| Pro | $29/mo | 500,000 | Haiku, Sonnet | RAG search, memory, priority support |
| Enterprise | $99/mo | 2,000,000 | All (incl. Opus) | Multi-agent, GitHub, testing, linting |

## Stripe Setup (Optional)

1. Create a [Stripe account](https://dashboard.stripe.com)
2. Go to **Products** → Create two products:
   - **Pro** ($29/mo recurring) — copy the Price ID
   - **Enterprise** ($99/mo recurring) — copy the Price ID
3. Go to **Developers** → **API Keys** — copy Secret and Publishable keys
4. Set up a webhook endpoint pointing to `https://your-domain/api/billing/webhook`
5. Add all keys to your `.env` file

Without Stripe configured, the admin can manually upgrade users from the admin dashboard.

## Pages

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/pricing` | Pricing plans |
| `/signup` | Create account |
| `/login` | Sign in |
| `/chat` | AI chat interface |
| `/dashboard` | Usage stats & billing |
| `/admin` | Admin dashboard (admin only) |

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/chat` | Send a chat message |
| POST | `/api/conversations/new` | Create new conversation |
| DELETE | `/api/conversations/{id}` | Delete a conversation |
| POST | `/api/billing/checkout` | Start Stripe checkout |
| POST | `/api/billing/webhook` | Stripe webhook handler |
| GET | `/api/billing/portal` | Stripe billing portal |
| POST | `/api/admin/users/{id}/plan` | Update user plan (admin) |
| POST | `/api/admin/users/{id}/toggle` | Enable/disable user (admin) |

## Architecture

```
agent_saas/
├── __init__.py          # Package marker
├── app.py               # FastAPI app with all routes
├── config.py            # Environment configuration
├── database.py          # SQLite + SQLAlchemy setup
├── models.py            # User, Conversation, Message, UsageRecord
├── auth.py              # JWT auth, password hashing, signup/login
├── billing.py           # Stripe integration
├── chat.py              # AI chat engine with usage metering
├── static/
│   └── style.css        # Global styles
├── templates/
│   ├── landing.html     # Marketing landing page
│   ├── pricing.html     # Pricing plans page
│   ├── login.html       # Login form
│   ├── signup.html      # Signup form
│   ├── chat.html        # Chat interface
│   ├── dashboard.html   # User dashboard
│   ├── admin.html       # Admin dashboard
│   └── billing_success.html  # Payment success page
├── .env.example         # Configuration template
└── README.md            # This file
```

## Revenue Model

Your profit = subscription revenue - API costs.

Example with 100 users:
- 80 Free users: $0 revenue, minimal API cost (50K tokens each)
- 15 Pro users: $435/mo revenue, ~$22/mo API cost
- 5 Enterprise users: $495/mo revenue, ~$30/mo API cost
- **Total: ~$930/mo revenue, ~$52/mo cost = ~$878/mo profit**

The admin dashboard shows real-time revenue vs. API cost tracking.
