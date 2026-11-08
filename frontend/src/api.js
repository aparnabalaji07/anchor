const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  queue: () => request("/queue"),
  summary: (id) => request(`/households/${id}/summary`),
  verify: (id) => request(`/households/${id}/verify`),
  setStatus: (id, status, updatedBy) =>
    request(`/households/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, updated_by: updatedBy }),
    }),
  claimDraft: (id) => request(`/households/${id}/claim-draft`),
  createClaimDraft: (id) =>
    request(`/households/${id}/claim-draft`, { method: "POST" }),
  reviewClaim: (draftId, status, reviewedBy, fields) =>
    request(`/claim-drafts/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, reviewed_by: reviewedBy, fields }),
    }),
};

export function severity(score) {
  if (score >= 70) return { label: "Critical", cls: "sev-critical" };
  if (score >= 45) return { label: "High", cls: "sev-high" };
  if (score >= 20) return { label: "Moderate", cls: "sev-moderate" };
  return { label: "Low", cls: "sev-low" };
}

export const STATUS_LABELS = {
  not_contacted: "Not contacted",
  contacted: "Contacted",
  needs_follow_up: "Needs follow-up",
  resolved: "Resolved",
};

export function getAgentName() {
  let name = localStorage.getItem("agentName");
  if (!name) {
    name =
      window.prompt("Your name (shown on status changes and approvals):") || "";
    if (name) localStorage.setItem("agentName", name);
  }
  return name;
}
