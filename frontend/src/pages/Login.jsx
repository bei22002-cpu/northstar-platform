import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f8fafc",
  },
  card: {
    background: "#fff",
    borderRadius: 12,
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    padding: "2.5rem",
    width: "100%",
    maxWidth: 420,
  },
  heading: { fontSize: "1.6rem", fontWeight: 700, marginBottom: "0.25rem" },
  sub: { color: "#64748b", marginBottom: "1.5rem", fontSize: "0.95rem" },
  label: { display: "block", fontWeight: 500, marginBottom: 4, fontSize: "0.9rem" },
  input: {
    width: "100%",
    padding: "0.6rem 0.75rem",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: "0.95rem",
    marginBottom: "1rem",
    outline: "none",
  },
  btn: {
    width: "100%",
    padding: "0.7rem",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontWeight: 600,
    fontSize: "1rem",
    cursor: "pointer",
    marginTop: "0.25rem",
  },
  error: {
    background: "#fee2e2",
    color: "#b91c1c",
    borderRadius: 8,
    padding: "0.6rem 0.75rem",
    marginBottom: "1rem",
    fontSize: "0.9rem",
  },
  toggle: {
    marginTop: "1rem",
    textAlign: "center",
    fontSize: "0.9rem",
    color: "#64748b",
  },
  link: { color: "#2563eb", cursor: "pointer", fontWeight: 500 },
};

export default function Login({ onLogin }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        const data = await api.login(email, password);
        localStorage.setItem("access_token", data.access_token);
        onLogin();
        navigate("/outreach");
      } else {
        await api.register(email, password, fullName);
        setMode("login");
        setError("");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.heading}>NorthStar Platform</h1>
        <p style={styles.sub}>
          {mode === "login" ? "Sign in to your account" : "Create a new account"}
        </p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <>
              <label style={styles.label}>Full name</label>
              <input
                style={styles.input}
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Smith"
              />
            </>
          )}
          <label style={styles.label}>Email</label>
          <input
            style={styles.input}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div style={styles.toggle}>
          {mode === "login" ? (
            <>
              No account?{" "}
              <span style={styles.link} onClick={() => setMode("register")}>
                Register
              </span>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <span style={styles.link} onClick={() => setMode("login")}>
                Sign in
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
