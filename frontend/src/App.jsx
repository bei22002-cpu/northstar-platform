import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Outreach from "./pages/Outreach.jsx";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("access_token"));

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login onLogin={() => setAuthed(true)} />} />
        <Route
          path="/outreach"
          element={
            <PrivateRoute>
              <Outreach onLogout={() => setAuthed(false)} />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to={authed ? "/outreach" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
