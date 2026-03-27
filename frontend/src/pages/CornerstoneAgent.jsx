import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

const QUICK_PROMPTS = [
  "Show me all Python files",
  "What is the project structure?",
  "Check git status",
  "Read the main.py file",
];

const PROVIDERS = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "openai", label: "OpenAI (GPT-4)" },
  { value: "google", label: "Google (Gemini)" },
];

const cardStyle = { background: "#fff", borderRadius: 10, boxShadow: "0 2px 12px rgba(0,0,0,0.06)" };
const clearBtnStyle = { background: "transparent", border: "1px solid #e2e8f0", color: "#718096", padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 500 };
const toolBadgeStyle = { background: "#ebf4ff", color: "#3182ce", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600 };
const toolToggleStyle = { background: "transparent", border: "1px solid #e9d8fd", color: "#805ad5", padding: "4px 12px", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 600 };
const quickPromptStyle = { background: "#ebf4ff", border: "1px solid #bee3f8", color: "#2b6cb0", padding: "6px 14px", borderRadius: 16, cursor: "pointer", fontSize: 13, fontWeight: 500 };
const sendBtnStyle = { background: "#3182ce", color: "#fff", border: "none", padding: "12px 24px", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" };
const dotStyle = { width: 8, height: 8, borderRadius: "50%", background: "#805ad5", animation: "pulse 1.2s ease-in-out infinite", display: "inline-block" };
const selectStyle = { padding: "6px 10px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 12, background: "#fff", color: "#4a5568", cursor: "pointer", outline: "none" };

export default function CornerstoneAgent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [agentInfo, setAgentInfo] = useState(null);
  const [history, setHistory] = useState([]);
  const [expandedTools, setExpandedTools] = useState({});
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("");
  const [requireApproval, setRequireApproval] = useState(true);
  const [pendingApprovals, setPendingApprovals] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [useStreaming, setUseStreaming] = useState(false);
  const bottomRef = useRef(null);
  const nextId = useRef(0);

  useEffect(() => {
    api.getAgentInfo().then(setAgentInfo).catch(() => {});
    api.getSubscription().then(setSubscription).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, streamingText]);

  const handleSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    const userMsg = { id: nextId.current++, role: "user", content: text, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    setStreamingText("");
    try {
      if (useStreaming) {
        const res = await api.streamAgentMessage(text, history, model);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") break;
              try {
                const parsed = JSON.parse(data);
                if (parsed.token) { fullText += parsed.token; setStreamingText(fullText); }
                if (parsed.tool_actions) {
                  setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: fullText || parsed.response || "", toolActions: parsed.tool_actions, tokens: parsed.tokens, timestamp: new Date() }]);
                  if (parsed.history) setHistory(parsed.history);
                }
              } catch (_e) { /* ignore parse errors */ }
            }
          }
        }
        if (fullText) {
          setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: fullText, timestamp: new Date() }]);
        }
        setStreamingText("");
      } else {
        const res = await api.sendAgentMessage(text, history, provider, model, requireApproval);
        if (res.pending_approvals && res.pending_approvals.length > 0) {
          setPendingApprovals(res.pending_approvals);
          setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: "I need your approval to perform the following actions:", toolActions: res.tool_actions, pendingApprovals: res.pending_approvals, timestamp: new Date() }]);
        } else {
          setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: res.response, toolActions: res.tool_actions, tokens: res.tokens, timestamp: new Date() }]);
          setHistory(res.history);
        }
      }
      api.getSubscription().then(setSubscription).catch(() => {});
    } catch (err) {
      setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: err?.message || "An error occurred.", timestamp: new Date() }]);
    } finally { setSending(false); }
  };

  const handleApproval = async (approved) => {
    if (!pendingApprovals) return;
    setSending(true);
    try {
      const res = await api.approveTools(pendingApprovals, approved);
      setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: approved ? res.response : "Actions cancelled.", toolActions: res.tool_actions || [], timestamp: new Date() }]);
      if (res.history) setHistory(res.history);
    } catch (err) {
      setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: err?.message || "Error processing approval.", timestamp: new Date() }]);
    } finally { setPendingApprovals(null); setSending(false); }
  };

  const toggleTool = (msgId) => setExpandedTools((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  const handleClear = () => { setMessages([]); setHistory([]); setExpandedTools({}); setPendingApprovals(null); setStreamingText(""); };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", maxWidth: 960, margin: "0 auto", padding: "16px 16px 0" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <div>
          <h2 style={{ margin: 0, color: "#2d3748", fontSize: 22 }}>Cornerstone AI Agent</h2>
          <p style={{ margin: "4px 0 0", color: "#718096", fontSize: 13 }}>Autonomous AI assistant with multi-model support</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {agentInfo && <span style={{ background: agentInfo.status === "online" ? "#c6f6d5" : "#fed7d7", color: agentInfo.status === "online" ? "#22543d" : "#9b2c2c", padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600 }}>{agentInfo.status.toUpperCase()}</span>}
          <button onClick={handleClear} style={clearBtnStyle}>Clear Chat</button>
        </div>
      </div>

      {/* Controls bar */}
      <div style={{ ...cardStyle, padding: "10px 16px", marginBottom: 12, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Provider:</label>
          <select value={provider} onChange={(e) => { setProvider(e.target.value); setModel(""); }} style={selectStyle}>
            {PROVIDERS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label style={{ fontSize: 12, color: "#718096", fontWeight: 600 }}>Model:</label>
          <select value={model} onChange={(e) => setModel(e.target.value)} style={selectStyle}>
            <option value="">Default</option>
            {agentInfo?.providers?.[provider]?.models?.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#718096", cursor: "pointer" }}>
          <input type="checkbox" checked={requireApproval} onChange={(e) => setRequireApproval(e.target.checked)} /> Require approval
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#718096", cursor: "pointer" }}>
          <input type="checkbox" checked={useStreaming} onChange={(e) => setUseStreaming(e.target.checked)} /> Streaming
        </label>
        {subscription && (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ background: subscription.tier === "free" ? "#ebf4ff" : "#f0fff4", color: subscription.tier === "free" ? "#3182ce" : "#276749", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>{subscription.tier}</span>
            <span style={{ fontSize: 11, color: "#a0aec0" }}>{subscription.messages_used}/{subscription.messages_limit} msgs</span>
            <div style={{ width: 60, height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ width: Math.min(100, (subscription.messages_used / subscription.messages_limit) * 100) + "%", height: "100%", background: (subscription.messages_used / subscription.messages_limit) > 0.8 ? "#e53e3e" : "#48bb78", borderRadius: 3 }} />
            </div>
          </div>
        )}
      </div>

      {/* Tool capabilities */}
      {agentInfo && agentInfo.tools && (
        <div style={{ ...cardStyle, padding: "10px 16px", marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: 12, color: "#718096", fontWeight: 600, marginRight: 4 }}>Tools:</span>
          {agentInfo.tools.map((tool) => <span key={tool} style={toolBadgeStyle}>{tool}</span>)}
        </div>
      )}

      {/* Chat area */}
      <div style={{ flex: 1, overflowY: "auto", marginBottom: 16, paddingBottom: 8 }}>
        {messages.length === 0 && !sending && (
          <div style={{ ...cardStyle, textAlign: "center", padding: 48, marginTop: 32 }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>{"</>"}</div>
            <h3 style={{ margin: "0 0 8px", color: "#2d3748" }}>Welcome to Cornerstone AI Agent</h3>
            <p style={{ margin: 0, color: "#718096", fontSize: 14, maxWidth: 480, marginLeft: "auto", marginRight: "auto" }}>Ask me to read files, write code, run commands, search your codebase, or manage your project.</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 20 }}>
              {QUICK_PROMPTS.map((prompt) => <button key={prompt} onClick={() => setInput(prompt)} style={quickPromptStyle}>{prompt}</button>)}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} style={{ marginBottom: 16, display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ ...cardStyle, maxWidth: "85%", padding: "12px 16px", background: msg.role === "user" ? "#3182ce" : "#fff", color: msg.role === "user" ? "#fff" : "#2d3748", borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, opacity: 0.7 }}>{msg.role === "user" ? "You" : "Cornerstone AI"}</div>
              <div style={{ fontSize: 14, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.content}</div>
              {msg.tokens && <div style={{ marginTop: 6, fontSize: 10, color: msg.role === "user" ? "rgba(255,255,255,0.6)" : "#a0aec0" }}>Tokens: {msg.tokens.input_tokens} in / {msg.tokens.output_tokens} out</div>}
            </div>
            {/* Approval UI */}
            {msg.pendingApprovals && pendingApprovals && (
              <div style={{ maxWidth: "85%", marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
                {msg.pendingApprovals.map((a, i) => (
                  <div key={i} style={{ ...cardStyle, padding: "10px 14px", background: "#fffaf0", borderLeft: "3px solid #ed8936" }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#c05621" }}>{a.tool}</div>
                    <code style={{ fontSize: 11, color: "#744210" }}>{JSON.stringify(a.input).slice(0, 200)}</code>
                  </div>
                ))}
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => handleApproval(true)} style={{ background: "#48bb78", color: "#fff", border: "none", padding: "8px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 13 }}>Approve</button>
                  <button onClick={() => handleApproval(false)} style={{ background: "#fc8181", color: "#fff", border: "none", padding: "8px 20px", borderRadius: 6, cursor: "pointer", fontWeight: 600, fontSize: 13 }}>Reject</button>
                </div>
              </div>
            )}
            {/* Tool actions */}
            {msg.toolActions && msg.toolActions.length > 0 && (
              <div style={{ maxWidth: "85%", marginTop: 6 }}>
                <button onClick={() => toggleTool(msg.id)} style={toolToggleStyle}>{expandedTools[msg.id] ? "Hide" : "Show"} {msg.toolActions.length} tool action{msg.toolActions.length > 1 ? "s" : ""}</button>
                {expandedTools[msg.id] && (
                  <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 8 }}>
                    {msg.toolActions.map((action, i) => (
                      <div key={i} style={{ ...cardStyle, padding: "10px 14px", background: "#f7fafc", borderLeft: "3px solid #805ad5" }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "#805ad5", marginBottom: 4 }}>{action.tool}</div>
                        <div style={{ fontSize: 12, color: "#4a5568", marginBottom: 4 }}><strong>Input:</strong> <code style={{ background: "#edf2f7", padding: "1px 4px", borderRadius: 3, fontSize: 11 }}>{JSON.stringify(action.input).slice(0, 200)}</code></div>
                        <div style={{ fontSize: 12, color: "#4a5568" }}><strong>Output:</strong><pre style={{ margin: "4px 0 0", fontSize: 11, background: "#edf2f7", padding: 8, borderRadius: 4, overflowX: "auto", maxHeight: 200, whiteSpace: "pre-wrap" }}>{action.output.slice(0, 1000)}{action.output.length > 1000 ? "\n...(truncated)" : ""}</pre></div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div style={{ fontSize: 10, color: "#a0aec0", marginTop: 4, paddingLeft: 4 }}>{msg.timestamp.toLocaleTimeString()}</div>
          </div>
        ))}

        {sending && streamingText && (
          <div style={{ marginBottom: 16, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <div style={{ ...cardStyle, maxWidth: "85%", padding: "12px 16px", borderRadius: "16px 16px 16px 4px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: "#718096" }}>Cornerstone AI</div>
              <div style={{ fontSize: 14, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{streamingText}<span style={{ ...dotStyle, marginLeft: 2 }} /></div>
            </div>
          </div>
        )}

        {sending && !streamingText && (
          <div style={{ display: "flex", alignItems: "flex-start", marginBottom: 16 }}>
            <div style={{ ...cardStyle, padding: "12px 16px", borderRadius: "16px 16px 16px 4px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: "#718096" }}>Cornerstone AI</div>
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <span style={dotStyle} /><span style={{ ...dotStyle, animationDelay: "0.2s" }} /><span style={{ ...dotStyle, animationDelay: "0.4s" }} />
                <span style={{ fontSize: 13, color: "#718096", marginLeft: 8 }}>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} style={{ display: "flex", gap: 8, padding: "12px 0 16px", borderTop: "1px solid #e2e8f0" }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the Cornerstone AI Agent..." disabled={sending} style={{ flex: 1, padding: "12px 16px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" }} />
        <button type="submit" disabled={sending || !input.trim()} style={{ ...sendBtnStyle, opacity: sending || !input.trim() ? 0.5 : 1 }}>{sending ? "Sending..." : "Send"}</button>
      </form>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }`}</style>
    </div>
  );
}
