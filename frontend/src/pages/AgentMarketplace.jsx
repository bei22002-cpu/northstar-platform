import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const cardStyle = { background: "#fff", borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", padding: "20px 24px" };
const btnPrimary = { background: "#3182ce", color: "#fff", border: "none", padding: "8px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 13 };
const btnSecondary = { background: "transparent", border: "1px solid #e2e8f0", color: "#718096", padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 500 };
const inputStyle = { width: "100%", padding: "10px 14px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" };
const textareaStyle = { ...inputStyle, minHeight: 80, resize: "vertical", fontFamily: "inherit" };
const selectStyle = { padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 13, background: "#fff", outline: "none" };
const CATEGORIES = ["general", "coding", "writing", "research", "devops", "data", "other"];

export default function AgentMarketplace() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filterCat, setFilterCat] = useState("");
  const [form, setForm] = useState({ name: "", description: "", system_prompt: "", model_provider: "anthropic", model_name: "", tools_enabled: [], category: "general", is_public: true });

  const loadConfigs = () => {
    api.getMarketplaceConfigs(filterCat || undefined).then((data) => { setConfigs(Array.isArray(data) ? data : data?.configs || []); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { loadConfigs(); }, [filterCat]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.createMarketplaceConfig(form);
      setShowCreate(false);
      setForm({ name: "", description: "", system_prompt: "", model_provider: "anthropic", model_name: "", tools_enabled: [], category: "general", is_public: true });
      loadConfigs();
    } catch (err) { alert(err.message || "Error creating config"); }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this agent config?")) return;
    try { await api.deleteMarketplaceConfig(id); loadConfigs(); } catch (err) { alert(err.message); }
  };

  if (loading) return <div style={{ padding: 32, textAlign: "center", color: "#718096" }}>Loading marketplace...</div>;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, color: "#2d3748", fontSize: 22 }}>Agent Marketplace</h2>
          <p style={{ margin: "4px 0 0", color: "#718096", fontSize: 13 }}>Browse and create custom agent configurations</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} style={btnPrimary}>{showCreate ? "Cancel" : "Create Agent"}</button>
      </div>

      {/* Create form */}
      {showCreate && (
        <form onSubmit={handleCreate} style={{ ...cardStyle, marginBottom: 24 }}>
          <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Create Custom Agent</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 }}>Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Custom Agent" required style={inputStyle} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 }}>Description</label>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What does this agent do?" style={inputStyle} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 }}>System Prompt</label>
              <textarea value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} placeholder="You are a helpful assistant specialized in..." required style={textareaStyle} />
            </div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 }}>Provider</label>
                <select value={form.model_provider} onChange={(e) => setForm({ ...form, model_provider: e.target.value })} style={{ ...selectStyle, width: "100%" }}>
                  <option value="anthropic">Anthropic</option>
                  <option value="openai">OpenAI</option>
                  <option value="google">Google</option>
                </select>
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 }}>Category</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} style={{ ...selectStyle, width: "100%" }}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#718096", cursor: "pointer" }}>
                  <input type="checkbox" checked={form.is_public} onChange={(e) => setForm({ ...form, is_public: e.target.checked })} /> Public
                </label>
              </div>
            </div>
            <button type="submit" style={btnPrimary}>Create Agent Config</button>
          </div>
        </form>
      )}

      {/* Filter */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        <button onClick={() => setFilterCat("")} style={filterCat === "" ? { ...btnPrimary, padding: "6px 14px", fontSize: 12 } : { ...btnSecondary, padding: "6px 14px", fontSize: 12 }}>All</button>
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => setFilterCat(c)} style={filterCat === c ? { ...btnPrimary, padding: "6px 14px", fontSize: 12 } : { ...btnSecondary, padding: "6px 14px", fontSize: 12 }}>
            {c.charAt(0).toUpperCase() + c.slice(1)}
          </button>
        ))}
      </div>

      {/* Agent cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {configs.map((config) => (
          <div key={config.id} style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <div style={{ fontSize: 28 }}>{config.icon || "🤖"}</div>
              <span style={{ background: "#ebf4ff", color: "#3182ce", padding: "2px 8px", borderRadius: 8, fontSize: 10, fontWeight: 600 }}>{config.category || "general"}</span>
            </div>
            <h3 style={{ margin: "0 0 4px", color: "#2d3748", fontSize: 16 }}>{config.name}</h3>
            <p style={{ margin: "0 0 8px", color: "#718096", fontSize: 12, lineHeight: 1.5 }}>{config.description || "No description"}</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              <span style={{ background: "#f7fafc", color: "#4a5568", padding: "2px 8px", borderRadius: 6, fontSize: 10, fontWeight: 600 }}>{config.model_provider}</span>
              {config.model_name && <span style={{ background: "#f7fafc", color: "#4a5568", padding: "2px 8px", borderRadius: 6, fontSize: 10 }}>{config.model_name}</span>}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #edf2f7", paddingTop: 8 }}>
              <span style={{ fontSize: 11, color: "#a0aec0" }}>{config.use_count || 0} uses</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => { window.location.href = "/agent"; }} style={{ ...btnPrimary, padding: "4px 12px", fontSize: 11 }}>Use</button>
                <button onClick={() => handleDelete(config.id)} style={{ ...btnSecondary, padding: "4px 12px", fontSize: 11, color: "#e53e3e", borderColor: "#fed7d7" }}>Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {configs.length === 0 && (
        <div style={{ ...cardStyle, textAlign: "center", padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>🤖</div>
          <h3 style={{ margin: "0 0 8px", color: "#2d3748" }}>No Agent Configs Yet</h3>
          <p style={{ margin: "0 0 16px", color: "#718096", fontSize: 14 }}>Create your first custom agent configuration to get started.</p>
          <button onClick={() => setShowCreate(true)} style={btnPrimary}>Create Agent</button>
        </div>
      )}
    </div>
  );
}
