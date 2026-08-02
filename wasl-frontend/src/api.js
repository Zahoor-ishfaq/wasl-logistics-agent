// src/api.js
// Single frontend API client.
// Browser authentication uses an in-memory JWT.
// X-API-Key support remains available for backwards compatibility.

let ACCESS_TOKEN = "";
let API_KEY = "";

export function setAccessToken(token) {
  ACCESS_TOKEN = token || "";
}

export function hasAccessToken() {
  return Boolean(ACCESS_TOKEN);
}

export function logout() {
  ACCESS_TOKEN = "";
}

export function setApiKey(key) {
  API_KEY = key || "";
}

export function hasApiKey() {
  return Boolean(API_KEY);
}

function formatErrorDetail(detail, fallback) {
  if (!detail) {
    return fallback;
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          const location = Array.isArray(item.loc)
            ? item.loc
                .filter((part) => part !== "body")
                .join(".")
            : "";

          const message =
            item.msg ||
            item.message ||
            "Invalid request";

          return location
            ? `${location}: ${message}`
            : message;
        }

        return String(item);
      })
      .filter(Boolean);

    return messages.join("; ") || fallback;
  }

  if (typeof detail === "object") {
    return (
      detail.message ||
      detail.msg ||
      fallback
    );
  }

  return String(detail);
}

function compactHistoryText(
  value,
  maxLength = 1200,
) {
  const text = String(
    value || "",
  ).trim();

  if (
    text.length <=
    maxLength
  ) {
    return text;
  }

  const separator =
    "\n...\n";

  const remaining =
    maxLength -
    separator.length;

  const startLength =
    Math.ceil(
      remaining / 2,
    );

  const endLength =
    Math.floor(
      remaining / 2,
    );

  return (
    text.slice(
      0,
      startLength,
    ) +
    separator +
    text.slice(
      -endLength,
    )
  );
}

async function request(
  path,
  {
    method = "GET",
    body,
    auth = true,
  } = {},
) {
  const headers = {
    "Content-Type":
      "application/json",
  };

  if (
    auth &&
    ACCESS_TOKEN
  ) {
    headers.Authorization =
      `Bearer ${ACCESS_TOKEN}`;
  } else if (
    auth &&
    API_KEY
  ) {
    headers["X-API-Key"] =
      API_KEY;
  }

  const res = await fetch(
    `/api${path}`,
    {
      method,
      headers,
      body: body
        ? JSON.stringify(body)
        : undefined,
    },
  );

  if (!res.ok) {
    let detail =
      `${res.status} ${res.statusText}`;

    try {
      const data =
        await res.json();

      detail =
        formatErrorDetail(
          data.detail,
          detail,
        );
    } catch {
      // Ignore non-JSON error bodies.
    }

    const err =
      new Error(detail);

    err.status =
      res.status;

    throw err;
  }

  if (
    res.status === 204
  ) {
    return null;
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

export async function login(
  username,
  password,
) {
  const data =
    await request(
      "/auth/login",
      {
        method: "POST",
        body: {
          username,
          password,
        },
        auth: false,
      },
    );

  setAccessToken(
    data.access_token,
  );

  return data;
}

export async function verifyApiKey(
  key,
) {
  const previous =
    API_KEY;

  API_KEY =
    key || "";

  try {
    await request(
      "/shipments",
    );

    return true;
  } catch (e) {
    API_KEY =
      previous;

    if (
      e.status === 401
    ) {
      return false;
    }

    throw e;
  }
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export const getHealth =
  () =>
    request(
      "/health",
      {
        auth: false,
      },
    );

// ---------------------------------------------------------------------------
// Shipments
// ---------------------------------------------------------------------------

export const listShipments =
  () =>
    request(
      "/shipments",
    );

// ---------------------------------------------------------------------------
// Ask / RAG
// ---------------------------------------------------------------------------

export const ask = (
  text,
  topK = 5,
  history = [],
) => {
  const safeHistory = (
    Array.isArray(history)
      ? history
      : []
  )
    .filter(
      (turn) =>
        (
          turn?.role ===
            "user" ||
          turn?.role ===
            "assistant"
        ) &&
        String(
          turn?.text ||
            "",
        ).trim(),
    )
    .slice(-4)
    .map(
      (turn) => ({
        role:
          turn.role,
        text:
          compactHistoryText(
            turn.text,
          ),
      }),
    );

  return request(
    "/answer",
    {
      method: "POST",
      body: {
        text,
        top_k:
          topK,
        history:
          safeHistory,
      },
    },
  );
};

// ---------------------------------------------------------------------------
// Investigations
// ---------------------------------------------------------------------------

export const startInvestigation =
  (shipmentId) =>
    request(
      "/investigations",
      {
        method:
          "POST",
        body: {
          shipment_id:
            shipmentId,
        },
      },
    );

export const decideInvestigation =
  (
    investigationId,
    approved,
  ) =>
    request(
      `/investigations/${investigationId}/approve`,
      {
        method:
          "POST",
        body: {
          approved,
        },
      },
    );

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export const listDocuments =
  () =>
    request(
      "/documents",
    );

export async function uploadDocument(
  file,
) {
  const form =
    new FormData();

  form.append(
    "file",
    file,
  );

  const headers = {};

  if (ACCESS_TOKEN) {
    headers.Authorization =
      `Bearer ${ACCESS_TOKEN}`;
  } else if (API_KEY) {
    headers["X-API-Key"] =
      API_KEY;
  }

  const res = await fetch(
    "/api/documents/upload",
    {
      method: "POST",
      headers,
      body: form,
    },
  );

  if (!res.ok) {
    let detail =
      `${res.status} ${res.statusText}`;

    try {
      const data =
        await res.json();

      detail =
        formatErrorDetail(
          data.detail,
          detail,
        );
    } catch {
      // Ignore non-JSON error bodies.
    }

    const err =
      new Error(detail);

    err.status =
      res.status;

    throw err;
  }

  return res.json();
}

export const deleteDocument =
  (filename) =>
    request(
      `/documents/${encodeURIComponent(
        filename,
      )}`,
      {
        method:
          "DELETE",
      },
    );