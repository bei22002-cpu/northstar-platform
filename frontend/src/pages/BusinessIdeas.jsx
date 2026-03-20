import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const INDUSTRIES = [
  { value: "technology", label: "Technology & Software" },
  { value: "retail", label: "Retail & E-Commerce" },
  { value: "services", label: "Professional Services" },
  { value: "healthcare", label: "Healthcare & Biotech" },
  { value: "finance", label: "Finance & Fintech" },
  { value: "education", label: "Education & EdTech" },
  { value: "food", label: "Food & Beverage" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "real_estate", label: "Real Estate & PropTech" },
  { value: "media", label: "Media & Entertainment" },
  { value: "sustainability", label: "Sustainability & CleanTech" },
  { value: "other", label: "Other" },
];

const BUDGET_RANGES = [
  { value: "0-10k", label: "$0 - $10,000" },
  { value: "10k-50k", label: "$10,000 - $50,000" },
  { value: "50k-200k", label: "$50,000 - $200,000" },
  { value: "200k-1m", label: "$200,000 - $1M" },
  { value: "1m+", label: "$1M+" },
];

const s = {
  page: { padding: "16px 16px 32px", maxWidth: 960, margin: "0 auto" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 },
  title: { margin: 0, color: "#2d3748", fontSize: 22 },
  card: { background: "#fff", padding: 20, borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", marginBottom: 16 },
  input: { padding: "10px 14px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14, width: "100%", boxSizing: "border-box" },
  label: { fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 },
  btnPrimary: { background: "#3182ce", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 14 },
  btnSecondary: { background: "#718096", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 14 },
  btnDanger: { background: "transparent", border: "none", color: "#e53e3e", cursor: "pointer", fontSize: 14, padding: "10px 12px" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 },
  badge: (color) => ({ background: color, color: "#fff", padding: "2px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600, textTransform: "uppercase", whiteSpace: "nowrap" }),
};

const STATUS_COLORS = { submitted: "#718096", analyzing: "#d97706", strategies_generated: "#2f855a", in_progress: "#3182ce", completed: "#6b46c1" };

export default function BusinessIdeas() {
  const [ideas, setIdeas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [form, setForm] = useState({ title: "", description: "", industry: "technology", target_market: "", budget_range: "" });

  const fetchIdeas = async () => {
    setLoading(true);
    try { setIdeas(await api.getBusinessIdeas()); } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchIdeas(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.submitBusinessIdea(form, 1);
      setForm({ title: "", description: "", industry: "technology", target_market: "", budget_range: "" });
      setShowForm(false);
      await fetchIdeas();
    } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this business idea?")) return;
    await api.deleteBusinessIdea(id);
    await fetchIdeas();
  };

  const parseJson = (str) => {
    if (!str) return null;
    try { return JSON.parse(str); } catch { return null; }
  };

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>Business Ideas</h2>
        <button onClick={() => setShowForm(!showForm)} style={s.btnPrimary}>
          {showForm ? "Cancel" : "+ Submit Idea"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={s.card}>
          <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Submit Your Business Idea</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input placeholder="Business idea title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required style={s.input} />
            <textarea placeholder="Describe your business idea in detail... *" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required rows={4} style={{ ...s.input, resize: "vertical" }} />
            <div style={s.grid}>
              <div>
                <label style={s.label}>Industry *</label>
                <select value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} style={s.input}>
                  {INDUSTRIES.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
                </select>
              </div>
              <div>
                <label style={s.label}>Target Market</label>
                <input placeholder="e.g., Small businesses" value={form.target_market} onChange={(e) => setForm({ ...form, target_market: e.target.value })} style={s.input} />
              </div>
              <div>
                <label style={s.label}>Budget Range</label>
                <select value={form.budget_range} onChange={(e) => setForm({ ...form, budget_range: e.target.value })} style={s.input}>
                  <option value="">Select range</option>
                  {BUDGET_RANGES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
                </select>
              </div>
            </div>
            <button type="submit" disabled={saving} style={s.btnPrimary}>{saving ? "Submitting..." : "Submit for AI Analysis"}</button>
          </div>
        </form>
      )}

      {loading ? (
        <p style={{ color: "#718096" }}>Loading ideas...</p>
      ) : ideas.length === 0 ? (
        <div style={{ ...s.card, textAlign: "center", padding: 48 }}>
          <p style={{ color: "#718096", fontSize: 16, margin: 0 }}>No business ideas yet. Submit your first idea above to get AI-powered analysis!</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {ideas.map((idea) => {
            const analysis = parseJson(idea.ai_analysis);
            const funding = parseJson(idea.funding_strategy);
            const isExpanded = expandedId === idea.id;
            const color = STATUS_COLORS[idea.status] || "#718096";

            return (
              <div key={idea.id} style={{ ...s.card, borderLeft: `4px solid ${color}`, marginBottom: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <h3 style={{ margin: "0 0 4px", color: "#2d3748", fontSize: 16 }}>{idea.title}</h3>
                    <div style={{ fontSize: 12, color: "#718096" }}>
                      {INDUSTRIES.find((i) => i.value === idea.industry)?.label || idea.industry}
                      {idea.target_market && <> &middot; {idea.target_market}</>}
                      {idea.budget_range && <> &middot; Budget: {idea.budget_range}</>}
                      &nbsp;&middot;&nbsp;{new Date(idea.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={s.badge(color)}>{idea.status.replace("_", " ")}</span>
                </div>
                <p style={{ color: "#4a5568", fontSize: 14, margin: "12px 0 8px" }}>{idea.description}</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button onClick={() => setExpandedId(isExpanded ? null : idea.id)} style={s.btnSecondary}>
                    {isExpanded ? "Hide Analysis" : "View AI Analysis"}
                  </button>
                  <button onClick={() => handleDelete(idea.id)} style={s.btnDanger}>Delete</button>
                </div>
                {isExpanded && analysis && (
                  <div style={{ marginTop: 16, background: "#f7fafc", borderRadius: 8, padding: 16 }}>
                    <h4 style={{ margin: "0 0 12px", color: "#2d3748" }}>AI Analysis</h4>
                    {analysis.industry_analysis && (
                      <div style={{ marginBottom: 12 }}>
                        <strong style={{ color: "#4a5568", fontSize: 13 }}>Industry Analysis:</strong>
                        <div style={{ fontSize: 13, color: "#718096", marginTop: 4 }}>
                          {Object.entries(analysis.industry_analysis).map(([k, v]) => (
                            <div key={k} style={{ marginBottom: 2 }}><strong>{k.replace(/_/g, " ")}:</strong> {Array.isArray(v) ? v.join(", ") : String(v)}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    {analysis.recommended_next_steps && (
                      <div style={{ marginBottom: 12 }}>
                        <strong style={{ color: "#4a5568", fontSize: 13 }}>Next Steps:</strong>
                        <ul style={{ margin: "4px 0", paddingLeft: 20, fontSize: 13, color: "#718096" }}>
                          {analysis.recommended_next_steps.map((step, i) => <li key={i}>{step}</li>)}
                        </ul>
                      </div>
                    )}
                    {funding && funding.recommended_strategies && (
                      <div>
                        <strong style={{ color: "#4a5568", fontSize: 13 }}>Funding Strategy:</strong>
                        <div style={{ fontSize: 13, color: "#718096", marginTop: 4 }}>
                          {funding.recommended_strategies.map((st, i) => (
                            <div key={i} style={{ background: "#fff", padding: 8, borderRadius: 6, marginBottom: 4, border: "1px solid #e2e8f0" }}>
                              <strong>{st.type.replace(/_/g, " ").toUpperCase()}</strong>: {st.description}<br /><em>Typical: {st.typical_amount}</em>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
