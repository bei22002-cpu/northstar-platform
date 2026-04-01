import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const cardStyle = { background: "#fff", borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", padding: "20px 24px" };
const inputStyle = { width: "100%", padding: "10px 14px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" };
const textareaStyle = { ...inputStyle, minHeight: 100, resize: "vertical", fontFamily: "monospace", fontSize: 12 };
const btnPrimary = { background: "#3182ce", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 14 };
const labelStyle = { fontSize: 12, color: "#718096", fontWeight: 600, display: "block", marginBottom: 4 };
const colorInput = { width: 48, height: 36, border: "1px solid #e2e8f0", borderRadius: 6, cursor: "pointer", padding: 2 };

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sub, setSub] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getPlatformSettings().catch(() => ({})),
      api.getSubscription().catch(() => null),
    ]).then(([s, subscription]) => {
      setSettings(s || {});
      setSub(subscription);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const res = await api.updatePlatformSettings(settings);
      setSettings(res);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) { alert(err.message || "Error saving settings"); }
    finally { setSaving(false); }
  };

  const handleUpgrade = async () => {
    try {
      const res = await api.createCheckoutSession();
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        // Fallback: direct upgrade if Stripe not configured
        const fallback = await api.upgradeSubscription();
        setSub(fallback);
        alert("Upgraded to Pro!");
      }
    } catch (err) {
      // If Stripe not configured (503), fall back to direct upgrade
      if (err.message && err.message.includes("not configured")) {
        try {
          const fallback = await api.upgradeSubscription();
          setSub(fallback);
          alert("Upgraded to Pro!");
        } catch (e2) { alert(e2.message || "Error upgrading"); }
      } else {
        alert(err.message || "Error upgrading");
      }
    }
  };

  const handleManageBilling = async () => {
    try {
      const res = await api.createPortalSession();
      if (res.portal_url) {
        window.location.href = res.portal_url;
      }
    } catch (err) { alert(err.message || "Could not open billing portal"); }
  };

  const update = (key, val) => setSettings({ ...settings, [key]: val });

  if (loading) return <div style={{ padding: 32, textAlign: "center", color: "#718096" }}>Loading settings...</div>;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h2 style={{ margin: "0 0 4px", color: "#2d3748", fontSize: 22 }}>Platform Settings</h2>
      <p style={{ margin: "0 0 20px", color: "#718096", fontSize: 13 }}>White-label customization and subscription management</p>

      {/* Subscription */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Subscription</h3>
        {sub ? (
          <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
            <div>
              <span style={{ background: sub.tier === "free" ? "#ebf4ff" : sub.tier === "pro" ? "#f0fff4" : "#faf5ff", color: sub.tier === "free" ? "#3182ce" : sub.tier === "pro" ? "#276749" : "#6b46c1", padding: "4px 14px", borderRadius: 12, fontSize: 13, fontWeight: 700, textTransform: "uppercase" }}>{sub.tier}</span>
            </div>
            <div style={{ fontSize: 13, color: "#4a5568" }}>
              <strong>{sub.messages_used}</strong> / {sub.messages_limit} messages used
            </div>
            <div style={{ width: 120, height: 8, background: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: Math.min(100, (sub.messages_used / sub.messages_limit) * 100) + "%", height: "100%", background: (sub.messages_used / sub.messages_limit) > 0.8 ? "#e53e3e" : "#48bb78", borderRadius: 4 }} />
            </div>
            {sub.tier === "free" && <button onClick={handleUpgrade} style={btnPrimary}>Upgrade to Pro ($29/mo)</button>}
            {sub.tier === "pro" && <button onClick={handleManageBilling} style={{ ...btnPrimary, background: "#805ad5" }}>Manage Billing</button>}
          </div>
        ) : <p style={{ color: "#a0aec0", fontSize: 13 }}>No subscription info available</p>}
      </div>

      {/* Branding */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Branding</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={labelStyle}>Platform Name</label>
            <input value={settings.platform_name || ""} onChange={(e) => update("platform_name", e.target.value)} placeholder="NorthStar Platform" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Tagline</label>
            <input value={settings.tagline || ""} onChange={(e) => update("tagline", e.target.value)} placeholder="AI-Powered Consulting Platform" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Logo URL</label>
            <input value={settings.logo_url || ""} onChange={(e) => update("logo_url", e.target.value)} placeholder="https://example.com/logo.png" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Support Email</label>
            <input value={settings.support_email || ""} onChange={(e) => update("support_email", e.target.value)} placeholder="support@yourplatform.com" style={inputStyle} />
          </div>
        </div>
      </div>

      {/* Colors */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Theme Colors</h3>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div>
            <label style={labelStyle}>Primary Color</label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="color" value={settings.primary_color || "#3182ce"} onChange={(e) => update("primary_color", e.target.value)} style={colorInput} />
              <input value={settings.primary_color || "#3182ce"} onChange={(e) => update("primary_color", e.target.value)} style={{ ...inputStyle, width: 100 }} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Accent Color</label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="color" value={settings.accent_color || "#805ad5"} onChange={(e) => update("accent_color", e.target.value)} style={colorInput} />
              <input value={settings.accent_color || "#805ad5"} onChange={(e) => update("accent_color", e.target.value)} style={{ ...inputStyle, width: 100 }} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Sidebar Background</label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="color" value={settings.sidebar_bg || "#1a202c"} onChange={(e) => update("sidebar_bg", e.target.value)} style={colorInput} />
              <input value={settings.sidebar_bg || "#1a202c"} onChange={(e) => update("sidebar_bg", e.target.value)} style={{ ...inputStyle, width: 100 }} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Sidebar Text</label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="color" value={settings.sidebar_text || "#e2e8f0"} onChange={(e) => update("sidebar_text", e.target.value)} style={colorInput} />
              <input value={settings.sidebar_text || "#e2e8f0"} onChange={(e) => update("sidebar_text", e.target.value)} style={{ ...inputStyle, width: 100 }} />
            </div>
          </div>
        </div>
      </div>

      {/* Custom CSS */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Custom CSS</h3>
        <textarea value={settings.custom_css || ""} onChange={(e) => update("custom_css", e.target.value)} placeholder="/* Add custom CSS overrides here */" style={textareaStyle} />
      </div>

      {/* Feature toggles */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Feature Toggles</h3>
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#4a5568", cursor: "pointer" }}>
            <input type="checkbox" checked={settings.enable_marketplace !== false} onChange={(e) => update("enable_marketplace", e.target.checked)} /> Enable Marketplace
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#4a5568", cursor: "pointer" }}>
            <input type="checkbox" checked={settings.enable_analytics !== false} onChange={(e) => update("enable_analytics", e.target.checked)} /> Enable Analytics
          </label>
        </div>
      </div>

      {/* Preview */}
      <div style={{ ...cardStyle, marginBottom: 24, background: settings.sidebar_bg || "#1a202c", color: settings.sidebar_text || "#e2e8f0" }}>
        <h3 style={{ margin: "0 0 12px", fontSize: 16, color: settings.sidebar_text || "#e2e8f0" }}>Sidebar Preview</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: settings.primary_color || "#3182ce" }}>{settings.platform_name || "NorthStar Platform"}</div>
          <div style={{ fontSize: 11, opacity: 0.7 }}>{settings.tagline || "AI-Powered Consulting Platform"}</div>
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {["Dashboard", "Leads", "Agent", "Analytics", "Marketplace", "Settings"].map((item) => (
              <div key={item} style={{ padding: "6px 12px", borderRadius: 6, fontSize: 13, background: item === "Settings" ? (settings.accent_color || "#805ad5") + "33" : "transparent", color: item === "Settings" ? (settings.accent_color || "#805ad5") : (settings.sidebar_text || "#e2e8f0"), cursor: "pointer" }}>{item}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Save */}
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={handleSave} disabled={saving} style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}>{saving ? "Saving..." : "Save Settings"}</button>
        {saved && <span style={{ fontSize: 13, color: "#48bb78", fontWeight: 600 }}>Settings saved successfully!</span>}
      </div>
    </div>
  );
}
