// src/api.js
// The single place that talks to the FastAPI backend.
// Every request goes through /api (proxied to :8000 by Vite in dev)
// and carries the X-API-Key header.

const API_KEY = import.meta.env.VITE_API_KEY || "";

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
    throw new Error(detail);
  }
  return res.json();
}

// ---- Health ---------------------------------------------------------------
export const getHealth = () => request("/health");

// ---- Ask (RAG) ------------------------------------------------------------
export const ask = (text, topK = 5) =>
  request("/answer", { method: "POST", body: { text, top_k: topK } });

// ---- Investigations (agent) ----------------------------------------------
export const startInvestigation = (shipmentId) =>
  request("/investigations", { method: "POST", body: { shipment_id: shipmentId } });

export const decideInvestigation = (investigationId, approved, reason = "") =>
  request(`/investigations/${investigationId}/approve`, {
    method: "POST",
    body: { approved, reason },
  });

// ---- Documents ------------------------------------------------------------
export const listDocuments = () => request("/documents");

export const uploadDocument = async (file) => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents/upload", {
    method: "POST",
    headers: { "X-API-Key": API_KEY }, // no Content-Type; browser sets multipart boundary
    body: form,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const d = await res.json();
      if (d.detail) detail = d.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
};
