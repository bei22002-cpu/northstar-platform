import React, { useEffect, useState } from 'react';
import {
  getEngines,
  createEngine,
  getMessageHistory,
  sendEngineMessage,
  AIEngine,
  AIEngineCreate,
  EngineMsg,
} from '../services/api';

const SPECIALIZATIONS = [
  { value: 'funding', label: 'Funding Specialist' },
  { value: 'market_research', label: 'Market Research' },
  { value: 'strategy', label: 'Business Strategy' },
  { value: 'outreach', label: 'Outreach & Sales' },
  { value: 'analytics', label: 'Analytics & Insights' },
  { value: 'operations', label: 'Operations' },
];

const MESSAGE_TYPES = [
  { value: 'funding_request', label: 'Funding Request' },
  { value: 'strategy_share', label: 'Strategy Share' },
  { value: 'insight_broadcast', label: 'Insight Broadcast' },
  { value: 'collaboration_proposal', label: 'Collaboration Proposal' },
  { value: 'status_update', label: 'Status Update' },
  { value: 'task_assignment', label: 'Task Assignment' },
];

export function AIEnginesPage() {
  const [engines, setEngines] = useState<AIEngine[]>([]);
  const [messages, setMessages] = useState<EngineMsg[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showMessageForm, setShowMessageForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'engines' | 'communication'>('engines');

  const [engineForm, setEngineForm] = useState<AIEngineCreate>({
    name: '',
    specialization: 'funding',
    token_balance: 1000,
  });

  const [msgForm, setMsgForm] = useState({
    sender_engine_id: 0,
    receiver_engine_id: undefined as number | undefined,
    message_type: 'status_update',
    subject: '',
    body: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eng, msgs] = await Promise.all([getEngines(), getMessageHistory()]);
      setEngines(eng);
      setMessages(msgs);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateEngine = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createEngine(engineForm);
      setEngineForm({ name: '', specialization: 'funding', token_balance: 1000 });
      setShowCreateForm(false);
      await fetchData();
    } finally {
      setSaving(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await sendEngineMessage(msgForm);
      setMsgForm({
        sender_engine_id: engines[0]?.id || 0,
        receiver_engine_id: undefined,
        message_type: 'status_update',
        subject: '',
        body: '',
      });
      setShowMessageForm(false);
      await fetchData();
    } finally {
      setSaving(false);
    }
  };

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: '#2f855a',
      idle: '#718096',
      researching: '#d97706',
      funding: '#3182ce',
      error: '#e53e3e',
    };
    return colors[status] || '#718096';
  };

  return (
    <div style={{ padding: '16px 16px 32px', maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ margin: '0 0 16px', color: '#2d3748', fontSize: 22 }}>AI Engines Dashboard</h2>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 24, borderBottom: '2px solid #e2e8f0' }}>
        {(['engines', 'communication'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              border: 'none',
              background: 'transparent',
              color: activeTab === tab ? '#3182ce' : '#718096',
              fontWeight: 600,
              fontSize: 14,
              cursor: 'pointer',
              borderBottom: activeTab === tab ? '2px solid #3182ce' : '2px solid transparent',
              marginBottom: -2,
            }}
          >
            {tab === 'engines' ? 'Engines' : 'Communication'}
          </button>
        ))}
      </div>

      {activeTab === 'engines' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <p style={{ margin: 0, color: '#718096', fontSize: 13 }}>
              {engines.length} engine(s) registered
            </p>
            <button onClick={() => setShowCreateForm(!showCreateForm)} style={btnPrimary}>
              {showCreateForm ? 'Cancel' : '+ Register Engine'}
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateEngine} style={cardStyle}>
              <h3 style={{ margin: '0 0 12px', color: '#2d3748', fontSize: 16 }}>Register New AI Engine</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Engine Name *</label>
                  <input
                    placeholder="e.g., FundBot Alpha"
                    value={engineForm.name}
                    onChange={(e) => setEngineForm({ ...engineForm, name: e.target.value })}
                    required
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={labelStyle}>Specialization *</label>
                  <select
                    value={engineForm.specialization}
                    onChange={(e) => setEngineForm({ ...engineForm, specialization: e.target.value })}
                    style={selectStyle}
                  >
                    {SPECIALIZATIONS.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Initial Token Balance</label>
                  <input
                    type="number"
                    value={engineForm.token_balance || 0}
                    onChange={(e) => setEngineForm({ ...engineForm, token_balance: Number(e.target.value) })}
                    style={inputStyle}
                  />
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <label style={labelStyle}>Description</label>
                <input
                  placeholder="Brief description of this engine's purpose"
                  value={engineForm.description || ''}
                  onChange={(e) => setEngineForm({ ...engineForm, description: e.target.value })}
                  style={inputStyle}
                />
              </div>
              <button type="submit" disabled={saving} style={{ ...btnPrimary, marginTop: 12 }}>
                {saving ? 'Creating...' : 'Register Engine'}
              </button>
            </form>
          )}

          {loading ? (
            <p style={{ color: '#718096' }}>Loading engines...</p>
          ) : engines.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
              <p style={{ color: '#718096', margin: 0 }}>No engines registered. Create your first AI engine above.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
              {engines.map((engine) => (
                <div key={engine.id} style={{
                  ...cardStyle,
                  borderTop: `3px solid ${statusColor(engine.status)}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <h4 style={{ margin: 0, color: '#2d3748', fontSize: 15 }}>{engine.name}</h4>
                    <span style={{
                      background: statusColor(engine.status), color: '#fff',
                      padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>
                      {engine.status}
                    </span>
                  </div>
                  <p style={{ margin: '0 0 12px', fontSize: 13, color: '#718096' }}>
                    {engine.description || 'No description'}
                  </p>
                  <div style={{ fontSize: 13, color: '#4a5568' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>Specialization:</span>
                      <strong>{engine.specialization.replace('_', ' ')}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>Token Balance:</span>
                      <strong style={{ color: engine.token_balance > 100 ? '#2f855a' : '#e53e3e' }}>
                        {engine.token_balance.toLocaleString()}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>Tokens Used:</span>
                      <span>{engine.tokens_consumed.toLocaleString()}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Active:</span>
                      <span>{engine.is_active ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'communication' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <p style={{ margin: 0, color: '#718096', fontSize: 13 }}>
              {messages.length} message(s) in history
            </p>
            <button onClick={() => setShowMessageForm(!showMessageForm)} style={btnPrimary}>
              {showMessageForm ? 'Cancel' : '+ Send Message'}
            </button>
          </div>

          {showMessageForm && engines.length > 0 && (
            <form onSubmit={handleSendMessage} style={cardStyle}>
              <h3 style={{ margin: '0 0 12px', color: '#2d3748', fontSize: 16 }}>Send Engine Message</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                <div>
                  <label style={labelStyle}>From Engine *</label>
                  <select
                    value={msgForm.sender_engine_id}
                    onChange={(e) => setMsgForm({ ...msgForm, sender_engine_id: Number(e.target.value) })}
                    required
                    style={selectStyle}
                  >
                    <option value={0}>Select sender</option>
                    {engines.map((e) => (
                      <option key={e.id} value={e.id}>{e.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>To Engine (empty = broadcast)</label>
                  <select
                    value={msgForm.receiver_engine_id || ''}
                    onChange={(e) => setMsgForm({
                      ...msgForm,
                      receiver_engine_id: e.target.value ? Number(e.target.value) : undefined,
                    })}
                    style={selectStyle}
                  >
                    <option value="">Broadcast to all</option>
                    {engines.map((e) => (
                      <option key={e.id} value={e.id}>{e.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Type *</label>
                  <select
                    value={msgForm.message_type}
                    onChange={(e) => setMsgForm({ ...msgForm, message_type: e.target.value })}
                    style={selectStyle}
                  >
                    {MESSAGE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <label style={labelStyle}>Subject *</label>
                <input
                  value={msgForm.subject}
                  onChange={(e) => setMsgForm({ ...msgForm, subject: e.target.value })}
                  required
                  style={inputStyle}
                />
              </div>
              <div style={{ marginTop: 8 }}>
                <label style={labelStyle}>Body *</label>
                <textarea
                  value={msgForm.body}
                  onChange={(e) => setMsgForm({ ...msgForm, body: e.target.value })}
                  required
                  rows={3}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </div>
              <button type="submit" disabled={saving} style={{ ...btnPrimary, marginTop: 12 }}>
                {saving ? 'Sending...' : 'Send Message'}
              </button>
            </form>
          )}

          {loading ? (
            <p style={{ color: '#718096' }}>Loading messages...</p>
          ) : messages.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: 'center', padding: 48 }}>
              <p style={{ color: '#718096', margin: 0 }}>
                No messages yet. AI engines will communicate here about funding strategies and collaboration.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {messages.map((msg) => {
                const sender = engines.find((e) => e.id === msg.sender_engine_id);
                const receiver = msg.receiver_engine_id ? engines.find((e) => e.id === msg.receiver_engine_id) : null;

                return (
                  <div key={msg.id} style={{
                    ...cardStyle,
                    borderLeft: `3px solid ${msgTypeColor(msg.message_type)}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                      <div style={{ fontSize: 13 }}>
                        <strong style={{ color: '#2d3748' }}>{sender?.name || `Engine #${msg.sender_engine_id}`}</strong>
                        <span style={{ color: '#718096' }}>
                          {receiver ? ` → ${receiver.name}` : ' → All Engines'}
                        </span>
                      </div>
                      <span style={{
                        background: msgTypeColor(msg.message_type), color: '#fff',
                        padding: '1px 8px', borderRadius: 10, fontSize: 10,
                        fontWeight: 600, textTransform: 'uppercase',
                      }}>
                        {msg.message_type.replace('_', ' ')}
                      </span>
                    </div>
                    <div style={{ fontWeight: 600, color: '#2d3748', fontSize: 14, marginBottom: 4 }}>
                      {msg.subject}
                    </div>
                    <p style={{ margin: 0, fontSize: 13, color: '#4a5568', whiteSpace: 'pre-wrap' }}>
                      {msg.body}
                    </p>
                    <div style={{ fontSize: 11, color: '#a0aec0', marginTop: 8 }}>
                      {new Date(msg.created_at).toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function msgTypeColor(type: string): string {
  const colors: Record<string, string> = {
    funding_request: '#e53e3e',
    strategy_share: '#3182ce',
    insight_broadcast: '#d97706',
    collaboration_proposal: '#6b46c1',
    status_update: '#718096',
    task_assignment: '#2f855a',
  };
  return colors[type] || '#718096';
}

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

const selectStyle: React.CSSProperties = {
  ...inputStyle,
};

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
