import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AreaChart from "../components/AreaChart";
import { api, getAgentName, household, STATUS_LABELS } from "../api";

const SOURCE_LABELS = { measured: "Measured", needs_confirmation: "Needs confirmation", photo: "From photo" };

function fmt(ts) {
  return ts ? new Date(ts).toLocaleString() : "—";
}

export default function HouseholdPage() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [verify, setVerify] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [draft, setDraft] = useState(null);
  const [fields, setFields] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([api.summary(id), api.verify(id), api.claimDraft(id), household.timeline(id)])
      .then(([s, v, d, t]) => {
        if (!active) return;
        setSummary(s);
        setVerify(v);
        setTimeline(t || []);
        setDraft(d);
        setFields(d ? d.fields : []);
      })
      .catch((e) => active && setMessage(e.message));
    return () => { active = false; };
  }, [id, reloadKey]);

  async function changeStatus(status) {
    const name = getAgentName();
    if (!name) return;
    await api.setStatus(id, status, name);
    setMessage(`Marked as ${STATUS_LABELS[status]}.`);
  }

  async function generateDraft() {
    setBusy(true);
    try {
      const d = await api.createClaimDraft(id);
      setDraft(d);
      setFields(d.fields);
    } catch (e) {
      setMessage(e.message);
    }
    setBusy(false);
  }

  async function review(status) {
    const name = getAgentName();
    if (!name) return;
    await api.reviewClaim(draft.id, status, name, fields);
    setReloadKey((k) => k + 1);
    setMessage(`Claim ${status} by ${name}.`);
  }

  function editField(i, value) {
    setFields(fields.map((f, j) => (j === i ? { ...f, value } : f)));
  }

  if (!summary) return <p>{message || "Loading..."}</p>;

  return (
    <>
      <Link to="/queue" className="back">← Call queue</Link>
      <div className="page-head">
        <div>
          <div className="eyebrow">{summary.device_id}</div>
          <h1>{summary.address || `Household ${id}`}</h1>
          {verify && (
            <span className={`badge ${verify.status === "verified" ? "ok" : "sev-critical"}`}>
              {verify.status === "verified"
                ? `Evidence verified · ${verify.readings_checked} readings`
                : `Tampered at reading ${verify.first_bad_counter}`}
            </span>
          )}
        </div>
        <div className="actions">
          <button className="btn" onClick={() => changeStatus("contacted")}>Contacted</button>
          <button className="btn" onClick={() => changeStatus("needs_follow_up")}>Needs follow-up</button>
          <button className="btn primary" onClick={() => changeStatus("resolved")}>Resolved</button>
        </div>
      </div>
      {message && <div className="notice">{message}</div>}

      <section className="card timeline-card">
        <div className="card-header">
          <span className="label">Indoor temperature during the outage ›</span>
          <span className="muted">{summary.outage_hours} hours without power</span>
        </div>
        <div className="card-body">
          <AreaChart points={timeline.filter((p) => p.temp != null).map((p) => ({ value: p.temp }))} />
          <div className="power-strip">
            {timeline.map((p, i) => (
              <span key={i} className={p.powerOn ? "on" : "off"} title={p.powerOn ? "Power on" : "Power out"} />
            ))}
          </div>
          <div className="legend"><span className="sw off" /> Power out <span className="sw on" /> Power on</div>
        </div>
      </section>

      <div className="grid">
        <section className="card">
          <h2>Outage record</h2>
          <dl className="facts">
            <dt>Power out</dt><dd>{fmt(summary.outage_start)}</dd>
            <dt>Power back</dt><dd>{fmt(summary.outage_end)}</dd>
            <dt>Outage length</dt><dd>{summary.outage_hours} hours</dd>
            <dt>Lowest indoor temp</dt><dd>{summary.min_temp != null ? `${Math.round(summary.min_temp)}°F` : "—"}</dd>
            <dt>Hours below 55°F</dt><dd>{summary.cold_hours}</dd>
            <dt>Asked for a call</dt><dd>{summary.call_requested ? "Yes" : "No"}</dd>
            <dt>Photo consent</dt><dd>{summary.photo_consent ? "Yes" : "No"}</dd>
          </dl>
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Claim draft</h2>
            {draft && <span className="badge neutral">{draft.status.replace("_", " ")}</span>}
          </div>
          {!draft && (
            <button className="btn primary" disabled={busy} onClick={generateDraft}>
              {busy ? "Drafting..." : "Generate claim draft"}
            </button>
          )}
          {draft && (
            <>
              <p className="summary">{draft.summary}</p>
              {fields.map((f, i) => (
                <div key={i} className="field">
                  <label>
                    {f.name}
                    <span className={`src src-${f.source}`}>{SOURCE_LABELS[f.source] || f.source}</span>
                  </label>
                  <input value={f.value ?? ""} onChange={(e) => editField(i, e.target.value)}
                    disabled={draft.status !== "pending_review"} />
                </div>
              ))}
              <h3>Ask the customer</h3>
              <ul className="checklist">
                {draft.questions.map((q) => (
                  <li key={q}><label><input type="checkbox" /> {q}</label></li>
                ))}
              </ul>
              {draft.status === "pending_review" ? (
                <div className="actions">
                  <button className="btn" onClick={() => review("rejected")}>Reject</button>
                  <button className="btn primary" onClick={() => review("approved")}>Approve</button>
                </div>
              ) : (
                <p className="muted">Reviewed by {draft.reviewed_by}</p>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
