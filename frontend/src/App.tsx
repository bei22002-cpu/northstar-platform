import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { LeadsPage } from './pages/LeadsPage';
import { OutreachPage } from './pages/OutreachPage';
import { Sidebar } from './components/Sidebar';

function App() {
  const { isLoggedIn, logout } = useAuth();

  if (!isLoggedIn) {
    return <LoginPage onSuccess={() => window.location.reload()} />;
  }

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
        <Sidebar onLogout={logout} />
        <main style={{ flex: 1, background: '#f7fafc', overflowY: 'auto' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/leads" replace />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/outreach" element={<OutreachPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
