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

  /** AI Engines */
  getEngines: (activeOnly = false) =>
    request("GET", `/ai-engines/?active_only=${activeOnly}`),

  createEngine: (payload) => request("POST", "/ai-engines/", payload),

  getEngine: (id) => request("GET", `/ai-engines/${id}`),

  getEngineMessages: (engineId, unreadOnly = false) =>
    request("GET", `/ai-engines/${engineId}/messages?unread_only=${unreadOnly}`),

  getMessageHistory: (engineId, messageType) => {
    const params = new URLSearchParams();
    if (engineId) params.set("engine_id", engineId);
    if (messageType) params.set("message_type", messageType);
    const qs = params.toString();
    return request("GET", `/ai-engines/messages/history${qs ? "?" + qs : ""}`);
  },

  sendEngineMessage: (payload) => request("POST", "/ai-engines/messages", payload),

  /** Funding */
  getFundingRequests: (engineId, status) => {
    const params = new URLSearchParams();
    if (engineId) params.set("engine_id", engineId);
    if (status) params.set("status", status);
    const qs = params.toString();
    return request("GET", `/funding/requests${qs ? "?" + qs : ""}`);
  },

  createFundingRequest: (payload) => request("POST", "/funding/requests", payload),

  updateFundingRequest: (id, payload) =>
    request("PATCH", `/funding/requests/${id}`, payload),

  getFundingAnalysis: (engineId) =>
    request("GET", `/funding/analysis/${engineId}`),

  getTokenHistory: (engineId) =>
    request("GET", `/funding/tokens/${engineId}/history`),

  /** Research */
  getResearchInsights: (engineId, category) => {
    const params = new URLSearchParams();
    if (engineId) params.set("engine_id", engineId);
    if (category) params.set("category", category);
    const qs = params.toString();
    return request("GET", `/research/insights${qs ? "?" + qs : ""}`);
  },

  getTopOpportunities: (limit = 10) =>
    request("GET", `/research/top-opportunities?limit=${limit}`),

  getFundingReport: (engineId) => {
    const qs = engineId ? `?engine_id=${engineId}` : "";
    return request("GET", `/research/report${qs}`);
  },

  getResearchTemplates: () => request("GET", "/research/templates"),

  /** Business Ideas */
  getBusinessIdeas: (userId, industry) => {
    const params = new URLSearchParams();
    if (userId) params.set("user_id", userId);
    if (industry) params.set("industry", industry);
    const qs = params.toString();
    return request("GET", `/business-ideas/${qs ? "?" + qs : ""}`);
  },

  submitBusinessIdea: (payload) =>
    request("POST", "/business-ideas/", payload),

  getBusinessIdea: (id) => request("GET", `/business-ideas/${id}`),

  updateBusinessIdea: (id, payload) =>
    request("PATCH", `/business-ideas/${id}`, payload),

  deleteBusinessIdea: (id) => request("DELETE", `/business-ideas/${id}`),

  getIndustries: () => request("GET", "/business-ideas/industries/list"),

  /** Rewards */
  getRewardBalance: (userId) => request("GET", `/rewards/balance/${userId}`),

  getRewardTransactions: (userId) =>
    request("GET", `/rewards/transactions/${userId}`),

  getLeaderboard: (limit = 10) =>
    request("GET", `/rewards/leaderboard?limit=${limit}`),

  getRevenueModels: () => request("GET", "/rewards/revenue-models"),

  /** Cornerstone AI Agent */
  sendAgentMessage: (message, history, provider, model, requireApproval, agentConfigId) =>
    request("POST", "/agent/chat", {
      message,
      history,
      provider: provider || "anthropic",
      model: model || null,
      require_approval: requireApproval || false,
      agent_config_id: agentConfigId || null,
    }),

  streamAgentMessage: (message, history, model) => {
    const token = localStorage.getItem("access_token");
    return fetch(`${BASE_URL}/agent/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, history, model }),
    });
  },

  approveTools: (approvals, approved) =>
    request("POST", "/agent/approve", { approvals, approved }),

  getAgentInfo: () => request("GET", "/agent/info"),

  /** Agent Audit Logs */
  getAuditLogs: (limit = 50, offset = 0) =>
    request("GET", `/agent/audit?limit=${limit}&offset=${offset}`),

  /** Agent Analytics */
  getAgentAnalytics: () => request("GET", "/agent/analytics"),

  /** Agent Marketplace */
  getMarketplaceConfigs: (category) => {
    const qs = category ? `?category=${category}` : "";
    return request("GET", `/agent/marketplace${qs}`);
  },

  createMarketplaceConfig: (payload) =>
    request("POST", "/agent/marketplace", payload),

  deleteMarketplaceConfig: (id) =>
    request("DELETE", `/agent/marketplace/${id}`),

  /** Subscription / Usage */
  getSubscription: () => request("GET", "/agent/subscription"),

  upgradeSubscription: () =>
    request("POST", "/agent/subscription/upgrade"),

  /** Platform Settings (White-Label) */
  getPlatformSettings: () => request("GET", "/agent/settings"),

  updatePlatformSettings: (payload) =>
    request("PUT", "/agent/settings", payload),
};
