import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";

const page = {
  minHeight: "100vh",
  background: "linear-gradient(135deg, #1a202c 0%, #2d3748 100%)",
  color: "#fff",
  fontFamily: "system-ui, sans-serif",
  padding: "0 24px",
};

const container = { maxWidth: 1100, margin: "0 auto" };

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
  padding: "14px 32px",
  borderRadius: 8,
  cursor: "pointer",
  fontWeight: 700,
  fontSize: 15,
  width: "100%",
};

const btnOutline = {
  background: "transparent",
  color: "#fff",
  border: "2px solid rgba(255,255,255,0.3)",
  padding: "12px 28px",
  borderRadius: 8,
  cursor: "pointer",
  fontWeight: 600,
  fontSize: 14,
  width: "100%",
};

const btnEnterprise = {
  background: "transparent",
  color: "#805ad5",
  border: "2px solid #805ad5",
  padding: "12px 28px",
  borderRadius: 8,
  cursor: "pointer",
  fontWeight: 600,
  fontSize: 14,
  width: "100%",
};

const card = {
  background: "rgba(255,255,255,0.06)",
  borderRadius: 16,
  padding: "36px 28px",
  border: "1px solid rgba(255,255,255,0.1)",
  display: "flex",
  flexDirection: "column",
};

const proCard = {
  ...card,
  background: "rgba(49,130,206,0.12)",
  border: "2px solid #3182ce",
  position: "relative",
};

const check = { color: "#48bb78", marginRight: 8 };

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    desc: "Get started with AI consulting",
    features: [
      "50 messages per month",
      "1 AI model (Anthropic Claude)",
      "Basic agent tools",
      "Lead management",
      "Outreach generation",
    ],
    missing: [
      "Unlimited messages",
      "Multi-model support",
      "Analytics dashboard",
      "Agent marketplace",
      "White-label branding",
      "Priority support",
    ],
    cta: "Start Free",
    style: "outline",
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    desc: "For power users and consultants",
    popular: true,
    features: [
      "Unlimited messages",
      "All 3 AI models",
      "All 8 agent tools",
      "Approval workflows",
      "Analytics dashboard",
      "Agent marketplace access",
      "Streaming responses",
      "Audit logging",
      "Priority support",
    ],
    missing: [
      "White-label branding",
      "Custom agent configs",
      "Dedicated support",
    ],
    cta: "Upgrade to Pro",
    style: "primary",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    desc: "For teams and agencies",
    features: [
      "Everything in Pro",
      "White-label branding",
      "Custom agent configurations",
      "SSO / SAML integration",
      "Dedicated account manager",
      "Custom API limits",
      "SLA guarantee",
      "On-premise option",
    ],
    missing: [],
    cta: "Contact Sales",
    style: "enterprise",
  },
];

