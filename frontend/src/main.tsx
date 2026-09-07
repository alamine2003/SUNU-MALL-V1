import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./index.css";

const CHUNK_RELOAD_KEY = "sunu-mall:stale-chunk";

window.addEventListener("vite:preloadError", (event) => {
  const failedChunk = event.payload.message;
  if (sessionStorage.getItem(CHUNK_RELOAD_KEY) === failedChunk) return;

  event.preventDefault();
  sessionStorage.setItem(CHUNK_RELOAD_KEY, failedChunk);

  const refreshedUrl = new URL(window.location.href);
  refreshedUrl.searchParams.set("app-reload", Date.now().toString());
  window.location.replace(refreshedUrl);
});

window.addEventListener("load", () => {
  sessionStorage.removeItem(CHUNK_RELOAD_KEY);

  const refreshedUrl = new URL(window.location.href);
  if (!refreshedUrl.searchParams.has("app-reload")) return;

  refreshedUrl.searchParams.delete("app-reload");
  window.history.replaceState(window.history.state, "", refreshedUrl);
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
