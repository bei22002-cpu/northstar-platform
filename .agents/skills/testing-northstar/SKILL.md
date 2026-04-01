# Testing NorthStar Platform

How to run and test the NorthStar Platform (FastAPI backend + React/Vite frontend).

## Devin Secrets Needed

- `ANTHROPIC_API_KEY` — Required for agent chat functionality. Without it, the agent page shows "UNCONFIGURED" and returns graceful error messages.
- `OPENAI_API_KEY` (optional) — For testing OpenAI/GPT-4 model provider.
- `GOOGLE_API_KEY` (optional) — For testing Google Gemini model provider.

## Backend Setup

```bash
cd /home/ubuntu/repos/northstar-platform/backend
source .venv/bin/activate
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Backend runs on port 8000
- Database is SQLite, tables auto-created on startup via `Base.metadata.create_all()`
- The `--reload` flag enables auto-reload on code changes

## Frontend Setup

### Development (Vite Dev Server)

```bash
cd /home/ubuntu/repos/northstar-platform/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

**Warning**: The Vite dev server uses WebSocket for HMR, which may cause page loading issues in manually-launched Chrome instances. If Chrome shows "Loading..." indefinitely with the Vite dev server, use the production build approach below instead.

### Production Build (Recommended for Testing)

```bash
cd /home/ubuntu/repos/northstar-platform/frontend
npx vite build
```

Then serve with a reverse proxy that handles both static files and API proxying:

```python
# /tmp/proxy_server.py — serves static frontend + proxies /auth/* and /agent/* to backend
import http.server, os, urllib.request, urllib.error

BACKEND = "http://127.0.0.1:8000"
DIST_DIR = "/home/ubuntu/repos/northstar-platform/frontend/dist"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=DIST_DIR, **kw)
    def _is_api(self): return self.path.startswith(('/auth/', '/agent/', '/docs', '/openapi'))
    def _proxy(self):
        url = BACKEND + self.path
        headers = {k: v for k, v in self.headers.items() if k.lower() != 'host'}
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))) if self.headers.get('Content-Length') else None
        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ('transfer-encoding', 'connection'): self.send_header(k, v)
                self.end_headers(); self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ('transfer-encoding', 'connection'): self.send_header(k, v)
            self.end_headers(); self.wfile.write(e.read())
    def do_GET(self):
        if self._is_api(): return self._proxy()
        path = self.translate_path(self.path)
        if not os.path.exists(path) and '.' not in os.path.basename(self.path): self.path = '/index.html'
        return super().do_GET()
    def do_POST(self): return self._proxy()
    def do_PUT(self): return self._proxy()
    def do_DELETE(self): return self._proxy()
    def log_message(self, *a): pass

http.server.HTTPServer(('0.0.0.0', 5173), ProxyHandler).serve_forever()
```

This is necessary because the frontend's `api.js` uses `BASE_URL = ""` (empty string), meaning all API calls go to the same origin. Without the proxy, API calls to `/auth/login` or `/agent/chat` would hit the static file server instead of the backend.

## Test User

Register a test user via API before testing:

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@northstar.dev","password":"Test1234"}'
```

Credentials: `test@northstar.dev` / `Test1234`

## Browser Testing

- Use `http://127.0.0.1:5173/login` (not `localhost`) when launching Chrome manually
- The frontend entry point is `.jsx` files, not `.tsx`
- Key pages to test:
  - `/agent` — Cornerstone Agent (chat, multi-model, approvals, streaming, tokens)
  - `/analytics` — Analytics Dashboard (messages, tools, model usage charts)
  - `/marketplace` — Agent Marketplace (create/browse agent configs)
  - `/settings` — Platform Settings (white-label branding, subscription)

## Common Issues

1. **Vite dev server + Chrome loading hang**: The WebSocket HMR connection may block page loads in manually-launched Chrome. Use the production build + proxy approach instead.

2. **Port already in use**: Kill old processes with `fuser -k 8000/tcp` or `fuser -k 5173/tcp`.

3. **SQLAlchemy compatibility**: Avoid using `sqlfunc.cast()` with `sqlfunc.text()` for date operations — it causes `AttributeError: 'Function' object has no attribute '_static_cache_key'`. Use Python-based grouping with `Counter` instead.

4. **Frontend API field names vs backend**: The frontend and backend may use different field names for the same data. Check both `api.js` and the backend router for field name alignment. Key mappings:
   - Backend `tokens_input`/`tokens_output` → Frontend constructs `{input_tokens, output_tokens}`
   - Backend `messages_by_day` → Frontend `dailyMessages`
   - Backend `top_tools` → Frontend `toolUsage`
   - Backend `messages_by_provider` → Frontend `modelUsage`
