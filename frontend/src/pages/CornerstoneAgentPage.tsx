import React, { useEffect, useRef, useState } from 'react';
import {
  sendAgentMessage,
  getAgentInfo,
  AgentToolAction,
  AgentInfo,
} from '../services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  toolActions?: AgentToolAction[];
  timestamp: Date;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CornerstoneAgentPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [agentInfo, setAgentInfo] = useState<AgentInfo | null>(null);
  const [history, setHistory] = useState<Array<Record<string, any>>>([]);
  const [expandedTools, setExpandedTools] = useState<Record<number, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);
  let nextId = useRef(0);

  useEffect(() => {
    getAgentInfo()
      .then(setAgentInfo)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: ChatMessage = {
      id: nextId.current++,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);

    try {
      const res = await sendAgentMessage(text, history);
      const assistantMsg: ChatMessage = {
        id: nextId.current++,
        role: 'assistant',
        content: res.response,
        toolActions: res.tool_actions,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setHistory(res.history);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: nextId.current++,
        role: 'assistant',
        content:
          err?.response?.data?.detail ||
          'An error occurred while communicating with the agent. Please check that the ANTHROPIC_API_KEY is configured.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  const toggleTool = (msgId: number) => {
    setExpandedTools((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleClear = () => {
    setMessages([]);
    setHistory([]);
    setExpandedTools({});
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', maxWidth: 960, margin: '0 auto', padding: '16px 16px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <h2 style={{ margin: 0, color: '#2d3748', fontSize: 22 }}>Cornerstone AI Agent</h2>
          <p style={{ margin: '4px 0 0', color: '#718096', fontSize: 13 }}>
            Autonomous AI assistant — reads, writes, and manages your project workspace
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {agentInfo && (
            <span
              style={{
                background: agentInfo.status === 'online' ? '#c6f6d5' : '#fed7d7',
                color: agentInfo.status === 'online' ? '#22543d' : '#9b2c2c',
                padding: '4px 12px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {agentInfo.status.toUpperCase()}
            </span>
          )}
          <button onClick={handleClear} style={clearBtnStyle}>
            Clear Chat
          </button>
        </div>
      </div>

      {/* Tool capabilities bar */}
      {agentInfo && (
        <div style={{ ...cardStyle, padding: '12px 16px', marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#718096', fontWeight: 600, marginRight: 4 }}>Tools:</span>
          {agentInfo.tools.map((tool) => (
            <span key={tool} style={toolBadgeStyle}>
              {tool}
            </span>
          ))}
        </div>
      )}

      {/* Chat messages */}
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: 16, paddingBottom: 8 }}>
        {messages.length === 0 && !sending && (
          <div style={{ ...cardStyle, textAlign: 'center', padding: 48, marginTop: 32 }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>{'</>'}</div>
            <h3 style={{ margin: '0 0 8px', color: '#2d3748' }}>Welcome to Cornerstone AI Agent</h3>
            <p style={{ margin: 0, color: '#718096', fontSize: 14, maxWidth: 480, marginLeft: 'auto', marginRight: 'auto' }}>
              Ask me to read files, write code, run commands, search your codebase, or manage your project.
              I can help you build, debug, and maintain the Cornerstone Platform.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 20 }}>
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  style={quickPromptStyle}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                ...cardStyle,
                maxWidth: '85%',
                padding: '12px 16px',
                background: msg.role === 'user' ? '#3182ce' : '#fff',
                color: msg.role === 'user' ? '#fff' : '#2d3748',
                borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, opacity: 0.7 }}>
                {msg.role === 'user' ? 'You' : 'Cornerstone AI'}
              </div>
              <div style={{ fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {msg.content}
              </div>
            </div>

            {/* Tool actions */}
            {msg.toolActions && msg.toolActions.length > 0 && (
              <div style={{ maxWidth: '85%', marginTop: 6 }}>
                <button onClick={() => toggleTool(msg.id)} style={toolToggleStyle}>
                  {expandedTools[msg.id] ? 'Hide' : 'Show'} {msg.toolActions.length} tool action{msg.toolActions.length > 1 ? 's' : ''}
                </button>
                {expandedTools[msg.id] && (
                  <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {msg.toolActions.map((action, i) => (
                      <div key={i} style={{ ...cardStyle, padding: '10px 14px', background: '#f7fafc', borderLeft: '3px solid #805ad5' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#805ad5', marginBottom: 4 }}>
                          {action.tool}
                        </div>
                        <div style={{ fontSize: 12, color: '#4a5568', marginBottom: 4 }}>
                          <strong>Input:</strong>{' '}
                          <code style={{ background: '#edf2f7', padding: '1px 4px', borderRadius: 3, fontSize: 11 }}>
                            {JSON.stringify(action.input).slice(0, 200)}
                            {JSON.stringify(action.input).length > 200 ? '...' : ''}
                          </code>
                        </div>
                        <div style={{ fontSize: 12, color: '#4a5568' }}>
                          <strong>Output:</strong>
                          <pre style={{ margin: '4px 0 0', fontSize: 11, background: '#edf2f7', padding: 8, borderRadius: 4, overflowX: 'auto', maxHeight: 200, whiteSpace: 'pre-wrap' }}>
                            {action.output.slice(0, 1000)}
                            {action.output.length > 1000 ? '\n...(truncated)' : ''}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div style={{ fontSize: 10, color: '#a0aec0', marginTop: 4, paddingLeft: 4, paddingRight: 4 }}>
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}

        {sending && (
          <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 16 }}>
            <div style={{ ...cardStyle, padding: '12px 16px', borderRadius: '16px 16px 16px 4px' }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#718096' }}>Cornerstone AI</div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <span style={dotStyle} />
                <span style={{ ...dotStyle, animationDelay: '0.2s' }} />
                <span style={{ ...dotStyle, animationDelay: '0.4s' }} />
                <span style={{ fontSize: 13, color: '#718096', marginLeft: 8 }}>Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSend} style={{ display: 'flex', gap: 8, padding: '12px 0 16px', borderTop: '1px solid #e2e8f0' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the Cornerstone AI Agent..."
          disabled={sending}
          style={{
            flex: 1,
            padding: '12px 16px',
            border: '1px solid #e2e8f0',
            borderRadius: 8,
            fontSize: 14,
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{
            ...sendBtnStyle,
            opacity: sending || !input.trim() ? 0.5 : 1,
          }}
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </form>

      {/* Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Constants & Styles
// ---------------------------------------------------------------------------

const QUICK_PROMPTS = [
  'Show me all Python files',
  'What is the project structure?',
  'Check git status',
  'Read the main.py file',
];

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 10,
  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
};

const clearBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid #e2e8f0',
  color: '#718096',
  padding: '6px 14px',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
};

const toolBadgeStyle: React.CSSProperties = {
  background: '#ebf4ff',
  color: '#3182ce',
  padding: '3px 10px',
  borderRadius: 12,
  fontSize: 11,
  fontWeight: 600,
};

const toolToggleStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid #e9d8fd',
  color: '#805ad5',
  padding: '4px 12px',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
};

const quickPromptStyle: React.CSSProperties = {
  background: '#ebf4ff',
  border: '1px solid #bee3f8',
  color: '#2b6cb0',
  padding: '6px 14px',
  borderRadius: 16,
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
};

const sendBtnStyle: React.CSSProperties = {
  background: '#3182ce',
  color: '#fff',
  border: 'none',
  padding: '12px 24px',
  borderRadius: 8,
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: 14,
  whiteSpace: 'nowrap',
};

const dotStyle: React.CSSProperties = {
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: '#805ad5',
  animation: 'pulse 1.2s ease-in-out infinite',
  display: 'inline-block',
};
