import React, { useEffect, useState } from 'react';
import {
  getEngines,
  getFundingRequests,
  createFundingRequest,
  getFundingAnalysis,
  AIEngine,
  FundingRequest,
  FundingRequestCreate,
  FundingAnalysis,
} from '../services/api';

const FUNDING_TYPES = [
  { value: 'grant', label: 'Grant' },
  { value: 'sponsorship', label: 'Sponsorship' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'crowdfunding', label: 'Crowdfunding' },
  { value: 'subscription_revenue', label: 'Subscription Revenue' },
  { value: 'ad_revenue', label: 'Ad Revenue' },
  { value: 'token_purchase', label: 'Token Purchase' },
];

export function FundingTrackerPage() {
  const [engines, setEngines] = useState<AIEngine[]>([]);
  const [requests, setRequests] = useState<FundingRequest[]>([]);
  const [analysis, setAnalysis] = useState<FundingAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedEngine, setSelectedEngine] = useState<number | null>(null);

  const [form, setForm] = useState<FundingRequestCreate>({
    engine_id: 0,
    funding_type: 'grant',
    title: '',
    description: '',
    amount_requested: 0,
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eng, reqs] = await Promise.all([getEngines(), getFundingRequests()]);
      setEngines(eng);
      setRequests(reqs);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedEngine) {
      getFundingAnalysis(selectedEngine).then(setAnalysis).catch(() => setAnalysis(null));
    } else {
      setAnalysis(null);
    }
  }, [selectedEngine]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createFundingRequest(form);
      setForm({ engine_id: 0, funding_type: 'grant', title: '', description: '', amount_requested: 0 });
      setShowForm(false);
      await fetchData();
    } finally {
      setSaving(false);
    }
  };

  const totalRequested = requests.reduce((s, r) => s + r.amount_requested, 0);
  const totalSecured = requests.reduce((s, r) => s + r.amount_secured, 0);
  const activeRequests = requests.filter((r) => !['completed', 'rejected'].includes(r.status));

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      proposed: '#718096',
      under_review: '#d97706',
      approved: '#2f855a',
      in_progress: '#3182ce',
      completed: '#6b46c1',
      rejected: '#e53e3e',
    };
    return colors[status] || '#718096';
  };

  const urgencyColor = (urgency: string) => {
    const colors: Record<string, string> = {
      critical: '#e53e3e',
      high: '#d97706',
      medium: '#3182ce',
      low: '#2f855a',
    };
    return colors[urgency] || '#718096';
  };

  return (
    <div style={{ padding: '16px 16px 32px', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ margin: '0 0 16px', color: '#2d3748', fontSize: 22 }}>Funding Tracker</h2>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
        <div style={summaryCard}>
          <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Total Requested</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#2d3748' }}>${totalRequested.toLocaleString()}</div>
        </div>
        <div style={summaryCard}>
          <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Total Secured</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#2f855a' }}>${totalSecured.toLocaleString()}</div>
        </div>
        <div style={summaryCard}>
          <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Active Requests</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#3182ce' }}>{activeRequests.length}</div>
        </div>
        <div style={summaryCard}>
          <div style={{ fontSize: 12, color: '#718096', fontWeight: 600 }}>Engines</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#6b46c1' }}>{engines.length}</div>
        </div>
      </div>

      {/* Funding Analysis */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 12px', color: '#2d3748', fontSize: 16 }}>Funding Analysis</h3>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            value={selectedEngine || ''}
            onChange={(e) => setSelectedEngine(e.target.value ? Number(e.target.value) : null)}
            style={{ ...selectStyle, maxWidth: 280 }}
          >
            <option value="">Select an engine to analyze</option>
            {engines.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
        </div>

        {analysis && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div style={{ background: '#f7fafc', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#718096' }}>Balance</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#2d3748' }}>{analysis.current_balance.toLocaleString()}</div>
              </div>
              <div style={{ background: '#f7fafc', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#718096' }}>Avg Daily Burn</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#2d3748' }}>{analysis.avg_daily_burn}</div>
              </div>
              <div style={{ background: '#f7fafc', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#718096' }}>Days Remaining</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#2d3748' }}>
                  {analysis.estimated_days_remaining ?? 'N/A'}
                </div>
              </div>
              <div style={{ background: '#f7fafc', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#718096' }}>Urgency</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: urgencyColor(analysis.urgency), textTransform: 'uppercase' }}>
                  {analysis.urgency}
                </div>
              </div>
            </div>

            <h4 style={{ margin: '0 0 8px', color: '#4a5568', fontSize: 14 }}>Suggested Strategies</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {analysis.suggested_strategies.map((s, i) => (
                <div key={i} style={{
                  background: '#f7fafc', padding: 12, borderRadius: 8,
                  borderLeft: `3px solid ${s.priority === 'high' ? '#e53e3e' : s.priority === 'medium' ? '#d97706' : '#718096'}`,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#2d3748', textTransform: 'capitalize' }}>
                    {s.type.replace(/_/g, ' ')}
                    <span style={{
                      marginLeft: 8, fontSize: 10, color: '#fff',
                      background: s.priority === 'high' ? '#e53e3e' : s.priority === 'medium' ? '#d97706' : '#718096',
                      padding: '1px 6px', borderRadius: 8,
                    }}>
                      {s.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#718096', marginTop: 4 }}>{s.rationale}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create funding request */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ margin: 0, color: '#2d3748', fontSize: 16 }}>Funding Requests</h3>
        <button onClick={() => setShowForm(!showForm)} style={btnPrimary}>
          {showForm ? 'Cancel' : '+ New Request'}
        </button>
      </div>

      {showForm && engines.length > 0 && (
        <form onSubmit={handleCreate} style={cardStyle}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <div>
              <label style={labelStyle}>Engine *</label>
              <select
                value={form.engine_id}
                onChange={(e) => setForm({ ...form, engine_id: Number(e.target.value) })}
                required
                style={selectStyle}
              >
                <option value={0}>Select engine</option>
                {engines.map((e) => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Funding Type *</label>
              <select
                value={form.funding_type}
                onChange={(e) => setForm({ ...form, funding_type: e.target.value })}
                style={selectStyle}
              >
                {FUNDING_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Amount Requested *</label>
              <input
                type="number"
                min={1}
                value={form.amount_requested || ''}
                onChange={(e) => setForm({ ...form, amount_requested: Number(e.target.value) })}
                required
                style={inputStyle}
              />
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <label style={labelStyle}>Title *</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
              style={inputStyle}
            />
          </div>
          <div style={{ marginTop: 8 }}>
            <label style={labelStyle}>Description *</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
              rows={3}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 8 }}>
            <div>
              <label style={labelStyle}>Justification</label>
              <input
                value={form.justification || ''}
                onChange={(e) => setForm({ ...form, justification: e.target.value })}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Projected ROI (%)</label>
              <input
                type="number"
                value={form.projected_roi || ''}
                onChange={(e) => setForm({ ...form, projected_roi: Number(e.target.value) })}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Operational Cost</label>
              <input
                type="number"
                value={form.operational_cost || ''}
                onChange={(e) => setForm({ ...form, operational_cost: Number(e.target.value) })}
                style={inputStyle}
              />
            </div>
          </div>
          <button type="submit" disabled={saving} style={{ ...btnPrimary, marginTop: 12 }}>
            {saving ? 'Creating...' : 'Submit Request'}
          </button>
        </form>
      )}

      {/* Request list */}
      {loading ? (
        <p style={{ color: '#718096' }}>Loading...</p>
      ) : requests.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
          <p style={{ color: '#718096', margin: 0 }}>No funding requests yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {requests.map((req) => {
            const engine = engines.find((e) => e.id === req.engine_id);
            const progress = req.amount_requested > 0
              ? Math.min(100, (req.amount_secured / req.amount_requested) * 100)
              : 0;

            return (
              <div key={req.id} style={{
                ...cardStyle,
                borderLeft: `4px solid ${statusColor(req.status)}`,
                marginBottom: 0,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#2d3748', fontSize: 15 }}>{req.title}</div>
                    <div style={{ fontSize: 12, color: '#718096' }}>
                      {engine?.name || `Engine #${req.engine_id}`} &middot;{' '}
                      {req.funding_type.replace(/_/g, ' ')} &middot;{' '}
                      {new Date(req.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={{
                    background: statusColor(req.status), color: '#fff',
                    padding: '2px 10px', borderRadius: 20, fontSize: 11,
                    fontWeight: 600, textTransform: 'uppercase',
                  }}>
                    {req.status.replace('_', ' ')}
                  </span>
                </div>

                <p style={{ margin: '0 0 12px', fontSize: 13, color: '#4a5568' }}>{req.description}</p>

                {/* Progress bar */}
                <div style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#718096', marginBottom: 4 }}>
                    <span>Secured: ${req.amount_secured.toLocaleString()}</span>
                    <span>Goal: ${req.amount_requested.toLocaleString()}</span>
                  </div>
                  <div style={{ background: '#e2e8f0', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                    <div style={{
                      background: progress >= 100 ? '#2f855a' : '#3182ce',
                      height: '100%',
                      width: `${progress}%`,
                      borderRadius: 4,
                      transition: 'width 0.3s ease',
                    }} />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#718096', flexWrap: 'wrap' }}>
                  {req.projected_roi != null && <span>ROI: {req.projected_roi}%</span>}
                  {req.operational_cost != null && <span>Op Cost: ${req.operational_cost.toLocaleString()}</span>}
                  {req.justification && <span>Justification: {req.justification}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const summaryCard: React.CSSProperties = {
  background: '#fff',
  padding: 16,
  borderRadius: 10,
  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  textAlign: 'center',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  padding: 20,
  borderRadius: 10,
  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  marginBottom: 16,
};

const inputStyle: React.CSSProperties = {
  padding: '10px 14px',
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  fontSize: 14,
  width: '100%',
  boxSizing: 'border-box',
};

const selectStyle: React.CSSProperties = { ...inputStyle };

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: '#718096',
  fontWeight: 600,
  display: 'block',
  marginBottom: 4,
};

const btnPrimary: React.CSSProperties = {
  background: '#3182ce',
  color: '#fff',
  border: 'none',
  padding: '10px 20px',
  borderRadius: 6,
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: 14,
};
