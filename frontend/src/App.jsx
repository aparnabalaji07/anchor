import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BellIcon, FileIcon, HelpIcon, HomeIcon, ListIcon, MapIcon, ShieldIcon } from "./components/Icons";
import { clearSession, getSession } from "./api";
import CallListPage from "./pages/CallListPage";
import HouseholdPage from "./pages/HouseholdPage";
import LoginPage from "./pages/LoginPage";
import MapPage from "./pages/MapPage";
import OverviewPage from "./pages/OverviewPage";
import logo from "./assets/logo.png";
import "./App.css";

// 5:00-11:59 morning, 12:00-16:59 afternoon, 17:00-4:59 evening
function greeting(now, name) {
  const h = now.getHours();
  const part = h >= 5 && h < 12 ? "morning" : h >= 12 && h < 17 ? "afternoon" : "evening";
  const first = name?.trim().split(/\s+/)[0];
  return `Good ${part}${first ? `, ${first}` : ""}`;
}

function initials(name) {
  const words = name?.trim().split(/\s+/).filter(Boolean) ?? [];
  return words.map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

function AccountMenu({ agent, onSignOut }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="account" ref={ref}>
      <button className="avatar" onClick={() => setOpen((o) => !o)} aria-expanded={open} title={agent.name}>
        {initials(agent.name)}
      </button>
      {open && (
        <div className="account-menu">
          <div className="account-name">{agent.name}</div>
          <div className="muted">{agent.email}</div>
          <button className="btn account-signout" onClick={onSignOut}>Sign out</button>
        </div>
      )}
    </div>
  );
}

function Shell({ agent, onSignOut }) {
  const [now, setNow] = useState(() => new Date());

  // Re-render each minute so the greeting flips at 5am, 12pm and 5pm.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand"><img src={logo} alt="" className="brand-logo" /> Anchor</div>
        <div className="side-section">Track</div>
        <NavLink to="/" end className="side-link"><HomeIcon /> Overview</NavLink>
        <NavLink to="/queue" className="side-link"><ListIcon /> Call queue</NavLink>
        <NavLink to="/map" className="side-link"><MapIcon /> Map</NavLink>
        <div className="side-section">Services</div>
        <span className="side-link static"><FileIcon /> Claim drafts</span>
        <span className="side-link static"><ShieldIcon /> Evidence integrity</span>
      </aside>
      <main className="content">
        <header className="topbar">
          <h1 className="greeting">{greeting(now, agent.name)}</h1>
          <div className="top-actions">
            <span className="icon-btn live-dot" title="Live feed" />
            <span className="icon-btn"><BellIcon /></span>
            <span className="icon-btn"><HelpIcon /></span>
            <AccountMenu agent={agent} onSignOut={onSignOut} />
          </div>
        </header>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/queue" element={<CallListPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/household/:id" element={<HouseholdPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function AppRoutes() {
  const [agent, setAgent] = useState(getSession);
  const navigate = useNavigate();
  const location = useLocation();

  function signedIn(session) {
    setAgent(session);
    navigate(location.state?.from || "/", { replace: true });
  }

  function signOut() {
    clearSession();
    setAgent(null);
    navigate("/login", { replace: true });
  }

  return (
    <Routes>
      <Route path="/login" element={agent ? <Navigate to="/" replace /> : <LoginPage onSignedIn={signedIn} />} />
      <Route
        path="*"
        element={agent
          ? <Shell agent={agent} onSignOut={signOut} />
          : <Navigate to="/login" replace state={{ from: location.pathname }} />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
