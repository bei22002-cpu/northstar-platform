import React, { useEffect, useState } from 'react';
import { getLeads, createLead, deleteLead, Lead, LeadCreate } from '../services/api';

export function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LeadCreate>({ company_name: '' });
  const [saving, setSaving] = useState(false);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const data = await getLeads();
      setLeads(data);
    } catch (_) {
      // handle silently
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createLead(form);
      setForm({ company_name: '' });
      setShowForm(false);
      await fetchLeads();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this lead?')) return;
    await deleteLead(id);
    await fetchLeads();
  };

  const badgeColor = (cls: string | null) => {
    if (cls === 'hot') return '#c53030';
    if (cls === 'warm') return '#d97706';
    return '#718096';
  };

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#2d3748' }}>Leads</h2>
        <button onClick={() => setShowForm(!showForm)} style={btnPrimary}>
          {showForm ? 'Cancel' : '+ Add Lead'}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          style={{
            background: '#fff',
            padding: 24,
            borderRadius: 10,
            boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
            marginBottom: 24,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 12,
          }}
        >
          <input
            placeholder="Company Name *"
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            required
            style={inputStyle}
          />
          <input
            placeholder="Contact Name"
            value={form.contact_name || ''}
            onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            style={inputStyle}
          />
          <input
            placeholder="Email"
            value={form.email || ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            style={inputStyle}
          />
          <input
            placeholder="Website"
            value={form.website || ''}
            onChange={(e) => setForm({ ...form, website: e.target.value })}
            style={inputStyle}
          />
          <input
            placeholder="Industry"
            value={form.industry || ''}
            onChange={(e) => setForm({ ...form, industry: e.target.value })}
            style={inputStyle}
          />
          <input
            placeholder="Notes"
            value={form.notes || ''}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            style={inputStyle}
          />
          <button type="submit" disabled={saving} style={{ ...btnPrimary, gridColumn: '1 / -1' }}>
            {saving ? 'Saving…' : 'Save Lead'}
          </button>
        </form>
      )}

      {loading ? (
        <p style={{ color: '#718096' }}>Loading leads…</p>
      ) : leads.length === 0 ? (
        <p style={{ color: '#718096' }}>No leads yet. Add your first lead above.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 10, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
            <thead>
              <tr style={{ background: '#edf2f7' }}>
                {['Company', 'Contact', 'Industry', 'Score', 'Class', 'Actions'].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={tdStyle}>{lead.company_name}</td>
                  <td style={tdStyle}>{lead.contact_name || '—'}</td>
                  <td style={tdStyle}>{lead.industry || '—'}</td>
                  <td style={tdStyle}>{lead.score.toFixed(0)}</td>
                  <td style={tdStyle}>
                    <span style={{
                      background: badgeColor(lead.classification),
                      color: '#fff',
                      padding: '2px 10px',
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>
                      {lead.classification || '—'}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <button
                      onClick={() => handleDelete(lead.id)}
                      style={{ background: 'transparent', border: 'none', color: '#e53e3e', cursor: 'pointer', fontSize: 14 }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '10px 14px',
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  fontSize: 14,
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

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '12px 16px',
  fontSize: 13,
  fontWeight: 600,
  color: '#4a5568',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 14,
  color: '#2d3748',
};
