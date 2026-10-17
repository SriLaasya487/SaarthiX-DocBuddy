// DB-074: offline-first. GET results are cached; a few write actions are queued and replayed to /sync/batch
// with their ORIGINAL timestamps (server de-duplicates by client_id). Dose alarms are scheduled on the phone itself.
const QK = "db_queue";
export const cacheSet = (p, v) => { try { localStorage.setItem("dbc:" + p, JSON.stringify(v)); } catch { /* quota */ } };
export const cacheGet = (p) => { try { return JSON.parse(localStorage.getItem("dbc:" + p)); } catch { return null; } };

export function toOp(method, path, body = {}) {
  if (method !== "POST") return null;
  let m;
  if ((m = path.match(/^\/medicines\/(\d+)\/taken$/))) return { op: "dose_taken", data: { medicine_id: +m[1], slot: body.slot } };
  if (path === "/checkin") return { op: "checkin", data: body };
  if (path === "/vitals") return { op: "vital", data: body };
  if (path === "/symptoms") return { op: "symptom", data: body };
  if (path === "/activity") return { op: "activity", data: body };
  return null;
}
const read = () => { try { return JSON.parse(localStorage.getItem(QK)) || []; } catch { return []; } };
export const pendingCount = () => read().length;
export function enqueue(o) {
  const q = read();
  q.push({ client_id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()), at: new Date().toISOString().replace("Z", ""), ...o });
  localStorage.setItem(QK, JSON.stringify(q));
}
export async function flush(post) {
  const q = read();
  if (!q.length) return 0;
  const r = await post("/sync/batch", { ops: q });
  localStorage.setItem(QK, "[]");   // ok + duplicate are done; rejected ops can never succeed, so they are dropped too
  return r.results.length;
}

// Local dose alarms: work with no network while the app is open/installed. (True background alarms need a native/push layer.)
let timers = [];
export function scheduleDoseAlarms(meds, onDue) {
  timers.forEach(clearTimeout); timers = [];
  const now = new Date();
  for (const m of meds || []) for (const slot of String(m.times).split(",")) {
    const [h, mi] = slot.split(":").map(Number);
    const at = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, mi) - now;
    if (at > 0 && at < 864e5) timers.push(setTimeout(() => onDue({ name: m.name, slot, tablets: m.tablets }), at));
  }
}
