import React from 'react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
  onLogout: () => void;
}

const navItems = [
  { to: '/leads', label: '📋 Leads' },
  { to: '/outreach', label: '✉️ Outreach' },
];

const linkStyle: React.CSSProperties = {
  display: 'block',
  padding: '10px 16px',
  color: '#e2e8f0',
  textDecoration: 'none',
  borderRadius: 6,
  marginBottom: 4,
};

const activeLinkStyle: React.CSSProperties = {
  ...linkStyle,
  background: '#3182ce',
  color: '#fff',
};

export function Sidebar({ onLogout }: SidebarProps) {
  return (
    <aside
      style={{
        width: 220,
        minHeight: '100vh',
        background: '#1a202c',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px 12px',
        gap: 8,
      }}
    >
      <div
        style={{
          color: '#90cdf4',
          fontWeight: 700,
          fontSize: 20,
          marginBottom: 24,
          paddingLeft: 8,
        }}
      >
        ⭐ NorthStar
      </div>

      <nav style={{ flex: 1 }}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => (isActive ? activeLinkStyle : linkStyle)}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={onLogout}
        style={{
          background: 'transparent',
          border: '1px solid #4a5568',
          color: '#a0aec0',
          padding: '8px 16px',
          borderRadius: 6,
          cursor: 'pointer',
          marginTop: 'auto',
        }}
      >
        Logout
      </button>
    </aside>
  );
}
