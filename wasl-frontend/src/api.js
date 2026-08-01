// src/api.js
// The single place that talks to the FastAPI backend.
// Every request goes through /api (proxied to :8000 by Vite in dev)
// and carries the X-API-Key header.
//
// The key is provided at runtime via the login screen (setApiKey), held
// in memory only — not baked into the build, not written to disk.

let API_KEY = "";

export function setApiKey(key) {
  API_KEY = key || "";
}

export function hasApiKey() {
  return Boolean(API_KEY);
}

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// Verify a key by calling a protected endpoint. Returns true if accepted.
export async function verifyApiKey(key) {
  const prev = API_KEY;
  API_KEY = key || "";
  try {
    // /documents requires the key; a 200 means the key is valid.
    await request("/shipments");
    return true;
  } catch (e) {
    API_KEY = prev; // roll back on failure
    if (e.status === 401) return false;
    // Non-auth error (e.g. server down) — surface it.
    throw e;
  }
}

// ---- Health ---------------------------------------------------------------
export const getHealth = () => request("/health");
// ---- Shipments ------------------------------------------------------------
export const listShipments = () => request("/shipments");

// ---- Ask (RAG) ------------------------------------------------------------
export const ask = (text, topK = 5) =>
  request("/answer", { method: "POST", body: { text, top_k: topK } });

// ---- Investigations (agent) ----------------------------------------------
export const startInvestigation = (shipmentId) =>
  request("/investigations", { method: "POST", body: { shipment_id: shipmentId } });

export const decideInvestigation = (investigationId, approved) =>
  request(`/investigations/${investigationId}/approve`, {
    method: "POST",
    body: { approved },
  });

// ---- Documents ------------------------------------------------------------
export const listDocuments = () => request("/documents");

// Upload a document (multipart). Sends the API key header, no JSON content-type.
export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api/documents/upload`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
    body: form,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch { /* ignore */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}