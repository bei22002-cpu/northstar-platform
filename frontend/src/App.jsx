import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Outreach from "./pages/Outreach.jsx";
import BusinessIdeas from "./pages/BusinessIdeas.jsx";
import AIEngines from "./pages/AIEngines.jsx";
import FundingTracker from "./pages/FundingTracker.jsx";
import Rewards from "./pages/Rewards.jsx";
import CornerstoneAgent from "./pages/CornerstoneAgent.jsx";
import AnalyticsDashboard from "./pages/AnalyticsDashboard.jsx";
import AgentMarketplace from "./pages/AgentMarketplace.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import PricingPage from "./pages/PricingPage.jsx";
import AppSidebar from "./components/Sidebar.jsx";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

function AuthenticatedLayout({ onLogout, children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <AppSidebar onLogout={onLogout} />
      <main className="main-content" style={{ flex: 1, background: "#f7fafc", overflowY: "auto" }}>
        {children}
      </main>
      <style>{`
        @media (max-width: 768px) {
          .main-content {
            padding-top: 56px;
          }
        }
      `}</style>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("access_token"));

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setAuthed(false);
  };

  if (!authed) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/login" element={<Login onLogin={() => setAuthed(true)} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <AuthenticatedLayout onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<Navigate to="/ideas" replace />} />
          <Route path="/ideas" element={<BusinessIdeas />} />
          <Route path="/outreach" element={<Outreach onLogout={handleLogout} />} />
          <Route path="/ai-engines" element={<AIEngines />} />
          <Route path="/funding" element={<FundingTracker />} />
          <Route path="/rewards" element={<Rewards />} />
          <Route path="/agent" element={<CornerstoneAgent />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/marketplace" element={<AgentMarketplace />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/ideas" replace />} />
        </Routes>
      </AuthenticatedLayout>
    </BrowserRouter>
  );
}
