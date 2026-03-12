import React, { useEffect, useState } from 'react';
import {
  getLeads,
  getOutreachMessages,
  createOutreachMessage,
  approveMessage,
  markSent,
  generateFollowUp,
  Lead,
  OutreachMessage,
  Tone,
} from '../services/api';

export function OutreachPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [messages, setMessages] = useState<OutreachMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLead, setSelectedLead] = useState<number | ''>('');
  const [tone, setTone] = useState<Tone>('professional');
  const [generating, setGenerating] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [l, m] = await Promise.all([getLeads(), getOutreachMessages()]);
      setLeads(l);
      setMessages(m);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLead) return;
    setGenerating(true);
    try {
      await createOutreachMessage(Number(selectedLead), tone);
      await fetchData();
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async (id: number) => {
    await approveMessage(id);
    await fetchData();
  };

  const handleMarkSent = async (id: number) => {
    await markSent(id);
    await fetchData();
  };

  const handleFollowUp = async (id: number, seq: number) => {
    await generateFollowUp(id, seq);
    alert(`Follow-up #${seq} generated! Refresh the message detail to view it.`);
  };

  const statusBadgeStyle = (status: string): React.CSSProperties => {
    const colors: Record<string, string> = {
      draft: '#718096',
      approved: '#2f855a',
      sent: '#3182ce',
    };
    return {
      background: colors[status] || '#718096',
      color: '#fff',
      padding: '2px 10px',
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'uppercase',
    };
  };

  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ margin: '0 0 24px', color: '#2d3748' }}>✉️ Outreach Engine</h2>

      {/* Generate form */}
      <div
        style={{
          background: '#fff',
          padding: 24,
          borderRadius: 10,
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
          marginBottom: 32,
        }}
      >
        <h3 style={{ margin: '0 0 16px', color: '#4a5568', fontSize: 16 }}>
          Generate Personalized Message
        </h3>
        <form
          onSubmit={handleGenerate}
          style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 200 }}>
            <label style={labelStyle}>Select Lead</label>
            <select
              value={selectedLead}
              onChange={(e) => setSelectedLead(Number(e.target.value) || '')}
              required
              style={selectStyle}
            >
              <option value="">— Choose a lead —</option>
              {leads.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.company_name} {l.contact_name ? `(${l.contact_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={labelStyle}>Tone</label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value as Tone)}
              style={selectStyle}
            >
              <option value="executive">Executive</option>
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
            </select>
          </div>

          <button type="submit" disabled={generating} style={btnPrimary}>
            {generating ? 'Generating…' : '⚡ Generate Draft'}
          </button>
        </form>
      </div>

      {/* Messages list */}
      <h3 style={{ margin: '0 0 16px', color: '#4a5568', fontSize: 16 }}>Draft & Sent Messages</h3>
      <p style={{ margin: '0 0 16px', color: '#718096', fontSize: 13 }}>
        All messages start as <strong>drafts</strong> and require human approval before sending.
        NorthStar never sends messages automatically.
      </p>

      {loading ? (
        <p style={{ color: '#718096' }}>Loading messages…</p>
      ) : messages.length === 0 ? (
        <p style={{ color: '#718096' }}>No outreach messages yet. Generate one above.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {messages.map((msg) => {
            const lead = leads.find((l) => l.id === msg.lead_id);
            return (
              <div
                key={msg.id}
                style={{
                  background: '#fff',
                  borderRadius: 10,
                  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
                  padding: 20,
                  borderLeft: `4px solid ${msg.status === 'sent' ? '#3182ce' : msg.status === 'approved' ? '#2f855a' : '#e2e8f0'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#2d3748', marginBottom: 4 }}>
                      {msg.subject}
                    </div>
                    <div style={{ fontSize: 12, color: '#718096' }}>
                      To: {lead?.company_name || `Lead #${msg.lead_id}`} &nbsp;·&nbsp;
                      Tone: <em>{msg.tone}</em> &nbsp;·&nbsp;
                      {new Date(msg.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={statusBadgeStyle(msg.status)}>{msg.status}</span>
                </div>

                <pre
                  style={{
                    background: '#f7fafc',
                    padding: 12,
                    borderRadius: 6,
                    fontSize: 13,
                    color: '#4a5568',
                    whiteSpace: 'pre-wrap',
                    margin: '8px 0',
                    fontFamily: 'inherit',
                  }}
                >
                  {msg.body}
                </pre>

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                  {msg.status === 'draft' && (
                    <button onClick={() => handleApprove(msg.id)} style={btnSuccess}>
                      ✅ Approve
                    </button>
                  )}
                  {msg.status === 'approved' && (
                    <button onClick={() => handleMarkSent(msg.id)} style={btnPrimary}>
                      📤 Mark as Sent
                    </button>
                  )}
                  {msg.status === 'sent' && (
                    <>
                      <button onClick={() => handleFollowUp(msg.id, 1)} style={btnSecondary}>
                        📩 Follow-up #1
                      </button>
                      <button onClick={() => handleFollowUp(msg.id, 2)} style={btnSecondary}>
                        📩 Follow-up #2
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const labelStyle: React.CSSProperties = { fontSize: 12, color: '#718096', fontWeight: 600 };

const selectStyle: React.CSSProperties = {
  padding: '10px 14px',
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  fontSize: 14,
  minWidth: 160,
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

const btnSuccess: React.CSSProperties = {
  ...btnPrimary,
  background: '#2f855a',
};

const btnSecondary: React.CSSProperties = {
  ...btnPrimary,
  background: '#718096',
};
