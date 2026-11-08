import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import CallListPage from "./pages/CallListPage";
import MapPage from "./pages/MapPage";
import HouseholdPage from "./pages/HouseholdPage";
import ClaimReviewPage from "./pages/ClaimReviewPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="content">
        <Routes>
          <Route path="/" element={<CallListPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/household/:id" element={<HouseholdPage />} />
          <Route path="/household/:id/claim" element={<ClaimReviewPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
