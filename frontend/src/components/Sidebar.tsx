import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
  onLogout: () => void;
}

const navItems = [
  { to: '/ideas', label: 'Business Ideas' },
  { to: '/leads', label: 'Leads' },
  { to: '/outreach', label: 'Outreach' },
  { to: '/ai-engines', label: 'AI Engines' },
  { to: '/funding', label: 'Funding Tracker' },
  { to: '/rewards', label: 'Rewards' },
];

const linkStyle: React.CSSProperties = {
  display: 'block',
  padding: '10px 16px',
  color: '#e2e8f0',
  textDecoration: 'none',
  borderRadius: 6,
  marginBottom: 4,
  fontSize: 14,
};

const activeLinkStyle: React.CSSProperties = {
  ...linkStyle,
  background: '#3182ce',
  color: '#fff',
};

export function Sidebar({ onLogout }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
        style={{
          position: 'fixed',
          top: 12,
          left: 12,
          zIndex: 1100,
          background: '#1a202c',
          color: '#90cdf4',
          border: 'none',
          borderRadius: 6,
          width: 40,
          height: 40,
          cursor: 'pointer',
          fontSize: 20,
          display: 'none',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        }}
        className="mobile-menu-btn"
      >
        {mobileOpen ? '\u2715' : '\u2630'}
      </button>

      {/* Overlay for mobile */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 999,
          }}
          className="mobile-overlay"
        />
      )}

      <aside
        className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}
        style={{
          width: 220,
          minHeight: '100vh',
          background: '#1a202c',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px 12px',
          gap: 8,
          flexShrink: 0,
          zIndex: 1000,
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
          NorthStar
        </div>

        <nav style={{ flex: 1 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
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
            fontSize: 14,
          }}
        >
          Logout
        </button>
      </aside>

      {/* Mobile responsive styles */}
      <style>{`
        @media (max-width: 768px) {
          .mobile-menu-btn {
            display: flex !important;
          }
          .sidebar {
            position: fixed !important;
            top: 0;
            left: -240px;
            height: 100vh;
            transition: left 0.3s ease;
          }
          .sidebar-open {
            left: 0 !important;
          }
        }
      `}</style>
    </>
  );
}
