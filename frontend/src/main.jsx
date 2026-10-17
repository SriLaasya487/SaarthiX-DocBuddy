import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import { restoreSettings } from "./a11y.js";
restoreSettings();
if ("serviceWorker" in navigator && import.meta.env.PROD) navigator.serviceWorker.register("/sw.js").catch(() => {});
createRoot(document.getElementById("root")).render(<App />);
