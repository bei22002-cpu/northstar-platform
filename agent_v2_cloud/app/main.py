"""Cornerstone AI Agent v2 Cloud Server."""
from __future__ import annotations
import json, os, pathlib
from typing import Any
import httpx
from dotenv import load_dotenv

# Load .env from the app directory (for Fly.io deployment)
_env_path = pathlib.Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
# Also try project root .env
_root_env = pathlib.Path(__file__).resolve().parent.parent / ".env"
if _root_env.exists():
    load_dotenv(_root_env)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Cornerstone AI Agent v2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class FreeMultiProvider:
    PROVIDERS = [
        ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "Groq"),
        ("GEMINI_API_KEY", None, "gemini-2.0-flash", "Gemini"),
        ("CEREBRAS_API_KEY", "https://api.cerebras.ai/v1", "llama3.1-70b", "Cerebras"),
        ("GITHUB_TOKEN", "https://models.inference.ai.azure.com", "gpt-4o", "GitHub Models"),
    ]
    def __init__(self) -> None:
        self._providers: list[dict[str, Any]] = []
        self._current_idx = 0
        self._call_count = 0
        for env_key, base_url, default_model, name in self.PROVIDERS:
            key = os.getenv(env_key, "")
            if key:
                if name == "Gemini":
                    self._providers.append({"name": name, "type": "gemini", "key": key, "model": os.getenv("GEMINI_MODEL", default_model)})
                else:
                    self._providers.append({"name": name, "type": "openai", "key": key, "base_url": base_url, "model": default_model})
        if not self._providers:
            raise RuntimeError("No free API keys found. Set at least one: GROQ_API_KEY, GEMINI_API_KEY, CEREBRAS_API_KEY, GITHUB_TOKEN")
    @property
    def provider_names(self) -> str:
        return ", ".join(p["name"] for p in self._providers)
    def create_message(self, messages: list[dict[str, str]], system: str = "") -> str:
        last_error: Exception | None = None
        for _ in range(len(self._providers)):
            p = self._providers[self._current_idx]
            try:
                return self._call_gemini(p, messages, system) if p["type"] == "gemini" else self._call_openai(p, messages, system)
            except Exception as exc:
                last_error = exc
                self._current_idx = (self._current_idx + 1) % len(self._providers)
        raise RuntimeError(f"All providers failed. Last: {last_error}")
    def _call_openai(self, prov: dict[str, Any], messages: list[dict[str, str]], system: str) -> str:
        oai = []
        if system: oai.append({"role": "system", "content": system})
        oai.extend(messages)
        payload = {"model": prov["model"], "messages": oai, "max_tokens": 4096, "stream": False}
        url = f"{prov['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {prov['key']}", "User-Agent": "CornerstoneAI/1.0"}
        resp = httpx.post(url, json=payload, headers=headers, timeout=120.0)
        if resp.status_code != 200:
            print(f"[Cornerstone AI] {prov['name']} error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
        body = resp.json()
        self._call_count += 1
        choices = body.get("choices", [])
        return choices[0].get("message", {}).get("content", "") if choices else "(empty)"
    def _call_gemini(self, prov: dict[str, Any], messages: list[dict[str, str]], system: str) -> str:
        contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
        payload: dict[str, Any] = {"contents": contents}
        if system: payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{prov['model']}:generateContent?key={prov['key']}"
        headers = {"Content-Type": "application/json", "User-Agent": "CornerstoneAI/1.0"}
        resp = httpx.post(url, json=payload, headers=headers, timeout=120.0)
        if resp.status_code != 200:
            print(f"[Cornerstone AI] Gemini error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
        body = resp.json()
        self._call_count += 1
        cands = body.get("candidates", [])
        if not cands: return "(empty)"
        return "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))

SYSTEM_PROMPT = "You are Cornerstone AI, a powerful and helpful AI assistant. You help users with coding, writing, analysis, math, and any other tasks. You are knowledgeable, precise, and friendly. Give thorough but concise answers. When writing code, always include the language in code blocks. You are running on a cloud server so you are available 24/7."
sessions: dict[str, list[dict[str, str]]] = {}
MAX_HISTORY = 40
def get_session(sid: str) -> list[dict[str, str]]:
    if sid not in sessions: sessions[sid] = []
    return sessions[sid]

provider: FreeMultiProvider | None = None

@app.on_event("startup")
async def startup():
    global provider
    try:
        provider = FreeMultiProvider()
        print(f"[Cornerstone AI] Ready: {provider.provider_names}")
    except RuntimeError as e:
        print(f"[Cornerstone AI] WARNING: {e}")

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "provider_ready": provider is not None}

@app.post("/api/chat")
async def chat(body: dict[str, Any]):
    if not provider:
        return JSONResponse(status_code=503, content={"error": "No AI provider. Set GROQ_API_KEY or GEMINI_API_KEY env var."})
    sid = body.get("session_id", "default")
    msg = body.get("message", "").strip()
    if not msg: return {"response": "", "session_id": sid}
    hist = get_session(sid)
    hist.append({"role": "user", "content": msg})
    if len(hist) > MAX_HISTORY: hist[:] = hist[-MAX_HISTORY:]
    try:
        reply = provider.create_message(hist, system=SYSTEM_PROMPT)
    except Exception as e:
        reply = f"Error: {e}"
    hist.append({"role": "assistant", "content": reply})
    if len(hist) > MAX_HISTORY: hist[:] = hist[-MAX_HISTORY:]
    return {"response": reply, "session_id": sid}

@app.get("/api/sessions/{session_id}")
async def get_sess(session_id: str):
    return {"session_id": session_id, "messages": sessions.get(session_id, [])}

@app.delete("/api/sessions/{session_id}")
async def clear_sess(session_id: str):
    sessions.pop(session_id, None)
    return {"status": "cleared"}

@app.get("/api/status")
async def status():
    return {"status": "running", "provider_ready": provider is not None, "providers": provider.provider_names if provider else "none", "active_sessions": len(sessions), "total_calls": provider._call_count if provider else 0}

@app.get("/", response_class=HTMLResponse)
async def root():
    return CHAT_HTML

CHAT_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Cornerstone AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f0f23;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
header{background:linear-gradient(135deg,#1a1a3e,#2d1b69);padding:16px 24px;border-bottom:1px solid #333;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:1.3rem;background:linear-gradient(90deg,#7c3aed,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.st{font-size:.8rem;color:#10b981;display:flex;align-items:center;gap:6px}
.dot{width:8px;height:8px;background:#10b981;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
#chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.m{max-width:80%;padding:12px 16px;border-radius:12px;line-height:1.6;font-size:.95rem;white-space:pre-wrap;word-wrap:break-word}
.m.u{align-self:flex-end;background:#7c3aed;color:#fff;border-bottom-right-radius:4px}
.m.a{align-self:flex-start;background:#1e1e3f;border:1px solid #333;border-bottom-left-radius:4px}
.m.a code{background:#0d0d1a;padding:2px 6px;border-radius:4px;font-family:'Fira Code',monospace;font-size:.85rem}
.m.a pre{background:#0d0d1a;padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0}
.m.a pre code{background:none;padding:0}
.m.e{align-self:center;background:#3b1111;border:1px solid #7f1d1d;color:#fca5a5;font-size:.85rem}
.tp{align-self:flex-start;color:#666;font-style:italic;font-size:.85rem;padding:8px 16px}
#bar{padding:16px 20px;background:#1a1a2e;border-top:1px solid #333;display:flex;gap:12px}
#bar textarea{flex:1;background:#0f0f23;border:1px solid #444;border-radius:12px;padding:12px 16px;color:#e0e0e0;font-size:.95rem;font-family:inherit;resize:none;outline:none;min-height:48px;max-height:150px}
#bar textarea:focus{border-color:#7c3aed}
#bar button{background:linear-gradient(135deg,#7c3aed,#06b6d4);border:none;border-radius:12px;padding:12px 24px;color:#fff;font-weight:600;cursor:pointer;font-size:.95rem;transition:opacity .2s}
#bar button:hover{opacity:.85}
#bar button:disabled{opacity:.4;cursor:not-allowed}
.wl{text-align:center;color:#666;margin-top:20vh}
.wl h2{font-size:1.5rem;margin-bottom:8px;background:linear-gradient(90deg,#7c3aed,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.wl p{font-size:.9rem}
@media(max-width:600px){.m{max-width:95%}header h1{font-size:1.1rem}}
</style></head><body>
<header><h1>Cornerstone AI</h1><div class="st" id="st"><div class="dot"></div><span>Connecting...</span></div></header>
<div id="chat"><div class="wl"><h2>Welcome to Cornerstone AI</h2><p>Your AI assistant running 24/7 in the cloud. Type a message to begin.</p></div></div>
<div id="bar"><textarea id="inp" placeholder="Type a message..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"></textarea><button id="btn" onclick="send()">Send</button></div>
<script>
const chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('btn'),st=document.getElementById('st');
const sid='s_'+Math.random().toString(36).substr(2,9);let wl=true;
inp.addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,150)+'px'});
async function ck(){try{const r=await fetch('/api/status');const d=await r.json();st.innerHTML=d.provider_ready?'<div class="dot"></div><span>Online &mdash; '+d.providers+'</span>':'<div class="dot" style="background:#ef4444"></div><span>No AI provider</span>'}catch(e){st.innerHTML='<div class="dot" style="background:#ef4444"></div><span>Offline</span>'}}
ck();setInterval(ck,30000);
function add(r,t){if(wl){const w=chat.querySelector('.wl');if(w)w.remove();wl=false}const d=document.createElement('div');d.className='m '+r;if(r==='a'){let h=t.replace(/```(\\w*)\\n([\\s\\S]*?)```/g,'<pre><code>$2</code></pre>');h=h.replace(/`([^`]+)`/g,'<code>$1</code>');h=h.replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>');d.innerHTML=h}else{d.textContent=t}chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
function showT(){const d=document.createElement('div');d.className='tp';d.id='tp';d.textContent='Cornerstone AI is thinking...';chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
function hideT(){const e=document.getElementById('tp');if(e)e.remove()}
async function send(){const t=inp.value.trim();if(!t)return;inp.value='';inp.style.height='auto';btn.disabled=true;add('u',t);showT();try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid,message:t})});const d=await r.json();hideT();if(d.error)add('e',d.error);else add('a',d.response)}catch(e){hideT();add('e','Failed to connect: '+e.message)}btn.disabled=false;inp.focus()}
inp.focus();
</script></body></html>"""
