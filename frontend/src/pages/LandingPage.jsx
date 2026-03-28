import { useNavigate } from "react-router-dom";

const hero = {
  minHeight: "100vh",
  background: "linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #4a5568 100%)",
  color: "#fff",
  fontFamily: "system-ui, sans-serif",
};

const container = { maxWidth: 1100, margin: "0 auto", padding: "0 24px" };

const nav = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "20px 0",
};

const btnPrimary = {
  background: "#3182ce",
  color: "#fff",
  border: "none",
  padding: "12px 32px",
  borderRadius: 8,
  cursor: "pointer",
  fontWeight: 700,
  fontSize: 16,
};

const btnOutline = {
  background: "transparent",
  color: "#fff",
  border: "2px solid #fff",
  padding: "10px 28px",
  borderRadius: 8,
  cursor: "pointer",
  fontWeight: 600,
  fontSize: 14,
};

const featureCard = {
  background: "rgba(255,255,255,0.08)",
  borderRadius: 12,
  padding: "28px 24px",
  border: "1px solid rgba(255,255,255,0.1)",
};

const features = [
  {
    icon: "🤖",
    title: "AI Agent with Real Tools",
    desc: "Claude-powered agent that reads files, runs commands, searches code, and manages git — all from a web chat interface.",
  },
  {
    icon: "🔒",
    title: "Approval Workflows",
    desc: "Destructive actions require human approval before execution. Built-in safety guardrails for enterprise use.",
  },
  {
    icon: "📊",
    title: "Analytics Dashboard",
    desc: "Track messages, tool usage, model performance, and costs with real-time charts and audit logs.",
  },
  {
    icon: "🏪",
    title: "Agent Marketplace",
    desc: "Create, share, and use custom agent configurations for different niches — real estate, SaaS sales, fundraising.",
  },
  {
    icon: "🎨",
    title: "White-Label Ready",
    desc: "Fully customizable branding, colors, sidebar, and CSS. Resell as your own platform to consulting firms.",
  },
  {
    icon: "⚡",
    title: "Multi-Model Support",
    desc: "Switch between Anthropic Claude, OpenAI GPT-4, and Google Gemini. Reduce single-vendor lock-in.",
  },
];

const stats = [
  { num: "8", label: "Built-in Tools" },
  { num: "3", label: "AI Models" },
  { num: "$29", label: "/mo Pro Plan" },
  { num: "50", label: "Free Messages" },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={hero}>
      {/* Nav */}
      <div style={container}>
        <div style={nav}>
          <div style={{ fontWeight: 800, fontSize: 22, letterSpacing: -0.5 }}>
            NorthStar
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={() => navigate("/pricing")} style={btnOutline}>
              Pricing
            </button>
            <button onClick={() => navigate("/login")} style={btnPrimary}>
              Get Started
            </button>
          </div>
        </div>
      </div>

      {/* Hero */}
      <div style={{ ...container, textAlign: "center", paddingTop: 80, paddingBottom: 60 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#63b3ed", textTransform: "uppercase", letterSpacing: 2, marginBottom: 16 }}>
          AI-Powered Consulting Platform
        </div>
        <h1 style={{ fontSize: 52, fontWeight: 800, margin: "0 0 20px", lineHeight: 1.15, maxWidth: 700, marginLeft: "auto", marginRight: "auto" }}>
          Your AI Agent That Actually Does the Work
        </h1>
        <p style={{ fontSize: 19, color: "#cbd5e0", maxWidth: 600, margin: "0 auto 40px", lineHeight: 1.6 }}>
          NorthStar combines AI consulting engines, lead generation, outreach automation, and a real coding agent — all in one platform.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <button onClick={() => navigate("/login")} style={{ ...btnPrimary, padding: "16px 48px", fontSize: 18 }}>
            Start Free
          </button>
          <button onClick={() => navigate("/pricing")} style={{ ...btnOutline, padding: "14px 40px" }}>
            View Pricing
          </button>
        </div>
      </div>

      {/* Stats */}
      <div style={{ ...container, paddingBottom: 60 }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 48, flexWrap: "wrap" }}>
          {stats.map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 36, fontWeight: 800, color: "#63b3ed" }}>{s.num}</div>
              <div style={{ fontSize: 13, color: "#a0aec0", marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div style={{ ...container, paddingBottom: 80 }}>
        <h2 style={{ textAlign: "center", fontSize: 32, fontWeight: 700, marginBottom: 40 }}>
          Everything You Need to Run an AI-Powered Business
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
          {features.map((f) => (
            <div key={f.title} style={featureCard}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px" }}>{f.title}</h3>
              <p style={{ fontSize: 14, color: "#a0aec0", lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{ background: "rgba(49,130,206,0.15)", padding: "60px 24px", textAlign: "center" }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, margin: "0 0 16px" }}>Ready to Get Started?</h2>
        <p style={{ fontSize: 16, color: "#cbd5e0", margin: "0 0 32px" }}>
          Start with 50 free messages per month. Upgrade anytime.
        </p>
        <button onClick={() => navigate("/login")} style={{ ...btnPrimary, padding: "16px 56px", fontSize: 18 }}>
          Create Free Account
        </button>
      </div>

      {/* Footer */}
      <div style={{ ...container, padding: "32px 24px", textAlign: "center", fontSize: 13, color: "#718096" }}>
        NorthStar Platform &copy; {new Date().getFullYear()} &mdash; AI-Powered Consulting
      </div>
    </div>
  );
}
