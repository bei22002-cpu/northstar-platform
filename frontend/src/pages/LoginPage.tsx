import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export function LoginPage() {
  const { login, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await login({ email, password });
    setLoading(false);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f7fafc',
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: '#fff',
          padding: 40,
          borderRadius: 12,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
          width: 360,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <h1 style={{ margin: 0, color: '#2d3748', fontSize: 24 }}>⭐ NorthStar</h1>
        <p style={{ margin: 0, color: '#718096', fontSize: 14 }}>Sign in to your account</p>

        {error && (
          <div
            style={{
              background: '#fff5f5',
              color: '#c53030',
              padding: '10px 14px',
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            {error}
          </div>
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={inputStyle}
        />
        <button type="submit" disabled={loading} style={buttonStyle}>
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '10px 14px',
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  fontSize: 14,
  outline: 'none',
};

const buttonStyle: React.CSSProperties = {
  padding: '12px',
  background: '#3182ce',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: 14,
};
