import { cacheGet, cacheSet, enqueue, flush, toOp } from "./offline.js";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
let token = localStorage.getItem("db_token") || "";

export const setToken = (t) => { token = t; t ? localStorage.setItem("db_token", t) : localStorage.removeItem("db_token"); };
export const hasToken = () => !!token;
const NOCACHE = /^\/(me\/export|.*\/(file|audio))/;

async function call(method, path, body) {
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
    const r = await fetch(BASE + p, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    return URL.createObjectURL(await r.blob());
  },
};
export const syncNow = () => flush(api.post).catch(() => 0);
window.addEventListener("online", syncNow);
