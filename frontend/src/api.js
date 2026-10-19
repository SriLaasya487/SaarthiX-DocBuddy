import { cacheGet, cacheSet, enqueue, flush, toOp } from "./offline.js";
import { demoCall } from "./demo.js";
import { setDomLanguage } from "./domtranslate.js";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
// Demo mode: no backend needed. On the live site it is on automatically when VITE_API_URL is not set.
export const isDemo = import.meta.env.VITE_DEMO === "true" || (import.meta.env.PROD && !import.meta.env.VITE_API_URL);
let token = localStorage.getItem("db_token") || "";

export const setToken = (t) => { token = t; t ? localStorage.setItem("db_token", t) : localStorage.removeItem("db_token"); };
export const hasToken = () => !!token;
const NOCACHE = /^\/(me\/export|.*\/(file|audio))/;

// remember the chosen language so every screen can be shown in it
function noteLanguage(method, path, body, data) {
  try {
    if (path === "/me" && method === "GET" && data?.language) setDomLanguage(data.language);
    else if (path === "/me" && method === "PATCH" && body?.language) setDomLanguage(body.language);
    else if (path === "/auth/verify" && data?.user?.language) setDomLanguage(data.user.language);
  } catch { /* never block the app */ }
}

async function call(method, path, body) {
  if (isDemo) { const d = await demoCall(method, path, body, token); noteLanguage(method, path, body, d); return d; }
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {                                 // network is down
    if (method === "GET") { const c = cacheGet(path); if (c !== null) return c; }
    const op = toOp(method, path, body);
    if (op) { enqueue(op); return { queued: true, offline: true }; }
    throw new Error("You are offline. Please try again when the network is back.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  const data = await res.json();
  noteLanguage(method, path, body, data);
  if (method === "GET" && !NOCACHE.test(path)) cacheSet(path, data);
  return data;
}
export const api = {
  get: (p) => call("GET", p),
  post: (p, b) => call("POST", p, b || {}),
  put: (p, b) => call("PUT", p, b),
  patch: (p, b) => call("PATCH", p, b),
  del: (p) => call("DELETE", p),
  // authenticated download (audio / printable pages) -> blob URL
  blob: async (p) => {
    if (isDemo) return URL.createObjectURL(new Blob(["<h2>AarogyaSaathi</h2><p>Printable page (demo).</p>"], { type: "text/html" }));
    const r = await fetch(BASE + p, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    return URL.createObjectURL(await r.blob());
  },
};
export const syncNow = () => (isDemo ? Promise.resolve(0) : flush(api.post).catch(() => 0));
window.addEventListener("online", syncNow);

