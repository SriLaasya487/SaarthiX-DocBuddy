// DB-077 hearing/vision + DB-076 low-end phones. Applied from the server-side settings.
import { setRate } from "./voice.js";

export function isLite(s = {}) {
  if (s.lite_mode === "on") return true;
  if (s.lite_mode === "off") return false;
  const c = navigator.connection || {};
  return (navigator.deviceMemory && navigator.deviceMemory <= 2) || c.saveData || /(^|-)2g$/.test(c.effectiveType || "") || (navigator.hardwareConcurrency || 4) <= 2;
}
export function applySettings(s) {
  const r = document.documentElement;
  r.style.fontSize = 22 * (s.font_scale || 1) + "px";
  r.classList.toggle("hc", !!s.high_contrast);
  r.classList.toggle("lite", isLite(s));
  r.dataset.captions = s.captions === false ? "off" : "on";
  r.dataset.flash = s.vibrate_flash ? "on" : "off";
  if (s.speech_rate) setRate(s.speech_rate);
  localStorage.setItem("db_a11y", JSON.stringify(s));
}
export const restoreSettings = () => { try { applySettings(JSON.parse(localStorage.getItem("db_a11y")) || {}); } catch { /* first run */ } };

// Visual + vibration alert for people who cannot hear the voice prompt.
export function attention() {
  if (document.documentElement.dataset.flash !== "on") return;
  navigator.vibrate?.([300, 150, 300, 150, 600]);
  const d = document.createElement("div"); d.className = "flash"; document.body.appendChild(d);
  setTimeout(() => d.remove(), 1600);
}
export const caption = (text) => window.dispatchEvent(new CustomEvent("db-caption", { detail: text }));
