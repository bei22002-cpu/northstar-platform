# NorthStar Platform

AI-powered consulting lead and outreach platform.

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | JWT Authentication | ✅ |
| Phase 2 | Lead Engine (CRUD) | ✅ |
| Phase 3 | Outreach Engine (generate only, no send) | ✅ |

## Quick start

### Backend

```bash
cd backend
cp .env.example .env          # fill in secrets
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

### Tests

```bash
cd backend
pytest tests/ -v
```

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Outreach Engine](docs/outreach_engine.md)

## Security

- `.env` is gitignored; never commit secrets.
- The outreach engine generates content only — no email is sent.
