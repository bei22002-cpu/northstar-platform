import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const SPECIALIZATIONS = [
  { value: "funding", label: "Funding Specialist" },
  { value: "market_research", label: "Market Research" },
  { value: "strategy", label: "Business Strategy" },
  { value: "outreach", label: "Outreach & Sales" },
  { value: "analytics", label: "Analytics & Insights" },
  { value: "operations", label: "Operations" },
];

const MESSAGE_TYPES = [
  { value: "funding_request", label: "Funding Request" },
  { value: "strategy_share", label: "Strategy Share" },
  { value: "insight_broadcast", label: "Insight Broadcast" },
  { value: "collaboration_proposal", label: "Collaboration Proposal" },
  { value: "status_update", label: "Status Update" },
  { value: "task_assignment", label: "Task Assignment" },
];

const STATUS_COLORS = { active: "#2f855a", idle: "#718096", researching: "#d97706", funding: "#3182ce", error: "#e53e3e" };
const MSG_COLORS = { funding_request: "#e53e3e", strategy_share: "#3182ce", insight_broadcast: "#d97706", collaboration_proposal: "#6b46c1", status_update: "#718096", task_assignment: "#2f855a" };

const s = {
  page: { padding: "16px 16px 32px", maxWidth: 960, margin: "0 auto" },
  card: { background: "#fff", padding: 20, borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", marginBottom: 16 },
  input: { padding: "10px 14px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14, width: "100%", boxSizing: "border-box" },
  label: { fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 },
  btnPrimary: { background: "#3182ce", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 14 },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 },
  badge: (color) => ({ background: color, color: "#fff", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }),
  tab: (active) => ({ padding: "10px 20px", border: "none", background: "transparent", color: active ? "#3182ce" : "#718096", fontWeight: 600, fontSize: 14, cursor: "pointer", borderBottom: active ? "2px solid #3182ce" : "2px solid transparent", marginBottom: -2 }),
};

export default function AIEngines() {
  const [engines, setEngines] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showMessageForm, setShowMessageForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("engines");
  const [engineForm, setEngineForm] = useState({ name: "", specialization: "funding", token_balance: 1000, description: "" });
  const [msgForm, setMsgForm] = useState({ sender_engine_id: 0, receiver_engine_id: "", message_type: "status_update", subject: "", body: "" });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eng, msgs] = await Promise.all([api.getEngines(), api.getMessageHistory()]);
      setEngines(eng);
      setMessages(msgs);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreateEngine = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.createEngine(engineForm);
      setEngineForm({ name: "", specialization: "funding", token_balance: 1000, description: "" });
      setShowCreateForm(false);
      await fetchData();
    } finally { setSaving(false); }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...msgForm };
      if (!payload.receiver_engine_id) delete payload.receiver_engine_id;
      else payload.receiver_engine_id = Number(payload.receiver_engine_id);
      await api.sendEngineMessage(payload);
      setMsgForm({ sender_engine_id: engines[0]?.id || 0, receiver_engine_id: "", message_type: "status_update", subject: "", body: "" });
      setShowMessageForm(false);
      await fetchData();
    } finally { setSaving(false); }
  };

  return (
    <div style={s.page}>
      <h2 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 22 }}>AI Engines Dashboard</h2>

      <div style={{ display: "flex", gap: 0, marginBottom: 24, borderBottom: "2px solid #e2e8f0" }}>
        <button onClick={() => setActiveTab("engines")} style={s.tab(activeTab === "engines")}>Engines</button>
        <button onClick={() => setActiveTab("communication")} style={s.tab(activeTab === "communication")}>Communication</button>
      </div>

      {activeTab === "engines" && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
            <p style={{ margin: 0, color: "#718096", fontSize: 13 }}>{engines.length} engine(s) registered</p>
            <button onClick={() => setShowCreateForm(!showCreateForm)} style={s.btnPrimary}>{showCreateForm ? "Cancel" : "+ Register Engine"}</button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateEngine} style={s.card}>
              <h3 style={{ margin: "0 0 12px", color: "#2d3748", fontSize: 16 }}>Register New AI Engine</h3>
              <div style={s.grid}>
                <div>
                  <label style={s.label}>Engine Name *</label>
                  <input placeholder="e.g., FundBot Alpha" value={engineForm.name} onChange={(e) => setEngineForm({ ...engineForm, name: e.target.value })} required style={s.input} />
                </div>
                <div>
                  <label style={s.label}>Specialization *</label>
                  <select value={engineForm.specialization} onChange={(e) => setEngineForm({ ...engineForm, specialization: e.target.value })} style={s.input}>
                    {SPECIALIZATIONS.map((sp) => <option key={sp.value} value={sp.value}>{sp.label}</option>)}
                  </select>
                </div>
                <div>
                  <label style={s.label}>Initial Token Balance</label>
                  <input type="number" value={engineForm.token_balance} onChange={(e) => setEngineForm({ ...engineForm, token_balance: Number(e.target.value) })} style={s.input} />
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <label style={s.label}>Description</label>
                <input placeholder="Brief description" value={engineForm.description} onChange={(e) => setEngineForm({ ...engineForm, description: e.target.value })} style={s.input} />
              </div>
              <button type="submit" disabled={saving} style={{ ...s.btnPrimary, marginTop: 12 }}>{saving ? "Creating..." : "Register Engine"}</button>
            </form>
          )}

          {loading ? <p style={{ color: "#718096" }}>Loading engines...</p> : engines.length === 0 ? (
            <div style={{ ...s.card, textAlign: "center", padding: 48 }}><p style={{ color: "#718096", margin: 0 }}>No engines registered. Create your first AI engine above.</p></div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
              {engines.map((engine) => (
                <div key={engine.id} style={{ ...s.card, borderTop: `3px solid ${STATUS_COLORS[engine.status] || "#718096"}`, marginBottom: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <h4 style={{ margin: 0, color: "#2d3748", fontSize: 15 }}>{engine.name}</h4>
                    <span style={s.badge(STATUS_COLORS[engine.status] || "#718096")}>{engine.status}</span>
                  </div>
                  <p style={{ margin: "0 0 12px", fontSize: 13, color: "#718096" }}>{engine.description || "No description"}</p>
                  <div style={{ fontSize: 13, color: "#4a5568" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}><span>Specialization:</span><strong>{engine.specialization.replace("_", " ")}</strong></div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}><span>Token Balance:</span><strong style={{ color: engine.token_balance > 100 ? "#2f855a" : "#e53e3e" }}>{engine.token_balance.toLocaleString()}</strong></div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}><span>Tokens Used:</span><span>{engine.tokens_consumed.toLocaleString()}</span></div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}><span>Active:</span><span>{engine.is_active ? "Yes" : "No"}</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === "communication" && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
            <p style={{ margin: 0, color: "#718096", fontSize: 13 }}>{messages.length} message(s) in history</p>
            <button onClick={() => setShowMessageForm(!showMessageForm)} style={s.btnPrimary}>{showMessageForm ? "Cancel" : "+ Send Message"}</button>
          </div>

          {showMessageForm && engines.length > 0 && (
            <form onSubmit={handleSendMessage} style={s.card}>
              <h3 style={{ margin: "0 0 12px", color: "#2d3748", fontSize: 16 }}>Send Engine Message</h3>
              <div style={s.grid}>
                <div>
                  <label style={s.label}>From Engine *</label>
                  <select value={msgForm.sender_engine_id} onChange={(e) => setMsgForm({ ...msgForm, sender_engine_id: Number(e.target.value) })} required style={s.input}>
                    <option value={0}>Select sender</option>
                    {engines.map((eng) => <option key={eng.id} value={eng.id}>{eng.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={s.label}>To Engine (empty = broadcast)</label>
                  <select value={msgForm.receiver_engine_id} onChange={(e) => setMsgForm({ ...msgForm, receiver_engine_id: e.target.value })} style={s.input}>
                    <option value="">Broadcast to all</option>
                    {engines.map((eng) => <option key={eng.id} value={eng.id}>{eng.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={s.label}>Type *</label>
                  <select value={msgForm.message_type} onChange={(e) => setMsgForm({ ...msgForm, message_type: e.target.value })} style={s.input}>
                    {MESSAGE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 8 }}><label style={s.label}>Subject *</label><input value={msgForm.subject} onChange={(e) => setMsgForm({ ...msgForm, subject: e.target.value })} required style={s.input} /></div>
              <div style={{ marginTop: 8 }}><label style={s.label}>Body *</label><textarea value={msgForm.body} onChange={(e) => setMsgForm({ ...msgForm, body: e.target.value })} required rows={3} style={{ ...s.input, resize: "vertical" }} /></div>
              <button type="submit" disabled={saving} style={{ ...s.btnPrimary, marginTop: 12 }}>{saving ? "Sending..." : "Send Message"}</button>
            </form>
          )}

          {loading ? <p style={{ color: "#718096" }}>Loading messages...</p> : messages.length === 0 ? (
            <div style={{ ...s.card, textAlign: "center", padding: 48 }}><p style={{ color: "#718096", margin: 0 }}>No messages yet. AI engines will communicate here about funding strategies and collaboration.</p></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.map((msg) => {
                const sender = engines.find((e) => e.id === msg.sender_engine_id);
                const receiver = msg.receiver_engine_id ? engines.find((e) => e.id === msg.receiver_engine_id) : null;
                const color = MSG_COLORS[msg.message_type] || "#718096";
                return (
                  <div key={msg.id} style={{ ...s.card, borderLeft: `3px solid ${color}`, marginBottom: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
                      <div style={{ fontSize: 13 }}>
                        <strong style={{ color: "#2d3748" }}>{sender?.name || `Engine #${msg.sender_engine_id}`}</strong>
                        <span style={{ color: "#718096" }}>{receiver ? ` \u2192 ${receiver.name}` : " \u2192 All Engines"}</span>
                      </div>
                      <span style={{ ...s.badge(color), padding: "1px 8px", borderRadius: 10, fontSize: 10 }}>{msg.message_type.replace("_", " ")}</span>
                    </div>
                    <div style={{ fontWeight: 600, color: "#2d3748", fontSize: 14, marginBottom: 4 }}>{msg.subject}</div>
                    <p style={{ margin: 0, fontSize: 13, color: "#4a5568", whiteSpace: "pre-wrap" }}>{msg.body}</p>
                    <div style={{ fontSize: 11, color: "#a0aec0", marginTop: 8 }}>{new Date(msg.created_at).toLocaleString()}</div>
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
