const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The signed-in agent lives in sessionStorage, so closing the tab signs them out
const SESSION_KEY = "anchorSession";

export function getSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    return s?.token ? s : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

export async function login(email, password) {
  let res;
  try {
    res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error("Can't reach the server. Make sure the backend is running.");
  }
  if (res.status === 401) throw new Error("Wrong email or password.");
  if (!res.ok) throw new Error("Could not sign in. Try again in a moment.");
  const { token, name, email: agentEmail } = await res.json();
  const session = { token, name, email: agentEmail };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

async function authFetch(path, options = {}) {
  const token = getSession()?.token;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    // Missing or expired token: start over at the sign-in page
    clearSession();
    window.location.assign(`${import.meta.env.BASE_URL}login`);
    throw new Error("Signed out");
  }
  return res;
}

async function request(path, options = {}) {
  const res = await authFetch(path, options);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  queue: () => request("/queue"),
  summary: (id) => request(`/households/${id}/summary`),
  verify: (id) => request(`/households/${id}/verify`),
  setStatus: (id, status) =>
    request(`/households/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  claimDraft: (id) => request(`/households/${id}/claim-draft`),
  createClaimDraft: (id) => request(`/households/${id}/claim-draft`, { method: "POST" }),
  reviewClaim: (draftId, status, fields) =>
    request(`/claim-drafts/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, fields }),
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

export const extra = {
  stats: () => request("/stats"),
  generateReasons: (limit = 15) => request(`/ai/reasons?limit=${limit}`, { method: "POST" }),
  brief: () => request("/ai/brief"),
  createBrief: () => request("/ai/brief", { method: "POST" }),
};

export const household = {
  timeline: (id) => request(`/households/${id}/timeline`),
};

export const photos = {
  list: (householdId) => request(`/households/${householdId}/photos`),
  analyze: (photoId) => request(`/photos/${photoId}/analyze`, { method: "POST" }),
  // Images need the auth header, so they are fetched as blobs instead of <img src>
  image: async (photoId) => {
    const res = await authFetch(`/photos/${photoId}/image`);
    if (!res.ok) throw new Error(`Could not load photo ${photoId}`);
    return res.blob();
  },
};
