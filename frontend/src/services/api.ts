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
