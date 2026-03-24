# NorthStar Platform - Development & Testing

## Tech Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy ORM, SQLite (dev) / PostgreSQL (prod)
- **Frontend**: React with Vite, `.jsx` files (active), `.tsx` files exist but are unused duplicates
- **Auth**: HTTPBearer with JWT tokens via `get_current_user` dependency from `app.api.deps`
- **Package Management**: Poetry (backend), npm (frontend)

## Running the Application

### Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head  # Run migrations first
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:5173
```

The frontend Vite config proxies API requests (`/auth`, `/ai-engines`, `/funding`, `/research`, `/business-ideas`, `/rewards`) to `http://localhost:8000`.

## Test Credentials
- Email: `test@example.com`
- Password: `Test1234!`
- Auth: POST `/auth/login` returns `access_token` JWT

## Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```
The dev database file is `backend/test_northstar.db` (SQLite). Do not commit this file.

## Key Architecture

### API Routers & Auth Pattern
- Protected endpoints use `current_user: User = Depends(get_current_user)` 
- Public endpoints (no auth): `/business-ideas/industries/list`, `/rewards/revenue-models`, `/research/templates`
- All other endpoints under `/ai-engines/*`, `/funding/*`, `/business-ideas/*`, `/rewards/*`, `/research/*` require Bearer token

### Frontend Pages
- `src/App.jsx` — Main router with `AuthenticatedLayout` wrapper
- `src/components/Sidebar.jsx` — Responsive nav, hamburger menu at 768px breakpoint
- `src/pages/BusinessIdeas.jsx` — Idea submission + AI analysis display
- `src/pages/AIEngines.jsx` — Engine registration and messaging
- `src/pages/FundingTracker.jsx` — Funding requests with progress bars
- `src/pages/Rewards.jsx` — Token balance, leaderboard, revenue models

### AI Analysis Service
- `app/services/ai_analysis.py` — Uses OpenAI GPT-4o-mini when `OPENAI_API_KEY` env var is set
- Falls back to rule-based analysis with industry-specific insights when no API key
- Industry insights cover: technology, healthcare, retail, fintech, education, sustainability

## Building Frontend for Deployment
```bash
cd frontend
npm run build  # Output in frontend/dist/
```

## Testing Checklist
1. Verify backend starts without errors on port 8000
2. Verify frontend starts without errors on port 5173
3. Login with test credentials
4. Submit a business idea and verify AI analysis renders
5. Navigate all sidebar pages (Business Ideas, Outreach, AI Engines, Funding Tracker, Rewards)
6. Test Revenue tab on Rewards page for subscription tiers
7. Test mobile responsive at 375px — hamburger menu, sidebar slide-in/out
8. Verify protected endpoints return 401 without Bearer token
9. Verify public endpoints work without auth

## Known Issues
- Vite proxy for `/funding` may intercept React Router `/funding` path during local dev
- Empty catch blocks in frontend pages silently swallow API errors
- `.tsx` page files are unused duplicates of active `.jsx` pages
