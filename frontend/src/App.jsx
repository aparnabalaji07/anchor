import { useEffect, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { BellIcon, FileIcon, HelpIcon, HomeIcon, ListIcon, MapIcon, ShieldIcon, UserIcon } from "./components/Icons";
import CallListPage from "./pages/CallListPage";
import HouseholdPage from "./pages/HouseholdPage";
import MapPage from "./pages/MapPage";
import OverviewPage from "./pages/OverviewPage";
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

export default function App() {
  const [now, setNow] = useState(() => new Date());
  // Comes from the signed-in agent once login exists (change 8).
  const agentName = null;

  // Re-render each minute so the greeting flips at 5am, 12pm and 5pm.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <BrowserRouter>
      <div className="layout">
        <aside className="sidebar">
          <div className="brand"><span className="brand-mark">⚓</span> Anchor</div>
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
            <h1 className="greeting">{greeting(now, agentName)}</h1>
            <div className="top-actions">
              <span className="icon-btn live-dot" title="Live feed" />
              <span className="icon-btn"><BellIcon /></span>
              <span className="icon-btn"><HelpIcon /></span>
              <span className="avatar">{initials(agentName) || <UserIcon />}</span>
            </div>
          </header>
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/queue" element={<CallListPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/household/:id" element={<HouseholdPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
