import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const register = (payload: RegisterPayload) =>
  api.post('/auth/register', payload);

export const login = async (payload: LoginPayload): Promise<TokenResponse> => {
  const { data } = await api.post<TokenResponse>('/auth/login', payload);
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// ─── Leads ──────────────────────────────────────────────────────────────────

export interface Lead {
  id: number;
  company_name: string;
  contact_name: string | null;
  email: string | null;
  website: string | null;
  industry: string | null;
  score: number;
  classification: string | null;
  source: string | null;
  notes: string | null;
  created_at: string;
}

export interface LeadCreate {
  company_name: string;
  contact_name?: string;
  email?: string;
  website?: string;
  industry?: string;
  notes?: string;
}

export const getLeads = () => api.get<Lead[]>('/leads/').then((r) => r.data);

export const createLead = (payload: LeadCreate) =>
  api.post<Lead>('/leads/', payload).then((r) => r.data);

export const deleteLead = (id: number) => api.delete(`/leads/${id}`);

// ─── Outreach ───────────────────────────────────────────────────────────────

export type Tone = 'executive' | 'professional' | 'casual';
export type OutreachStatus = 'draft' | 'approved' | 'sent';

export interface OutreachMessage {
  id: number;
  lead_id: number;
  subject: string;
  body: string;
  tone: Tone;
  status: OutreachStatus;
  created_at: string;
  updated_at: string | null;
}

export interface FollowUp {
  id: number;
  outreach_id: number;
  subject: string;
  body: string;
  sequence_number: number;
  status: OutreachStatus;
  created_at: string;
  updated_at: string | null;
}

export interface OutreachWithFollowUps {
  message: OutreachMessage;
  follow_ups: FollowUp[];
}

export const getOutreachMessages = () =>
  api.get<OutreachMessage[]>('/outreach/messages').then((r) => r.data);

export const createOutreachMessage = (lead_id: number, tone: Tone) =>
  api.post<OutreachMessage>('/outreach/messages', { lead_id, tone }).then((r) => r.data);

export const approveMessage = (message_id: number) =>
  api.post<OutreachMessage>(`/outreach/messages/${message_id}/approve`).then((r) => r.data);

export const markSent = (message_id: number) =>
  api.post<OutreachMessage>(`/outreach/messages/${message_id}/sent`).then((r) => r.data);

export const generateFollowUp = (outreach_id: number, sequence_number: number) =>
  api
    .post<FollowUp>('/outreach/followups', { outreach_id, sequence_number })
    .then((r) => r.data);

export const getMessageWithFollowUps = (message_id: number) =>
  api
    .get<OutreachWithFollowUps>(`/outreach/messages/${message_id}`)
    .then((r) => r.data);

// ─── AI Engines ─────────────────────────────────────────────────────────────

export interface AIEngine {
  id: number;
  name: string;
  description: string | null;
  specialization: string;
  status: string;
  token_balance: number;
  tokens_consumed: number;
  is_active: boolean;
  last_heartbeat: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AIEngineCreate {
  name: string;
  description?: string;
  specialization: string;
  token_balance?: number;
}

export interface EngineMsg {
  id: number;
  sender_engine_id: number;
  receiver_engine_id: number | null;
  message_type: string;
  subject: string;
  body: string;
  metadata_json: string | null;
  is_read: number;
  created_at: string;
}

export const getEngines = (activeOnly = false) =>
  api.get<AIEngine[]>('/ai-engines/', { params: { active_only: activeOnly } }).then((r) => r.data);

export const createEngine = (payload: AIEngineCreate) =>
  api.post<AIEngine>('/ai-engines/', payload).then((r) => r.data);

export const getEngine = (id: number) =>
  api.get<AIEngine>(`/ai-engines/${id}`).then((r) => r.data);

export const getEngineMessages = (engineId: number, unreadOnly = false) =>
  api.get<EngineMsg[]>(`/ai-engines/${engineId}/messages`, { params: { unread_only: unreadOnly } }).then((r) => r.data);

export const getMessageHistory = (engineId?: number, messageType?: string) =>
  api.get<EngineMsg[]>('/ai-engines/messages/history', { params: { engine_id: engineId, message_type: messageType } }).then((r) => r.data);

export const sendEngineMessage = (payload: {
  sender_engine_id: number;
  receiver_engine_id?: number;
  message_type: string;
  subject: string;
  body: string;
}) => api.post<EngineMsg>('/ai-engines/messages', payload).then((r) => r.data);

// ─── Funding ────────────────────────────────────────────────────────────────

export interface FundingRequest {
  id: number;
  engine_id: number;
  funding_type: string;
  title: string;
  description: string;
  amount_requested: number;
  amount_secured: number;
  justification: string | null;
  projected_roi: number | null;
  operational_cost: number | null;
  status: string;
  strategy_details: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface FundingRequestCreate {
  engine_id: number;
  funding_type: string;
  title: string;
  description: string;
  amount_requested: number;
  justification?: string;
  projected_roi?: number;
  operational_cost?: number;
}

export interface FundingAnalysis {
  engine_id: number;
  engine_name: string;
  current_balance: number;
  total_consumed: number;
  avg_daily_burn: number;
  estimated_days_remaining: number | null;
  urgency: string;
  suggested_strategies: Array<{ type: string; priority: string; rationale: string }>;
  recommended_funding_amount: number;
}

export interface TokenTxn {
  id: number;
  engine_id: number;
  amount: number;
  balance_after: number;
  description: string;
  funding_request_id: number | null;
  created_at: string;
}

export const getFundingRequests = (engineId?: number, status?: string) =>
  api.get<FundingRequest[]>('/funding/requests', { params: { engine_id: engineId, status } }).then((r) => r.data);

export const createFundingRequest = (payload: FundingRequestCreate) =>
  api.post<FundingRequest>('/funding/requests', payload).then((r) => r.data);

export const updateFundingRequest = (id: number, payload: { status?: string; amount_secured?: number }) =>
  api.patch<FundingRequest>(`/funding/requests/${id}`, payload).then((r) => r.data);

export const getFundingAnalysis = (engineId: number) =>
  api.get<FundingAnalysis>(`/funding/analysis/${engineId}`).then((r) => r.data);

export const getTokenHistory = (engineId: number) =>
  api.get<TokenTxn[]>(`/funding/tokens/${engineId}/history`).then((r) => r.data);

// ─── Research ───────────────────────────────────────────────────────────────

export interface ResearchInsight {
  id: number;
  engine_id: number;
  category: string;
  title: string;
  summary: string;
  source_url: string | null;
  viability: string;
  estimated_amount: number | null;
  actionable_steps: string | null;
  relevance_score: number;
  created_at: string;
}

export const getResearchInsights = (engineId?: number, category?: string) =>
  api.get<ResearchInsight[]>('/research/insights', { params: { engine_id: engineId, category } }).then((r) => r.data);

export const getTopOpportunities = (limit = 10) =>
  api.get<ResearchInsight[]>('/research/top-opportunities', { params: { limit } }).then((r) => r.data);

export const getFundingReport = (engineId?: number) =>
  api.get('/research/report', { params: { engine_id: engineId } }).then((r) => r.data);

export const getResearchTemplates = () =>
  api.get('/research/templates').then((r) => r.data);

// ─── Business Ideas ─────────────────────────────────────────────────────────

export interface BusinessIdea {
  id: number;
  user_id: number;
  title: string;
  description: string;
  industry: string;
  target_market: string | null;
  budget_range: string | null;
  status: string;
  ai_analysis: string | null;
  funding_strategy: string | null;
  feedback: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface BusinessIdeaCreate {
  title: string;
  description: string;
  industry: string;
  target_market?: string;
  budget_range?: string;
}

export interface IndustryOption {
  value: string;
  label: string;
}

export const getBusinessIdeas = (userId?: number, industry?: string) =>
  api.get<BusinessIdea[]>('/business-ideas/', { params: { user_id: userId, industry } }).then((r) => r.data);

export const submitBusinessIdea = (payload: BusinessIdeaCreate, userId: number) =>
  api.post<BusinessIdea>('/business-ideas/', payload, { params: { user_id: userId } }).then((r) => r.data);

export const getBusinessIdea = (id: number) =>
  api.get<BusinessIdea>(`/business-ideas/${id}`).then((r) => r.data);

export const updateBusinessIdea = (id: number, payload: { status?: string; feedback?: string }) =>
  api.patch<BusinessIdea>(`/business-ideas/${id}`, payload).then((r) => r.data);

export const deleteBusinessIdea = (id: number) =>
  api.delete(`/business-ideas/${id}`);

export const getIndustries = () =>
  api.get<{ industries: IndustryOption[] }>('/business-ideas/industries/list').then((r) => r.data.industries);

// ─── Rewards ────────────────────────────────────────────────────────────────

export interface RewardBalance {
  id: number;
  user_id: number;
  total_tokens: number;
  lifetime_earned: number;
  lifetime_spent: number;
  tier: string;
  updated_at: string | null;
}

export interface RewardTxn {
  id: number;
  user_id: number;
  reward_type: string;
  tokens_earned: number;
  description: string;
  metadata_json: string | null;
  created_at: string;
}

export const getRewardBalance = (userId: number) =>
  api.get<RewardBalance | null>(`/rewards/balance/${userId}`).then((r) => r.data);

export const getRewardTransactions = (userId: number) =>
  api.get<RewardTxn[]>(`/rewards/transactions/${userId}`).then((r) => r.data);

export const getLeaderboard = (limit = 10) =>
  api.get<RewardBalance[]>('/rewards/leaderboard', { params: { limit } }).then((r) => r.data);

export const getRevenueModels = () =>
  api.get('/rewards/revenue-models').then((r) => r.data);
