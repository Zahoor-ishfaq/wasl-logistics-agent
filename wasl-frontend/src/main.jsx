import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import Login from "./Login.jsx";

function Root() {
  const [authed, setAuthed] = useState(false);
  return authed ? <App /> : <Login onSuccess={() => setAuthed(true)} />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);