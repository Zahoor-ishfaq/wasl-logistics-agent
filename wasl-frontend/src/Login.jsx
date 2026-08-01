// src/Login.jsx
// JWT login screen. The access token is kept in memory by api.js.

import { useState } from "react";
import { login } from "./api";

const NAVY = "#0C1C2E";
const AMBER = "#D9971E";

export default function Login({ onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!username.trim() || !password) {
      setErr("Enter your username and password.");
      return;
    }

    setBusy(true);
    setErr("");

    try {
      await login(username.trim(), password);
      onSuccess();
    } catch (e) {
      if (e.status === 401) {
        setErr("Invalid username or password.");
      } else {
        setErr("Could not reach the server. Is the backend running?");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "#F4F5F3",
      fontFamily: "Inter, system-ui, sans-serif",
    }}>
      <div style={{
        width: 360, background: "#fff", borderRadius: 14,
        border: "1px solid #E4E7E4", padding: 32,
        boxShadow: "0 8px 30px rgba(12,28,46,0.08)",
      }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
          <svg width="56" height="56" viewBox="0 0 512 512">
            <rect width="512" height="512" rx="112" fill={NAVY} />
            <path
              d="M150 362 Q256 362 256 256 Q256 150 362 150"
              fill="none"
              stroke={AMBER}
              strokeWidth="26"
              strokeLinecap="round"
            />
            <circle cx="150" cy="362" r="34" fill={NAVY} stroke={AMBER} strokeWidth="20" />
            <circle cx="362" cy="150" r="30" fill={AMBER} />
            <circle cx="256" cy="256" r="16" fill="#F4F1EA" />
          </svg>
        </div>

        <div style={{
          textAlign: "center", marginBottom: 4,
          fontSize: 22, fontWeight: 700, color: NAVY,
        }}>
          Wasl
        </div>

        <div style={{
          textAlign: "center", marginBottom: 24,
          fontSize: 12, letterSpacing: 2,
          color: "#8A96A2", fontWeight: 600,
        }}>
          CONTROL TOWER
        </div>

        <label style={{ fontSize: 12, fontWeight: 600, color: "#5E6B78" }}>
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter your username"
          autoComplete="username"
          autoFocus
          style={{
            width: "100%", marginTop: 6, marginBottom: 14,
            padding: "11px 12px", border: "1px solid #D8DDD8",
            borderRadius: 8, fontSize: 14, boxSizing: "border-box",
            outline: "none",
          }}
        />

        <label style={{ fontSize: 12, fontWeight: 600, color: "#5E6B78" }}>
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Enter your password"
          autoComplete="current-password"
          style={{
            width: "100%", marginTop: 6, marginBottom: 14,
            padding: "11px 12px", border: "1px solid #D8DDD8",
            borderRadius: 8, fontSize: 14, boxSizing: "border-box",
            outline: "none",
          }}
        />

        {err && (
          <div style={{ marginBottom: 14, fontSize: 12.5, color: "#C0392B" }}>
            {err}
          </div>
        )}

        <button
          onClick={submit}
          disabled={busy}
          style={{
            width: "100%", padding: 12,
            background: busy ? "#B8842A" : AMBER,
            color: "#fff", border: "none", borderRadius: 8,
            fontSize: 14, fontWeight: 600,
            cursor: busy ? "default" : "pointer",
          }}
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </div>
    </div>
  );
}