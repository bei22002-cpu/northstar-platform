import { useState } from "react";

const s = {
  card: {
    background: "#fff",
    borderRadius: 12,
    boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
    padding: "1.5rem",
    overflow: "hidden",
  },
  heading: { fontWeight: 700, fontSize: "1.1rem", marginBottom: "1.25rem" },
  sectionLabel: {
    fontWeight: 600,
    fontSize: "0.82rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "#64748b",
    marginBottom: "0.3rem",
  },
  valueBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: "0.65rem 0.8rem",
    fontSize: "0.9rem",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    marginBottom: "0.4rem",
    lineHeight: 1.6,
    color: "#1e293b",
  },
  copyBtn: {
    background: "none",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    padding: "0.3rem 0.65rem",
    fontSize: "0.8rem",
    cursor: "pointer",
    color: "#475569",
    marginBottom: "1rem",
  },
  copyBtnDone: {
    color: "#16a34a",
    borderColor: "#bbf7d0",
    background: "#f0fdf4",
  },
  divider: { borderTop: "1px solid #f1f5f9", margin: "0.75rem 0" },
  followupHeading: {
    fontWeight: 700,
    fontSize: "1rem",
    marginBottom: "1rem",
    marginTop: "0.5rem",
  },
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <button
      style={{ ...s.copyBtn, ...(copied ? s.copyBtnDone : {}) }}
      onClick={handleCopy}
      type="button"
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

function TextBlock({ label, value }) {
  return (
    <>
      <p style={s.sectionLabel}>{label}</p>
      <div style={s.valueBox}>{value}</div>
      <CopyButton text={value} />
    </>
  );
}

export default function MessageOutput({ subject, message, followups }) {
  return (
    <div style={s.card}>
      <h2 style={s.heading}>Generated Content</h2>

      {subject && <TextBlock label="Subject" value={subject} />}
      {message && <TextBlock label="Message" value={message} />}

      {followups && (
        <>
          <div style={s.divider} />
          <p style={s.followupHeading}>3-Step Follow-up Sequence</p>
          <TextBlock label="Follow-up 1 (3–5 days)" value={followups.followup_1} />
          <TextBlock label="Follow-up 2 (7–10 days)" value={followups.followup_2} />
          <TextBlock label="Follow-up 3 (14+ days)" value={followups.followup_3} />
        </>
      )}
    </div>
  );
}
