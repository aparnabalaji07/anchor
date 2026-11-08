import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import CallListPage from "./pages/CallListPage";
import HouseholdPage from "./pages/HouseholdPage";
import MapPage from "./pages/MapPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark">⚓</span>
            <div>
              <div className="brand-name">ANCHOR</div>
              <div className="brand-sub">Agent console</div>
            </div>
          </div>
          <NavLink to="/" end className="side-link">
            Call queue
          </NavLink>
          <NavLink to="/map" className="side-link">
            Map
          </NavLink>
          <div className="live">
            <span className="dot" /> Live feed
          </div>
        </aside>
        <main className="content">
          <Routes>
            <Route path="/" element={<CallListPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/household/:id" element={<HouseholdPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