export default function PricingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleCheckout = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/login");
      return;
    }
    setLoading(true);
    try {
      const res = await api.createCheckoutSession();
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err) {
      alert(err.message || "Could not start checkout. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handlePlanClick = (plan) => {
    if (plan.name === "Free") {
      navigate("/login");
    } else if (plan.name === "Pro") {
      handleCheckout();
    } else {
      window.location.href = "mailto:sales@northstarplatform.com?subject=Enterprise%20Inquiry";
    }
  };

  const cancelled = new URLSearchParams(window.location.search).get("payment") === "cancelled";

  return (
    <div style={page}>
      <div style={container}>
        {/* Nav */}
        <div style={nav}>
          <div
            onClick={() => navigate("/")}
            style={{ fontWeight: 800, fontSize: 22, letterSpacing: -0.5, cursor: "pointer" }}
          >
            NorthStar
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <button
              onClick={() => navigate("/login")}
              style={{ background: "#3182ce", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 14 }}
            >
              Sign In
            </button>
          </div>
        </div>

        {/* Header */}
        <div style={{ textAlign: "center", paddingTop: 60, paddingBottom: 48 }}>
          <h1 style={{ fontSize: 44, fontWeight: 800, margin: "0 0 16px" }}>Simple, Transparent Pricing</h1>
          <p style={{ fontSize: 18, color: "#a0aec0", margin: 0 }}>
            Start free. Upgrade when you need more power.
          </p>
          {cancelled && (
            <div style={{ marginTop: 16, background: "rgba(237,137,54,0.15)", border: "1px solid #ed8936", borderRadius: 8, padding: "10px 20px", display: "inline-block", color: "#ed8936", fontSize: 14 }}>
              Payment was cancelled. No worries — you can try again anytime.
            </div>
          )}
        </div>

        {/* Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24, paddingBottom: 80 }}>
          {plans.map((plan) => (
            <div key={plan.name} style={plan.popular ? proCard : card}>
              {plan.popular && (
                <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", background: "#3182ce", color: "#fff", padding: "4px 16px", borderRadius: 12, fontSize: 12, fontWeight: 700 }}>
                  MOST POPULAR
                </div>
              )}
              <div style={{ fontSize: 13, fontWeight: 700, color: "#63b3ed", textTransform: "uppercase", letterSpacing: 1 }}>
                {plan.name}
              </div>
              <div style={{ marginTop: 12 }}>
                <span style={{ fontSize: 48, fontWeight: 800 }}>{plan.price}</span>
                <span style={{ fontSize: 16, color: "#a0aec0" }}>{plan.period}</span>
              </div>
              <p style={{ fontSize: 14, color: "#a0aec0", margin: "12px 0 24px" }}>{plan.desc}</p>

              <div style={{ flex: 1 }}>
                {plan.features.map((f) => (
                  <div key={f} style={{ fontSize: 14, padding: "6px 0", display: "flex", alignItems: "center" }}>
                    <span style={check}>&#10003;</span> {f}
                  </div>
                ))}
                {plan.missing.map((f) => (
                  <div key={f} style={{ fontSize: 14, padding: "6px 0", display: "flex", alignItems: "center", color: "#4a5568" }}>
                    <span style={{ color: "#4a5568", marginRight: 8 }}>&#10007;</span> {f}
                  </div>
                ))}
              </div>

              <button
                onClick={() => handlePlanClick(plan)}
                disabled={loading && plan.name === "Pro"}
                style={
                  plan.style === "primary"
                    ? { ...btnPrimary, marginTop: 24, opacity: loading ? 0.6 : 1 }
                    : plan.style === "enterprise"
                    ? { ...btnEnterprise, marginTop: 24 }
                    : { ...btnOutline, marginTop: 24 }
                }
              >
                {loading && plan.name === "Pro" ? "Redirecting..." : plan.cta}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div style={{ maxWidth: 700, margin: "0 auto", paddingBottom: 80 }}>
          <h2 style={{ textAlign: "center", fontSize: 28, fontWeight: 700, marginBottom: 32 }}>
            Frequently Asked Questions
          </h2>
          {[
            {
              q: "Can I cancel anytime?",
              a: "Yes. You can cancel your Pro subscription at any time from Settings. You'll keep access until the end of your billing period.",
            },
            {
              q: "What happens when I hit my free message limit?",
              a: "You'll see a notification asking you to upgrade. Your data and configurations are preserved.",
            },
            {
              q: "Do you offer annual billing?",
              a: "Not yet, but it's coming soon. Annual plans will offer a 20% discount.",
            },
            {
              q: "Can I white-label this for my agency?",
              a: "Yes! The Enterprise plan includes full white-label support — custom branding, colors, logo, and CSS.",
            },
          ].map((faq) => (
            <div key={faq.q} style={{ marginBottom: 24, background: "rgba(255,255,255,0.04)", borderRadius: 12, padding: "20px 24px" }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 8px" }}>{faq.q}</h3>
              <p style={{ fontSize: 14, color: "#a0aec0", margin: 0, lineHeight: 1.6 }}>{faq.a}</p>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", padding: "24px 0", fontSize: 13, color: "#718096", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          NorthStar Platform &copy; {new Date().getFullYear()}
        </div>
      </div>
    </div>
  );
}
