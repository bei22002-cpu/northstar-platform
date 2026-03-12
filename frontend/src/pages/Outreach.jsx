import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import OutreachForm from "../components/OutreachForm.jsx";
import MessageOutput from "../components/MessageOutput.jsx";

const styles = {
  page: { maxWidth: 860, margin: "0 auto", padding: "2rem 1rem" },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "2rem",
  },
  heading: { fontSize: "1.7rem", fontWeight: 700 },
  signout: {
    background: "none",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: "0.4rem 0.9rem",
    cursor: "pointer",
    fontSize: "0.9rem",
    color: "#64748b",
  },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" },
  errorBanner: {
    background: "#fee2e2",
    color: "#b91c1c",
    borderRadius: 8,
    padding: "0.6rem 1rem",
    marginBottom: "1rem",
    fontSize: "0.9rem",
  },
};

export default function Outreach({ onLogout }) {
  const [leads, setLeads] = useState([]);
  const [leadsError, setLeadsError] = useState("");

  // Generated content
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [followups, setFollowups] = useState(null); // { followup_1, followup_2, followup_3 }
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");

  useEffect(() => {
    api
      .listLeads()
      .then(setLeads)
      .catch((err) => setLeadsError(err.message));
  }, []);

  async function handleGenerate({ leadId, tone, serviceFocus, extraContext }) {
    setGenError("");
    setGenerating(true);
    setSubject("");
    setMessage("");
    setFollowups(null);
    try {
      const [msgResult, fuResult] = await Promise.all([
        api.generateMessage(leadId, tone, serviceFocus, extraContext),
        api.generateFollowups(leadId, tone, serviceFocus),
      ]);
      setSubject(msgResult.subject);
      setMessage(msgResult.message);
      setFollowups(fuResult);
    } catch (err) {
      setGenError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    onLogout();
  }

  const hasOutput = subject || message || followups;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.heading}>✉️ Outreach Engine</h1>
        <button style={styles.signout} onClick={handleLogout}>
          Sign out
        </button>
      </div>

      {leadsError && (
        <div style={styles.errorBanner}>Failed to load leads: {leadsError}</div>
      )}
      {genError && (
        <div style={styles.errorBanner}>Generation error: {genError}</div>
      )}

      <div style={styles.grid}>
        <OutreachForm leads={leads} onGenerate={handleGenerate} generating={generating} />

        {hasOutput && (
          <MessageOutput
            subject={subject}
            message={message}
            followups={followups}
          />
        )}
      </div>

      {!hasOutput && !generating && (
        <p style={{ color: "#94a3b8", marginTop: "2rem", textAlign: "center" }}>
          Select a lead, choose tone &amp; focus, then click Generate.
        </p>
      )}
    </div>
  );
}
