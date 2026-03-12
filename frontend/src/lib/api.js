/**
 * API fetch wrapper.
 *
 * Reads the JWT access token from localStorage ("access_token") and attaches
 * it as a Bearer token on every authenticated request.
 *
 * The base URL is empty so that Vite's proxy (vite.config.js) forwards
 * /auth, /leads, and /outreach to the FastAPI backend on localhost:8000.
 */

const BASE_URL = "";

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(method, path, body = null) {
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders(),
  };

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== null ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const message = errorData.detail || res.statusText;
    throw new Error(message);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  /** Auth */
  login: (email, password) => {
    const body = new URLSearchParams({ username: email, password });
    return fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    }).then(async (res) => {
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errorData.detail || res.statusText);
      }
      return res.json();
    });
  },

  register: (email, password, full_name) =>
    request("POST", "/auth/register", { email, password, full_name }),

  /** Leads */
  listLeads: () => request("GET", "/leads"),

  createLead: (lead) => request("POST", "/leads", lead),

  /** Outreach */
  generateMessage: (lead_id, tone, service_focus, extra_context) =>
    request("POST", "/outreach/generate", {
      lead_id,
      tone,
      service_focus,
      extra_context: extra_context || undefined,
    }),

  generateFollowups: (lead_id, tone, service_focus) =>
    request("POST", "/outreach/followups", { lead_id, tone, service_focus }),
};
