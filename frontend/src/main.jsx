import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import { restoreSettings } from "./a11y.js";
import { startDomTranslate } from "./domtranslate.js";
restoreSettings();
if ("serviceWorker" in navigator && import.meta.env.PROD)
  navigator.serviceWorker
    .register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL })
    .catch(() => {});
createRoot(document.getElementById("root")).render(<App />);
startDomTranslate();

