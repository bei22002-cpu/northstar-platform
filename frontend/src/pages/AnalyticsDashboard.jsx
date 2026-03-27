import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const cardStyle = { background: "#fff", borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", padding: "20px 24px" };
const statStyle = { textAlign: "center", flex: 1, minWidth: 140 };
const statValue = { fontSize: 28, fontWeight: 700, color: "#2d3748", margin: 0 };
const statLabel = { fontSize: 12, color: "#718096", marginTop: 4 };
const barBg = { height: 24, background: "#edf2f7", borderRadius: 6, overflow: "hidden", marginBottom: 4 };

export default function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAgentAnalytics().catch(() => null),
      api.getAuditLogs(20, 0).catch(() => []),
    ]).then(([a, l]) => {
      setAnalytics(a);
      setLogs(Array.isArray(l) ? l : l?.logs || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <div style={{ padding: 32, textAlign: "center", color: "#718096" }}>Loading analytics...</div>;

  const stats = analytics || { total_messages: 0, total_tokens: 0, avg_latency_ms: 0, messages_today: 0, tool_usage: {}, model_usage: {}, daily_messages: [], messages_by_day: [], top_tools: [], messages_by_provider: {} };
  // Support both field name conventions
  const dailyMessages = stats.daily_messages || stats.messages_by_day || [];
  const toolUsage = stats.tool_usage || (stats.top_tools ? Object.fromEntries((stats.top_tools || []).map(t => [t.tool, t.count])) : {});
  const modelUsage = stats.model_usage || stats.messages_by_provider || {};
  const messagesToday = stats.messages_today ?? stats.total_messages ?? 0;
  const maxDaily = Math.max(1, ...(dailyMessages.map((d) => d.count)));

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h2 style={{ margin: "0 0 4px", color: "#2d3748", fontSize: 22 }}>Analytics Dashboard</h2>
      <p style={{ margin: "0 0 20px", color: "#718096", fontSize: 13 }}>Agent usage metrics and audit trail</p>

      {/* Summary cards */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
        <div style={{ ...cardStyle, ...statStyle }}>
          <p style={statValue}>{stats.total_messages}</p>
          <p style={statLabel}>Total Messages</p>
        </div>
        <div style={{ ...cardStyle, ...statStyle }}>
          <p style={statValue}>{messagesToday}</p>
          <p style={statLabel}>Messages Today</p>
        </div>
        <div style={{ ...cardStyle, ...statStyle }}>
          <p style={statValue}>{(stats.total_tokens || 0).toLocaleString()}</p>
          <p style={statLabel}>Total Tokens</p>
        </div>
        <div style={{ ...cardStyle, ...statStyle }}>
          <p style={statValue}>{Math.round(stats.avg_latency_ms || 0)}ms</p>
          <p style={statLabel}>Avg Latency</p>
        </div>
      </div>

      {/* Daily messages chart */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Messages per Day</h3>
        <div style={{ display: "flex", gap: 4, alignItems: "flex-end", height: 120 }}>
          {dailyMessages.map((d, i) => (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ width: "100%", maxWidth: 40, background: "#3182ce", borderRadius: "4px 4px 0 0", height: Math.max(4, (d.count / maxDaily) * 100) }} />
              <span style={{ fontSize: 9, color: "#a0aec0", marginTop: 4 }}>{d.date?.slice(5) || ""}</span>
            </div>
          ))}
          {dailyMessages.length === 0 && <p style={{ color: "#a0aec0", fontSize: 13, margin: "auto" }}>No data yet</p>}
        </div>
      </div>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
        {/* Tool usage */}
        <div style={{ ...cardStyle, flex: 1, minWidth: 280 }}>
          <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Tool Usage</h3>
          {Object.entries(toolUsage).sort((a, b) => b[1] - a[1]).map(([tool, count]) => {
            const max = Math.max(1, ...Object.values(toolUsage));
            return (
              <div key={tool} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
                  <span style={{ color: "#4a5568", fontWeight: 600 }}>{tool}</span>
                  <span style={{ color: "#718096" }}>{count}</span>
                </div>
                <div style={barBg}><div style={{ height: "100%", width: (count / max * 100) + "%", background: "#805ad5", borderRadius: 6 }} /></div>
              </div>
            );
          })}
          {Object.keys(toolUsage).length === 0 && <p style={{ color: "#a0aec0", fontSize: 13 }}>No tool usage data</p>}
        </div>

        {/* Model usage */}
        <div style={{ ...cardStyle, flex: 1, minWidth: 280 }}>
          <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Model Usage</h3>
          {Object.entries(modelUsage).sort((a, b) => b[1] - a[1]).map(([mdl, count]) => {
            const max = Math.max(1, ...Object.values(modelUsage));
            return (
              <div key={mdl} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
                  <span style={{ color: "#4a5568", fontWeight: 600 }}>{mdl}</span>
                  <span style={{ color: "#718096" }}>{count}</span>
                </div>
                <div style={barBg}><div style={{ height: "100%", width: (count / max * 100) + "%", background: "#3182ce", borderRadius: 6 }} /></div>
              </div>
            );
          })}
          {Object.keys(modelUsage).length === 0 && <p style={{ color: "#a0aec0", fontSize: 13 }}>No model usage data</p>}
        </div>
      </div>

      {/* Recent audit logs */}
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 16px", color: "#2d3748", fontSize: 16 }}>Recent Audit Logs</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Time</th>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Message</th>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Model</th>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Tokens</th>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Latency</th>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#718096", fontWeight: 600 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #edf2f7" }}>
                  <td style={{ padding: "8px 12px", color: "#4a5568", whiteSpace: "nowrap" }}>{log.created_at ? new Date(log.created_at).toLocaleString() : "-"}</td>
                  <td style={{ padding: "8px 12px", color: "#4a5568", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{log.message || "-"}</td>
                  <td style={{ padding: "8px 12px", color: "#4a5568" }}>{log.model_used || "-"}</td>
                  <td style={{ padding: "8px 12px", color: "#4a5568" }}>{(log.tokens_input || 0) + (log.tokens_output || 0)}</td>
                  <td style={{ padding: "8px 12px", color: "#4a5568" }}>{log.latency_ms ? log.latency_ms + "ms" : "-"}</td>
                  <td style={{ padding: "8px 12px" }}>
                    <span style={{ background: log.status === "success" ? "#c6f6d5" : "#fed7d7", color: log.status === "success" ? "#22543d" : "#9b2c2c", padding: "2px 8px", borderRadius: 8, fontSize: 11, fontWeight: 600 }}>{log.status || "unknown"}</span>
                  </td>
                </tr>
              ))}
              {logs.length === 0 && <tr><td colSpan={6} style={{ padding: 16, textAlign: "center", color: "#a0aec0" }}>No audit logs yet</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
