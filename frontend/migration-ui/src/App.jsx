import { useState, useRef, useEffect } from "react";

const STEPS = {
  1: { label: "Classifier",    icon: "⬡" },
  2: { label: "Translator",    icon: "⇄" },
  3: { label: "Pre-Executor",  icon: "⌫" },
  4: { label: "Executor",      icon: "▶" },
  5: { label: "SelfCorrector", icon: "↺" },
  6: { label: "Validator",     icon: "✓" },
  0: { label: "Pipeline",      icon: "⚑" },
};

const STATUS_COLOR = {
  running: "#f0a500",
  ok:      "#22c55e",
  error:   "#ef4444",
  done:    "#6366f1",
};

function StepCard({ step, label, content, status }) {
  const [expanded, setExpanded] = useState(status === "running");
  const meta = STEPS[step] || { label, icon: "•" };

  useEffect(() => {
    if (status === "running") setExpanded(true);
  }, [status]);

  const isCode = content && content.includes("\n");

  return (
    <div
      style={{
        marginBottom: "8px",
        borderRadius: "12px",
        background: "rgba(255,255,255,0.03)",
        overflow: "hidden",
        transition: "all 0.2s",
        border: `1px solid ${STATUS_COLOR[status] || "rgba(255,255,255,0.08)"}`,
      }}
    >
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: "100%",
          background: "none",
          border: "none",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          cursor: "pointer",
          color: "#e2e8f0",
          textAlign: "left",
        }}
      >
        <span style={{ 
          fontSize: "16px", 
          opacity: 0.7,
          width: "24px",
          display: "inline-block",
        }}>{meta.icon}</span>
        <span style={{ 
          fontFamily: "system-ui, -apple-system, sans-serif", 
          fontSize: "13px", 
          fontWeight: 500,
          color: STATUS_COLOR[status] || "#aaa" 
        }}>
          {meta.label}
        </span>
        {status === "running" && (
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "#f0a500" }}>
            <span style={{ 
              display: "inline-block", 
              width: "8px", 
              height: "8px", 
              borderRadius: "50%", 
              background: "#f0a500",
              marginRight: "8px",
              animation: "pulse 1s infinite",
            }} />
            Processing...
          </span>
        )}
        {status === "ok" && (
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "#22c55e" }}>
            ✓ Complete
          </span>
        )}
        {status === "error" && (
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "#ef4444" }}>
            ✗ Failed
          </span>
        )}
        <span style={{ marginLeft: status === "running" ? "0" : "auto", fontSize: "12px", opacity: 0.5 }}>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && content && (
        <div style={{ padding: "0 16px 16px 52px" }}>
          {isCode ? (
            <pre style={{
              margin: 0,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: "12px",
              lineHeight: "1.6",
              color: "#94a3b8",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              background: "rgba(0,0,0,0.3)",
              padding: "12px",
              borderRadius: "8px",
            }}>
              {content}
            </pre>
          ) : (
            <p style={{
              margin: 0,
              fontFamily: "system-ui, -apple-system, sans-serif",
              fontSize: "13px",
              color: "#94a3b8",
              lineHeight: "1.6",
            }}>
              {content}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MigrationMessage({ steps, finalSql, failed }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(finalSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ width: "100%" }}>
      <div style={{ marginBottom: "16px" }}>
        {steps.map((s, i) => (
          <StepCard key={i} {...s} />
        ))}
      </div>

      {finalSql && !failed && (
        <div style={{
          marginTop: "16px",
          background: "rgba(99,102,241,0.05)",
          borderRadius: "12px",
          overflow: "hidden",
          border: "1px solid rgba(99,102,241,0.15)",
        }}>
          <div style={{
            padding: "12px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid rgba(99,102,241,0.1)",
            background: "rgba(99,102,241,0.03)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "14px" }}>🐘</span>
              <span style={{ fontFamily: "system-ui, -apple-system, sans-serif", fontSize: "12px", fontWeight: 500, color: "#6366f1" }}>
                PostgreSQL Output
              </span>
            </div>
            <button
              onClick={copy}
              style={{
                background: copied ? "rgba(34,197,94,0.15)" : "rgba(99,102,241,0.1)",
                border: "none",
                color: copied ? "#22c55e" : "#6366f1",
                padding: "6px 12px",
                borderRadius: "8px",
                cursor: "pointer",
                fontFamily: "system-ui, -apple-system, sans-serif",
                fontSize: "12px",
                fontWeight: 500,
                transition: "all 0.2s",
              }}
            >
              {copied ? "✓ Copied" : "📋 Copy"}
            </button>
          </div>
          <pre style={{
            margin: 0,
            padding: "16px",
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: "12px",
            lineHeight: "1.7",
            color: "#c7d2fe",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "rgba(0,0,0,0.2)",
          }}>
            {finalSql}
          </pre>
        </div>
      )}

      {failed && (
        <div style={{
          marginTop: "16px",
          padding: "14px 16px",
          background: "rgba(239,68,68,0.08)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: "12px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontSize: "13px",
          color: "#f87171",
        }}>
          <span style={{ marginRight: "8px" }}>⚠️</span>
          Migration failed — max retries reached or validation could not be resolved.
        </div>
      )}
    </div>
  );
}

function UserBubble({ sql }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
      <div style={{
        maxWidth: "80%",
        background: "#2a2a35",
        borderRadius: "20px 20px 4px 20px",
        padding: "12px 16px",
      }}>
        <pre style={{
          margin: 0,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: "13px",
          color: "#e2e8f0",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          lineHeight: "1.6",
        }}>
          {sql}
        </pre>
      </div>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div style={{
      width: "32px",
      height: "32px",
      borderRadius: "50%",
      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "14px",
      flexShrink: 0,
    }}>
      <span>🐘</span>
    </div>
  );
}

export default function App() {
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState("");
  const [migrating, setMigrating] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef                 = useRef(null);
  const textareaRef               = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleMigrate = async () => {
    const sql = input.trim();
    if (!sql || migrating) return;

    setInput("");
    setMigrating(true);

    setMessages(prev => [...prev, { type: "user", sql }]);
    const msgIndex = messages.length + 1;
    setMessages(prev => [...prev, { type: "assistant", steps: [], finalSql: null, failed: false, id: Date.now() }]);

    try {
      const res = await fetch(`http://localhost:8000/migrate`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ sql }),
      });

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));

          setMessages(prev => {
            const updated = [...prev];
            const last    = { ...updated[updated.length - 1] };

            if (event.status === "done") {
              last.finalSql = event.content;
            } else if (event.status === "error" && event.step === 0) {
              last.failed = true;
            } else {
              const existing = last.steps.findIndex(s => s.step === event.step && s.label === event.label);
              if (existing >= 0) {
                last.steps = last.steps.map((s, i) => i === existing ? event : s);
              } else {
                last.steps = [...last.steps, event];
              }
            }

            updated[updated.length - 1] = last;
            return updated;
          });
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          failed: true,
        };
        return updated;
      });
    } finally {
      setMigrating(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleMigrate();
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput("");
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&family=JetBrains+Mono:wght@400;500&display=swap');

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: #0f0f13;
          color: #e2e8f0;
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          height: 100vh;
          overflow: hidden;
        }

        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }

        textarea:focus { outline: none; }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
          from { transform: translateX(-100%); }
          to { transform: translateX(0); }
        }

        .message-enter { animation: fadeIn 0.3s ease forwards; }
      `}</style>

      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

        {/* Sidebar - ChatGPT style */}
        <div style={{
          width: sidebarOpen ? "260px" : "0px",
          background: "rgba(15,15,19,0.95)",
          borderRight: sidebarOpen ? "1px solid rgba(255,255,255,0.06)" : "none",
          transition: "width 0.3s ease",
          overflow: "hidden",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}>
          <div style={{ padding: "20px 16px" }}>
            <button
              onClick={handleNewChat}
              style={{
                width: "100%",
                padding: "10px 16px",
                background: "rgba(99,102,241,0.15)",
                border: "1px solid rgba(99,102,241,0.3)",
                borderRadius: "10px",
                color: "#6366f1",
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: "14px",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "8px",
                justifyContent: "center",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = "rgba(99,102,241,0.25)"}
              onMouseLeave={(e) => e.currentTarget.style.background = "rgba(99,102,241,0.15)"}
            >
              <span>+</span> New Migration
            </button>
          </div>
          <div style={{ 
            flex: 1, 
            overflowY: "auto",
            padding: "0 12px",
            fontSize: "13px",
            color: "#64748b",
          }}>
            {messages.filter(m => m.type === "assistant" && m.finalSql).length > 0 && (
              <div style={{ padding: "16px 8px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ marginBottom: "12px", fontWeight: 500, fontSize: "12px", color: "#475569" }}>Recent</div>
                {messages.filter(m => m.type === "assistant" && m.finalSql).slice(-3).map((msg, i) => (
                  <div key={i} style={{ padding: "8px", borderRadius: "8px", cursor: "pointer", fontSize: "12px", color: "#94a3b8" }}>
                    Migration {messages.length - i}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}>

          {/* Header */}
          <div style={{
            padding: "12px 20px",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            gap: "16px",
          }}>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                background: "none",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: "20px",
                padding: "8px",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              ☰
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>🐘</span>
              <span style={{ fontWeight: 600, fontSize: "15px" }}>SQL Server → PostgreSQL</span>
              <span style={{ 
                fontSize: "11px", 
                padding: "2px 8px", 
                background: "rgba(99,102,241,0.15)", 
                borderRadius: "20px",
                color: "#6366f1",
                marginLeft: "8px",
              }}>
                Migration Pipeline
              </span>
            </div>
          </div>

          {/* Messages Area */}
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "0",
          }}>
            <div style={{
              maxWidth: "900px",
              margin: "0 auto",
              padding: "20px 24px",
            }}>
              {messages.length === 0 && (
                <div style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: "400px",
                  textAlign: "center",
                }}>
                  <div style={{
                    fontSize: "56px",
                    marginBottom: "20px",
                  }}>
                    🐘
                  </div>
                  <div style={{ 
                    fontFamily: "inherit", 
                    fontSize: "28px", 
                    fontWeight: 600, 
                    marginBottom: "12px",
                    background: "linear-gradient(135deg, #e2e8f0, #94a3b8)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}>
                    SQL Server to PostgreSQL
                  </div>
                  <div style={{ fontSize: "15px", color: "#64748b", marginBottom: "32px", maxWidth: "450px" }}>
                    Paste your SQL Server DDL below and let the pipeline handle the migration
                  </div>
                  <div style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                    justifyContent: "center",
                  }}>
                    {["Tables", "Procedures", "Functions", "Triggers", "Views"].map(item => (
                      <div key={item} style={{
                        padding: "6px 14px",
                        background: "rgba(255,255,255,0.03)",
                        borderRadius: "20px",
                        fontSize: "12px",
                        color: "#475569",
                      }}>
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className="message-enter" style={{ marginBottom: "24px" }}>
                  {msg.type === "user" ? (
                    <UserBubble sql={msg.sql} />
                  ) : (
                    <div style={{ display: "flex", gap: "12px" }}>
                      <AssistantAvatar />
                      <div style={{ flex: 1 }}>
                        <MigrationMessage
                          steps={msg.steps}
                          finalSql={msg.finalSql}
                          failed={msg.failed}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input Area */}
          <div style={{
            padding: "16px 24px 24px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            flexShrink: 0,
            background: "#0f0f13",
          }}>
            <div style={{
              maxWidth: "900px",
              margin: "0 auto",
            }}>
              <div style={{
                display: "flex",
                gap: "12px",
                background: "rgba(255,255,255,0.04)",
                border: `1px solid ${migrating ? "rgba(99,102,241,0.4)" : "rgba(255,255,255,0.08)"}`,
                borderRadius: "16px",
                padding: "12px 16px",
                transition: "all 0.2s",
              }}>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Paste your SQL Server DDL here... (⌘/Ctrl + Enter to migrate)"
                  disabled={migrating}
                  rows={3}
                  style={{
                    flex: 1,
                    background: "none",
                    border: "none",
                    resize: "none",
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    fontSize: "13px",
                    lineHeight: "1.6",
                    color: "#e2e8f0",
                    minHeight: "60px",
                  }}
                />
                <button
                  onClick={handleMigrate}
                  disabled={migrating || !input.trim()}
                  style={{
                    background: migrating ? "rgba(99,102,241,0.2)" : "#6366f1",
                    border: "none",
                    color: migrating ? "#6366f1" : "#fff",
                    padding: "0 24px",
                    borderRadius: "12px",
                    cursor: migrating || !input.trim() ? "not-allowed" : "pointer",
                    fontFamily: "inherit",
                    fontSize: "14px",
                    fontWeight: 500,
                    opacity: !input.trim() && !migrating ? 0.5 : 1,
                    transition: "all 0.2s",
                    whiteSpace: "nowrap",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  {migrating ? (
                    <>
                      <span style={{ 
                        display: "inline-block", 
                        width: "14px", 
                        height: "14px", 
                        borderRadius: "50%", 
                        border: "2px solid currentColor",
                        borderTopColor: "transparent",
                        animation: "pulse 0.8s linear infinite",
                      }} />
                      Migrating
                    </>
                  ) : (
                    "→ Migrate"
                  )}
                </button>
              </div>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "8px",
                fontSize: "11px",
                color: "#334155",
                padding: "0 4px",
              }}>
                <span>Supports: CREATE TABLE, PROCEDURE, FUNCTION, TRIGGER, VIEW</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

