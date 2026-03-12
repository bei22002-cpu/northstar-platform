# NorthStar Platform

An AI-driven consulting platform that automates lead generation, outreach, and proposal creation for consulting professionals.

---

## What Is NorthStar?

NorthStar is a modular backend platform built with FastAPI and PostgreSQL.  It covers:

- **Phase 1 — Auth:** Secure JWT-based user registration and login.
- **Phase 2 — Leads:** AI-assisted lead discovery (SerpAPI), scoring, and classification.
- **Phase 3+ — Outreach, Proposals, Market Intelligence, Dashboard** (planned).

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full technical design, [`docs/ROADMAP.md`](docs/ROADMAP.md) for the phase roadmap, and [`docs/OUTREACH_ENGINE.md`](docs/OUTREACH_ENGINE.md) for the Phase 3 specification.

---

## Running Locally (venv + uvicorn)

### Prerequisites

- Python 3.11+
- PostgreSQL (local install or Docker)

### Steps

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your real values (see Required Env Vars below)

# 4. Run Alembic migrations to create tables
cd backend
alembic upgrade head
cd ..

# 5. Start the API server
uvicorn app.main:app --reload --app-dir backend
```

The API is now available at <http://localhost:8000>.  
Interactive docs: <http://localhost:8000/docs>.

---

## Running via Docker Compose

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/)

### Steps

```bash
# 1. Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your real values (DATABASE_URL is set automatically by Compose)

# 2. Build and start all services (Postgres + API)
docker compose up --build
```

The API is available at <http://localhost:8000>.

Migrations (`alembic upgrade head`) run automatically on container startup via the entrypoint script.

To stop:

```bash
docker compose down
# To also remove the database volume:
docker compose down -v
```

---

## Required Environment Variables

Create `backend/.env` (never commit this file):

| Variable            | Description                                     | Example                                                  |
|---------------------|-------------------------------------------------|----------------------------------------------------------|
| `DATABASE_URL`      | SQLAlchemy PostgreSQL connection string         | `postgresql+psycopg2://user:pass@localhost/northstar_db` |
| `JWT_SECRET`        | Secret key for access tokens                    | `<random-32-char-string>`                                |
| `JWT_REFRESH_SECRET`| Secret key for refresh tokens (use different)   | `<random-32-char-string>`                                |
| `SERPAPI_KEY`       | SerpAPI key for `/leads/search`                 | `<your-serpapi-key>`                                     |
| `CORS_ORIGINS`      | Comma-separated allowed CORS origins            | `http://localhost:3000`                                  |

> When running via Docker Compose, `DATABASE_URL` is automatically set to point at the `db` service — you do not need to set it in `backend/.env`.

---

## API Endpoints

| Method | Path               | Description                                |
|--------|--------------------|--------------------------------------------|
| GET    | `/`                | Health check                               |
| POST   | `/auth/register`   | Register a new user                        |
| POST   | `/auth/login`      | Login, receive access + refresh tokens     |
| POST   | `/auth/refresh`    | Exchange refresh token for new tokens      |
| GET    | `/leads/`          | List all leads                             |
| POST   | `/leads/`          | Create a lead manually (auto-scored)       |
| GET    | `/leads/{id}`      | Get a single lead                          |
| POST   | `/leads/search`    | Search public web and import leads         |

---

## Links

- [Architecture](ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Outreach Engine Specification](docs/OUTREACH_ENGINE.md)
