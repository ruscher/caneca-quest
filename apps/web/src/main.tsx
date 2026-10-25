import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Offline support for the installed PWA (the desktop shell does not need it).
if (import.meta.env.PROD && "serviceWorker" in navigator && !window.__CANECA_RUNTIME__) {
  void import("virtual:pwa-register").then(({ registerSW }) => registerSW({ immediate: true }));
}
