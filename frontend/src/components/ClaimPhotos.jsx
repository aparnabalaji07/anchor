import { useEffect, useRef, useState } from "react";
import { photos as photoApi } from "../api";

const POLL_MS = 10000;
const SEVERITY_CLASS = { none: "neutral", minor: "sev-moderate", moderate: "sev-high", severe: "sev-critical" };

function takenTime(ts) {
  return new Date(ts).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function Analysis({ photo, onReanalyze }) {
  if (photo.analysis_status === "pending") return <div className="photo-pending">Analyzing...</div>;
  if (photo.analysis_status === "failed" || !photo.analysis) {
    return (
      <div className="photo-failed">
        Analysis failed.
        <button className="btn small" onClick={() => onReanalyze(photo.id)}>Re-analyze</button>
      </div>
    );
  }
  const a = photo.analysis;
  return (
    <>
      <p className="photo-desc">{a.description}</p>
      <div className="tags">
        <span className={`tag sev ${SEVERITY_CLASS[a.severity] || "neutral"}`}>Severity: {a.severity}</span>
        {a.location && <span className="tag neutral">{a.location}</span>}
        {a.damage.map((d) => <span key={d} className="tag risk">{d}</span>)}
      </div>
    </>
  );
}

export default function ClaimPhotos({ householdId, photoConsent }) {
  const [list, setList] = useState([]);
  const [urls, setUrls] = useState({});
  const [viewing, setViewing] = useState(null);
  const [error, setError] = useState(null);
  const urlsRef = useRef({});
  const loadingRef = useRef(new Set());

  // Poll so new uploads and finished analyses show up without a refresh
  useEffect(() => {
    let active = true;
    const load = () =>
      photoApi.list(householdId)
        .then((data) => { if (active) { setList(data || []); setError(null); } })
        .catch((e) => active && setError(e.message));
    load();
    const timer = setInterval(load, POLL_MS);
    return () => { active = false; clearInterval(timer); };
  }, [householdId]);

  // Fetch each image once and keep an object URL for it
  useEffect(() => {
    for (const p of list) {
      if (urlsRef.current[p.id] || loadingRef.current.has(p.id)) continue;
      loadingRef.current.add(p.id);
      photoApi.image(p.id)
        .then((blob) => {
          urlsRef.current[p.id] = URL.createObjectURL(blob);
          setUrls({ ...urlsRef.current });
        })
        .catch(() => {})
        .finally(() => loadingRef.current.delete(p.id));
    }
  }, [list]);

  // Free the object URLs when leaving the page
  useEffect(() => () => {
    Object.values(urlsRef.current).forEach((u) => URL.revokeObjectURL(u));
    urlsRef.current = {};
  }, [householdId]);

  useEffect(() => {
    if (viewing == null) return;
    const onKey = (e) => { if (e.key === "Escape") setViewing(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [viewing]);

  async function reanalyze(photoId) {
    setList((l) => l.map((p) => (p.id === photoId ? { ...p, analysis_status: "pending" } : p)));
    try {
      await photoApi.analyze(photoId);
    } catch (e) {
      setError(e.message);
    }
  }

  const open = list.find((p) => p.id === viewing);

  return (
    <section className="card photos-card">
      <div className="card-header">
        <span className="label">Claim photos ›</span>
        <span className="muted">{list.length} {list.length === 1 ? "photo" : "photos"}</span>
      </div>
      <div className="card-body">
        {error && <div className="brief-error">Could not load photos: {error}</div>}
        {list.length === 0 ? (
          <div className="muted">
            {photoConsent
              ? "No photos yet. They appear here a few seconds after the box uploads them."
              : "The customer has not agreed to claim photos."}
          </div>
        ) : (
          <div className="photo-grid">
            {list.map((p) => (
              <div key={p.id} className="photo-tile">
                <button className="photo-thumb" onClick={() => setViewing(p.id)} aria-label="View photo larger">
                  {urls[p.id] ? <img src={urls[p.id]} alt="Claim photo" /> : <span className="muted">Loading...</span>}
                </button>
                <div className="photo-meta">
                  <span className="muted">{takenTime(p.taken_at)}</span>
                  <span className={`badge ${p.verified ? "ok" : "sev-critical"}`}
                    title={p.verified ? "Image matches the hash saved at upload" : "Image no longer matches its upload hash"}>
                    {p.verified ? "Verified" : "Changed"}
                  </span>
                </div>
                <Analysis photo={p} onReanalyze={reanalyze} />
              </div>
            ))}
          </div>
        )}
      </div>

      {open && (
        <div className="lightbox" onClick={() => setViewing(null)}>
          <figure className="lightbox-inner" onClick={(e) => e.stopPropagation()}>
            {urls[open.id] && <img src={urls[open.id]} alt="Claim photo, large" />}
            <figcaption>
              <span>{takenTime(open.taken_at)}</span>
              {open.analysis?.description && <span> · {open.analysis.description}</span>}
            </figcaption>
            <button className="btn small lightbox-close" onClick={() => setViewing(null)}>Close</button>
          </figure>
        </div>
      )}
    </section>
  );
}
