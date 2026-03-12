import { useState } from "react";

const s = {
  card: {
    background: "#fff",
    borderRadius: 12,
    boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
    padding: "1.5rem",
  },
  heading: { fontWeight: 700, fontSize: "1.1rem", marginBottom: "1.25rem" },
  label: { display: "block", fontWeight: 500, marginBottom: 4, fontSize: "0.88rem", color: "#475569" },
  select: {
    width: "100%",
    padding: "0.55rem 0.7rem",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: "0.9rem",
    marginBottom: "1rem",
    background: "#fff",
    outline: "none",
  },
  textarea: {
    width: "100%",
    padding: "0.55rem 0.7rem",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: "0.9rem",
    marginBottom: "1rem",
    resize: "vertical",
    minHeight: 72,
    outline: "none",
    fontFamily: "inherit",
  },
  btn: {
    width: "100%",
    padding: "0.7rem",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontWeight: 600,
    fontSize: "0.95rem",
    cursor: "pointer",
  },
  btnDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
  },
  note: { fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.75rem" },
  newLeadSection: { marginTop: "1.25rem", borderTop: "1px solid #f1f5f9", paddingTop: "1.25rem" },
  newLeadHeading: { fontWeight: 600, fontSize: "0.9rem", color: "#64748b", marginBottom: "0.75rem" },
  input: {
    width: "100%",
    padding: "0.5rem 0.7rem",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: "0.88rem",
    marginBottom: "0.6rem",
    outline: "none",
  },
  addBtn: {
    width: "100%",
    padding: "0.5rem",
    background: "#f1f5f9",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontWeight: 500,
    fontSize: "0.88rem",
    cursor: "pointer",
    color: "#1e293b",
  },
};

export default function OutreachForm({ leads, onGenerate, generating }) {
  const [leadId, setLeadId] = useState("");
  const [tone, setTone] = useState("professional");
  const [serviceFocus, setServiceFocus] = useState("operations");
  const [extraContext, setExtraContext] = useState("");

  // Inline new-lead form
  const [showNewLead, setShowNewLead] = useState(false);
  const [newCompany, setNewCompany] = useState("");
  const [newIndustry, setNewIndustry] = useState("");
  const [addingLead, setAddingLead] = useState(false); // eslint-disable-line no-unused-vars

  function handleSubmit(e) {
    e.preventDefault();
    if (!leadId) return;
    onGenerate({ leadId: Number(leadId), tone, serviceFocus, extraContext });
  }

  const disabled = generating || !leadId;

  return (
    <div style={s.card}>
      <h2 style={s.heading}>Generate Outreach</h2>

      <form onSubmit={handleSubmit}>
        <label style={s.label}>Lead</label>
        <select style={s.select} value={leadId} onChange={(e) => setLeadId(e.target.value)} required>
          <option value="">— select a lead —</option>
          {leads.map((l) => (
            <option key={l.id} value={l.id}>
              {l.company_name}{l.industry ? ` (${l.industry})` : ""}
            </option>
          ))}
        </select>

        <label style={s.label}>Tone</label>
        <select style={s.select} value={tone} onChange={(e) => setTone(e.target.value)}>
          <option value="professional">Professional</option>
          <option value="executive">Executive</option>
          <option value="casual">Casual</option>
        </select>

        <label style={s.label}>Service Focus</label>
        <select style={s.select} value={serviceFocus} onChange={(e) => setServiceFocus(e.target.value)}>
          <option value="operations">Operations</option>
          <option value="strategy">Strategy</option>
          <option value="scaling">Scaling</option>
        </select>

        <label style={s.label}>Extra context (optional)</label>
        <textarea
          style={s.textarea}
          value={extraContext}
          onChange={(e) => setExtraContext(e.target.value)}
          placeholder="e.g. They just raised a Series A, focus on cost reduction"
        />

        <button
          type="submit"
          style={{ ...s.btn, ...(disabled ? s.btnDisabled : {}) }}
          disabled={disabled}
        >
          {generating ? "Generating…" : "Generate message & follow-ups"}
        </button>
        <p style={s.note}>Content is generated only — no email is sent.</p>
      </form>

      {/* Quick add-lead panel */}
      <div style={s.newLeadSection}>
        <button style={s.addBtn} onClick={() => setShowNewLead((v) => !v)}>
          {showNewLead ? "▲ Hide" : "＋ Add a new lead"}
        </button>
        {showNewLead && (
          <AddLeadInline
            onAdded={(lead) => {
              leads.push(lead);
              setLeadId(String(lead.id));
              setShowNewLead(false);
            }}
          />
        )}
      </div>
    </div>
  );
}

function AddLeadInline({ onAdded }) {
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  async function handleAdd(e) {
    e.preventDefault();
    if (!companyName) return;
    setSaving(true);
    setErr("");
    try {
      // Dynamic import to keep this component self-contained
      const { api } = await import("../lib/api.js");
      const lead = await api.createLead({ company_name: companyName, industry, website });
      onAdded(lead);
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleAdd} style={{ marginTop: "0.75rem" }}>
      {err && (
        <p style={{ color: "#b91c1c", fontSize: "0.85rem", marginBottom: "0.5rem" }}>{err}</p>
      )}
      <input
        style={s.input}
        placeholder="Company name *"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
        required
      />
      <input
        style={s.input}
        placeholder="Industry"
        value={industry}
        onChange={(e) => setIndustry(e.target.value)}
      />
      <input
        style={s.input}
        placeholder="Website"
        value={website}
        onChange={(e) => setWebsite(e.target.value)}
      />
      <button
        type="submit"
        style={{ ...s.btn, marginTop: "0.25rem" }}
        disabled={saving}
      >
        {saving ? "Saving…" : "Add lead"}
      </button>
    </form>
  );
}
