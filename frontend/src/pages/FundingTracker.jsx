import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const FUNDING_TYPES = [
  { value: "grant", label: "Grant" },
  { value: "sponsorship", label: "Sponsorship" },
  { value: "partnership", label: "Partnership" },
  { value: "crowdfunding", label: "Crowdfunding" },
  { value: "subscription_revenue", label: "Subscription Revenue" },
  { value: "ad_revenue", label: "Ad Revenue" },
  { value: "token_purchase", label: "Token Purchase" },
];

const STATUS_COLORS = { proposed: "#718096", under_review: "#d97706", approved: "#2f855a", in_progress: "#3182ce", completed: "#6b46c1", rejected: "#e53e3e" };
const URGENCY_COLORS = { critical: "#e53e3e", high: "#d97706", medium: "#3182ce", low: "#2f855a" };

const s = {
  page: { padding: "16px 16px 32px", maxWidth: 960, margin: "0 auto" },
  card: { background: "#fff", padding: 20, borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", marginBottom: 16 },
  summary: { background: "#fff", padding: 16, borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", textAlign: "center" },
  input: { padding: "10px 14px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14, width: "100%", boxSizing: "border-box" },
  label: { fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 },
  btnPrimary: { background: "#3182ce", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 14 },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 },
  badge: (color) => ({ background: color, color: "#fff", padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }),
};

export default function FundingTracker() {
  const [engines, setEngines] = useState([]);
  const [requests, setRequests] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedEngine, setSelectedEngine] = useState(null);
  const [form, setForm] = useState({ engine_id: 0, funding_type: "grant", title: "", description: "", amount_requested: 0, justification: "", projected_roi: "", operational_cost: "" });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eng, reqs] = await Promise.all([api.getEngines(), api.getFundingRequests()]);
      setEngines(eng);
      setRequests(reqs);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    if (selectedEngine) {
      api.getFundingAnalysis(selectedEngine).then(setAnalysis).catch(() => setAnalysis(null));
    } else { setAnalysis(null); }
  }, [selectedEngine]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form };
      if (payload.projected_roi) payload.projected_roi = Number(payload.projected_roi);
      else delete payload.projected_roi;
      if (payload.operational_cost) payload.operational_cost = Number(payload.operational_cost);
      else delete payload.operational_cost;
      if (!payload.justification) delete payload.justification;
      await api.createFundingRequest(payload);
      setForm({ engine_id: 0, funding_type: "grant", title: "", description: "", amount_requested: 0, justification: "", projected_roi: "", operational_cost: "" });
      setShowForm(false);
      await fetchData();
    } finally { setSaving(false); }
  };

  const totalRequested = requests.reduce((sum, r) => sum + r.amount_requested, 0);
  const totalSecured = requests.reduce((sum, r) => sum + r.amount_secured, 0);
  const activeRequests = requests.filter((r) => !["completed", "rejected"].includes(r.status));

  return (
    <div style={s.page}>
      <h2 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 22 }}>Funding Tracker</h2>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
        <div style={s.summary}><div style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Total Requested</div><div style={{ fontSize: 22, fontWeight: 700, color: "#2d3748" }}>${totalRequested.toLocaleString()}</div></div>
        <div style={s.summary}><div style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Total Secured</div><div style={{ fontSize: 22, fontWeight: 700, color: "#2f855a" }}>${totalSecured.toLocaleString()}</div></div>
        <div style={s.summary}><div style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Active Requests</div><div style={{ fontSize: 22, fontWeight: 700, color: "#3182ce" }}>{activeRequests.length}</div></div>
        <div style={s.summary}><div style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Engines</div><div style={{ fontSize: 22, fontWeight: 700, color: "#6b46c1" }}>{engines.length}</div></div>
      </div>

      {/* Funding Analysis */}
      <div style={{ ...s.card, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 12px", color: "#2d3748", fontSize: 16 }}>Funding Analysis</h3>
        <select value={selectedEngine || ""} onChange={(e) => setSelectedEngine(e.target.value ? Number(e.target.value) : null)} style={{ ...s.input, maxWidth: 280 }}>
          <option value="">Select an engine to analyze</option>
          {engines.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
        {analysis && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
              <div style={{ background: "#f7fafc", padding: 12, borderRadius: 8 }}><div style={{ fontSize: 11, color: "#718096" }}>Balance</div><div style={{ fontSize: 18, fontWeight: 700, color: "#2d3748" }}>{analysis.current_balance.toLocaleString()}</div></div>
              <div style={{ background: "#f7fafc", padding: 12, borderRadius: 8 }}><div style={{ fontSize: 11, color: "#718096" }}>Avg Daily Burn</div><div style={{ fontSize: 18, fontWeight: 700, color: "#2d3748" }}>{analysis.avg_daily_burn}</div></div>
              <div style={{ background: "#f7fafc", padding: 12, borderRadius: 8 }}><div style={{ fontSize: 11, color: "#718096" }}>Days Remaining</div><div style={{ fontSize: 18, fontWeight: 700, color: "#2d3748" }}>{analysis.estimated_days_remaining ?? "N/A"}</div></div>
              <div style={{ background: "#f7fafc", padding: 12, borderRadius: 8 }}><div style={{ fontSize: 11, color: "#718096" }}>Urgency</div><div style={{ fontSize: 18, fontWeight: 700, color: URGENCY_COLORS[analysis.urgency] || "#718096", textTransform: "uppercase" }}>{analysis.urgency}</div></div>
            </div>
            <h4 style={{ margin: "0 0 8px", color: "#4a5568", fontSize: 14 }}>Suggested Strategies</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {analysis.suggested_strategies.map((st, i) => (
                <div key={i} style={{ background: "#f7fafc", padding: 12, borderRadius: 8, borderLeft: `3px solid ${st.priority === "high" ? "#e53e3e" : st.priority === "medium" ? "#d97706" : "#718096"}` }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#2d3748", textTransform: "capitalize" }}>
                    {st.type.replace(/_/g, " ")}
                    <span style={{ marginLeft: 8, fontSize: 10, color: "#fff", background: st.priority === "high" ? "#e53e3e" : st.priority === "medium" ? "#d97706" : "#718096", padding: "1px 6px", borderRadius: 8 }}>{st.priority}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>{st.rationale}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create funding request */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <h3 style={{ margin: 0, color: "#2d3748", fontSize: 16 }}>Funding Requests</h3>
        <button onClick={() => setShowForm(!showForm)} style={s.btnPrimary}>{showForm ? "Cancel" : "+ New Request"}</button>
      </div>

      {showForm && engines.length > 0 && (
        <form onSubmit={handleCreate} style={s.card}>
          <div style={s.grid}>
            <div><label style={s.label}>Engine *</label><select value={form.engine_id} onChange={(e) => setForm({ ...form, engine_id: Number(e.target.value) })} required style={s.input}><option value={0}>Select engine</option>{engines.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}</select></div>
            <div><label style={s.label}>Funding Type *</label><select value={form.funding_type} onChange={(e) => setForm({ ...form, funding_type: e.target.value })} style={s.input}>{FUNDING_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></div>
            <div><label style={s.label}>Amount Requested *</label><input type="number" min={1} value={form.amount_requested || ""} onChange={(e) => setForm({ ...form, amount_requested: Number(e.target.value) })} required style={s.input} /></div>
          </div>
          <div style={{ marginTop: 8 }}><label style={s.label}>Title *</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required style={s.input} /></div>
          <div style={{ marginTop: 8 }}><label style={s.label}>Description *</label><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required rows={3} style={{ ...s.input, resize: "vertical" }} /></div>
          <div style={s.grid}>
            <div><label style={s.label}>Justification</label><input value={form.justification} onChange={(e) => setForm({ ...form, justification: e.target.value })} style={s.input} /></div>
            <div><label style={s.label}>Projected ROI (%)</label><input type="number" value={form.projected_roi} onChange={(e) => setForm({ ...form, projected_roi: e.target.value })} style={s.input} /></div>
            <div><label style={s.label}>Operational Cost</label><input type="number" value={form.operational_cost} onChange={(e) => setForm({ ...form, operational_cost: e.target.value })} style={s.input} /></div>
          </div>
          <button type="submit" disabled={saving} style={{ ...s.btnPrimary, marginTop: 12 }}>{saving ? "Creating..." : "Submit Request"}</button>
        </form>
      )}

      {/* Request list */}
      {loading ? <p style={{ color: "#718096" }}>Loading...</p> : requests.length === 0 ? (
        <div style={{ ...s.card, textAlign: "center", padding: 48 }}><p style={{ color: "#718096", margin: 0 }}>No funding requests yet.</p></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {requests.map((req) => {
            const engine = engines.find((e) => e.id === req.engine_id);
            const progress = req.amount_requested > 0 ? Math.min(100, (req.amount_secured / req.amount_requested) * 100) : 0;
            const color = STATUS_COLORS[req.status] || "#718096";
            return (
              <div key={req.id} style={{ ...s.card, borderLeft: `4px solid ${color}`, marginBottom: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, color: "#2d3748", fontSize: 15 }}>{req.title}</div>
                    <div style={{ fontSize: 12, color: "#718096" }}>{engine?.name || `Engine #${req.engine_id}`} &middot; {req.funding_type.replace(/_/g, " ")} &middot; {new Date(req.created_at).toLocaleDateString()}</div>
                  </div>
                  <span style={s.badge(color)}>{req.status.replace("_", " ")}</span>
                </div>
                <p style={{ margin: "0 0 12px", fontSize: 13, color: "#4a5568" }}>{req.description}</p>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#718096", marginBottom: 4 }}><span>Secured: ${req.amount_secured.toLocaleString()}</span><span>Goal: ${req.amount_requested.toLocaleString()}</span></div>
                  <div style={{ background: "#e2e8f0", borderRadius: 4, height: 8, overflow: "hidden" }}><div style={{ background: progress >= 100 ? "#2f855a" : "#3182ce", height: "100%", width: `${progress}%`, borderRadius: 4, transition: "width 0.3s ease" }} /></div>
                </div>
                <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#718096", flexWrap: "wrap" }}>
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
