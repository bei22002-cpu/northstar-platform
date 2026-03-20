import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { LeadsPage } from './pages/LeadsPage';
import { OutreachPage } from './pages/OutreachPage';
import { BusinessIdeasPage } from './pages/BusinessIdeasPage';
import { AIEnginesPage } from './pages/AIEnginesPage';
import { FundingTrackerPage } from './pages/FundingTrackerPage';
import { RewardsPage } from './pages/RewardsPage';
import { Sidebar } from './components/Sidebar';

function App() {
  const { isLoggedIn, logout } = useAuth();

  if (!isLoggedIn) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
        <Sidebar onLogout={logout} />
        <main className="main-content" style={{ flex: 1, background: '#f7fafc', overflowY: 'auto' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/ideas" replace />} />
            <Route path="/ideas" element={<BusinessIdeasPage />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/outreach" element={<OutreachPage />} />
            <Route path="/ai-engines" element={<AIEnginesPage />} />
            <Route path="/funding" element={<FundingTrackerPage />} />
            <Route path="/rewards" element={<RewardsPage />} />
          </Routes>
        </main>
      </div>
      <style>{`
        @media (max-width: 768px) {
          .main-content {
            padding-top: 56px;
          }
        }
      `}</style>
    </BrowserRouter>
  );
}

export default App;
