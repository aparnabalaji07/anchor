import { useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { BellIcon, FileIcon, HelpIcon, HomeIcon, ListIcon, MapIcon, ShieldIcon, SparkIcon } from "./components/Icons";
import { extra } from "./api";
import CallListPage from "./pages/CallListPage";
import HouseholdPage from "./pages/HouseholdPage";
import MapPage from "./pages/MapPage";
import OverviewPage from "./pages/OverviewPage";
import "./App.css";

function greeting() {
  const h = new Date().getHours();
  const part = h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
  const name = localStorage.getItem("agentName");
  return `Good ${part}${name ? `, ${name}` : ""}`;
}

function initials() {
  const name = localStorage.getItem("agentName") || "Agent";
  return name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

export default function App() {
  const [aiState, setAiState] = useState("idle");

  async function refreshAi() {
    setAiState("working");
    try {
      await extra.generateReasons(15);
      setAiState("done");
    } catch {
      setAiState("idle");
    }
  }

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
          <button className="ask" onClick={refreshAi} disabled={aiState === "working"}>
            <SparkIcon />
            {aiState === "working" ? "Writing reasons..." : aiState === "done" ? "AI reasons updated" : "Refresh AI reasons"}
          </button>
        </aside>
        <main className="content">
          <header className="topbar">
            <h1 className="greeting">{greeting()}</h1>
            <div className="top-actions">
              <span className="icon-btn live-dot" title="Live feed" />
              <span className="icon-btn"><BellIcon /></span>
              <span className="icon-btn"><HelpIcon /></span>
              <span className="avatar">{initials()}</span>
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
