// src/pages/ElderApp.jsx
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { api, syncNow } from "../api.js";
import { applySettings, attention } from "../a11y.js";
import { pendingCount, scheduleDoseAlarms } from "../offline.js";
import { canListen, hearAgain, listen, loadLexicon, slowDown, speak, voiceNav } from "../voice.js";

import CheckIn from "./CheckIn.jsx";
import Medicines from "./Medicines.jsx";
import Doctor from "./Doctor.jsx";
import Sharing from "./Sharing.jsx";
import Health from "./Health.jsx";
import Pending from "./Pending.jsx";
import SosButton from "./SosButton.jsx";
import FallGuard from "./FallGuard.jsx";

const Records = lazy(() => import("./Records.jsx"));
const Companion = lazy(() => import("./Companion.jsx"));
const SafetyHub = lazy(() => import("./SafetyHub.jsx"));
const Assistant = lazy(() => import("./Assistant.jsx"));
const Daily = lazy(() => import("./Daily.jsx"));
const Community = lazy(() => import("./Community.jsx"));
const Settings = lazy(() => import("./Settings.jsx"));

const TILES = [
  { id: "checkin", label: "Daily check-in", icon: "☀️", color: "var(--primary-subtle)" },
  { id: "meds", label: "My medicines", icon: "💊", color: "#FDF2E9" },
  { id: "health", label: "BP, sugar & visits", icon: "🩺", color: "var(--blue-bg)" },
  { id: "sharing", label: "Who can see what", icon: "🛡️", color: "var(--ok-bg)" },
  { id: "records", label: "My records", icon: "📋", color: "var(--paper)" },
  { id: "doctor", label: "Which doctor?", icon: "📞", color: "var(--blue-bg)" },
  { id: "companion", label: "Companion", icon: "🌺", color: "var(--purple-bg)" },
  { id: "assistant", label: "Ask DocBuddy", icon: "🎙️", color: "var(--primary-subtle)" },
  { id: "safety", label: "Staying safe", icon: "🔍", color: "var(--sos-bg)" },
  { id: "daily", label: "Learn & benefits", icon: "📜", color: "var(--paper)" },
  { id: "community", label: "Friends", icon: "🤝", color: "var(--ok-bg)" },
  { id: "settings", label: "Settings", icon: "⚙️", color: "var(--paper)" },
];

export default function ElderApp({ user: u0, onLogout }) {
  const [user, setUser] = useState(u0);
  const [view, setView] = useState("home");
  const [home, setHome] = useState(null);
  const [caption, setCaption] = useState("");
  const [call, setCall] = useState(null);
  const [alarm, setAlarm] = useState(null);
  const [fine, setFine] = useState(null);
  const lang = user.language;

  useEffect(() => {
    applySettings(u0.settings || {});
    loadLexicon(api.get);
    syncNow();
  }, []);

  useEffect(() => {
    const f = (e) => {
      setCaption(e.detail);
      clearTimeout(window.__cap);
      window.__cap = setTimeout(() => setCaption(""), 9000);
    };
    window.addEventListener("db-caption", f);
    return () => window.removeEventListener("db-caption", f);
  }, []);

  const refresh = useCallback(() => api.get("/lite/home").then((h) => {
    setHome(h);
    scheduleDoseAlarms(h.medicines, (d) => {
      attention();
      speak(`Time for ${d.name}.`, lang);
      setAlarm(d);
    });
  }).catch(() => {}), [lang]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60000);
    return () => clearInterval(t);
  }, [view, refresh]);

  const due = home?.due || [];
  useEffect(() => {
    if (view !== "home" || !home) return;
    const parts = [
      `Namaste ${user.name}.`,
      due.length ? `You have ${due.length} medicine${due.length > 1 ? "s" : ""} to take.` : "Everything is on track.",
      ...(home.appointments || []).map((a) => a.speak),
      ...(home.reminders || []).map((r) => r.say),
      ...(home.nudges || []).map((n) => n.say)
    ];
    speak(parts.join(" "), lang);
    if (due.length || home.appointments?.length) attention();
  }, [view, !!home, due.length]);

  const go = (v) => setView(v);
  const Back = () => <button className="back" onClick={() => go("home")}>← Back to Home</button>;

  const sayFine = async () => {
    const d = await api.post("/imfine");
    setFine(d);
    speak(d.speak, lang);
  };

  const voiceGo = async () => {
    speak("Where would you like to go?", lang);
    await new Promise((r) => setTimeout(r, 1800));
    const t = await listen(lang).catch(() => "");
    const v = voiceNav(t);
    if (v) go(v === "home" ? "home" : v);
    else speak("I did not understand. Please tap a button.", lang);
  };

  const badge = (id) => (id === "meds" && due.length) || (id === "companion" && home?.unread_messages) || (id === "sharing" && home?.pending) ? (
    <span className="badge">{id === "meds" ? due.length : id === "companion" ? home.unread_messages : home.pending}</span>
  ) : null;
  const queued = pendingCount();

  // Hackathon demo fall trigger
  const simulateFall = () => {
    window.dispatchEvent(new CustomEvent("db-simulate-fall"));
  };

  return (
    <div className="shell">
      <header className="bar">
        <strong>🌿 DocBuddy</strong>
        <span className="tools">
          <button aria-label="Hear it again" onClick={hearAgain}>🔊 Repeat</button>
          <button aria-label="Slow down" onClick={slowDown}>🐢 Slower</button>
          {canListen() && <button aria-label="Say where to go" onClick={voiceGo}>🎙️ Go to…</button>}
          <button onClick={onLogout}>Sign out</button>
        </span>
      </header>
      
      {queued > 0 && <p className="note" style={{ padding: "0 1rem" }}>📡 {queued} item(s) saved on this phone, waiting for network.</p>}
      {home?.disaster && <p className="warn" style={{ padding: "0 1rem" }}>⚠️ <b>Extra safety mode is on.</b> <button className="back" onClick={() => go("safety")}>See guidance</button></p>}
      
      <FallGuard lang={lang} />
      
      {call && (
        <div className="modal" role="alertdialog">
          <p style={{ fontSize: "1.4rem", fontWeight: "bold" }}>📹 {call.from} is calling you</p>
          <button className="big ok" onClick={async () => {
            const r = await api.post(`/video/${call.id}`, { accept: true });
            window.open(r.room_url, "_blank");
            setCall(null);
          }}>Answer Call</button>
          <button className="big" onClick={async () => {
            await api.post(`/video/${call.id}`, { accept: false });
            setCall(null);
          }}>Not Now</button>
        </div>
      )}

      {alarm && (
        <div className="modal" role="alertdialog">
          <p style={{ fontSize: "1.3rem", fontWeight: "bold" }}>💊 Time for {alarm.name} ({alarm.tablets} tablet)</p>
          <button className="big ok" onClick={() => {
            setAlarm(null);
            go("meds");
          }}>Open Medicines</button>
          <button className="big" onClick={() => setAlarm(null)}>Remind Later</button>
        </div>
      )}

      <main className="page">
        {view === "home" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <h1>Namaste, {user.name || "friend"}</h1>
              <button onClick={simulateFall} style={{ background: "var(--sos-bg)", border: "1px dashed var(--sos)", color: "var(--sos)", padding: "0.3rem 0.6rem", borderRadius: "8px", fontSize: "0.8rem", cursor: "pointer", fontWeight: "bold" }}>
                ⚠️ Demo: Fall
              </button>
            </div>
            
            {due.length > 0 && (
              <button className="due" onClick={() => go("meds")}>
                <span>💊 <b>Medicine time:</b> {due[0].name} {due.length > 1 ? `(+${due.length - 1} more)` : ""}</span>
                <span>Open →</span>
              </button>
            )}
            
            {(home?.appointments || []).map((a) => (
              <button className="due" style={{ background: "var(--blue-bg)", borderColor: "var(--blue-soft)" }} key={a.id} onClick={() => go("health")}>
                <span>🩺 {a.speak}</span>
                <span>→</span>
              </button>
            ))}

            <div className="tiles small">
              {TILES.map((t) => (
                <button key={t.id} className="tile" style={{ background: t.color }} onClick={() => go(t.id)}>
                  <span className="ico" aria-hidden>{t.icon}</span>
                  {t.label}
                  {badge(t.id)}
                </button>
              ))}
            </div>

            {home?.pending > 0 && (
              <button className="big primary" style={{ marginTop: "1.2rem" }} onClick={() => go("pending")}>
                🔔 Please check {home.pending} item(s)
              </button>
            )}

            <button className="big ok" style={{ marginTop: "0.8rem" }} onClick={sayFine}>
              👍 Tell my family I am fine
            </button>

            {fine && fine.draft && (
              <div className="card stack" style={{ marginTop: "0.8rem" }}>
                <p>{fine.draft}</p>
                <button className="big ok" onClick={async () => {
                  const r = await api.post("/imfine?approve=true");
                  setFine(null);
                  speak(r.speak, lang);
                }}>Yes, send it</button>
                <button className="big" onClick={() => setFine(null)}>Cancel</button>
              </div>
            )}
          </>
        )}

        <Suspense fallback={<p className="note">Loading…</p>}>
          {view === "checkin" && <><Back /><CheckIn lang={lang} onDone={() => go("home")} /></>}
          {view === "meds" && <><Back /><Medicines lang={lang} onPending={refresh} /></>}
          {view === "doctor" && <><Back /><Doctor lang={lang} /></>}
          {view === "health" && <><Back /><Health lang={lang} /></>}
          {view === "records" && <><Back /><Records lang={lang} onPending={refresh} /></>}
          {view === "companion" && <><Back /><Companion lang={lang} /></>}
          {view === "assistant" && <><Back /><Assistant lang={lang} onNavigate={(r) => go(r === "sharing" ? "sharing" : r)} /></>}
          {view === "safety" && <><Back /><SafetyHub lang={lang} /></>}
          {view === "daily" && <><Back /><Daily lang={lang} /></>}
          {view === "community" && <><Back /><Community lang={lang} /></>}
          {view === "sharing" && <><Back /><Sharing lang={lang} /></>}
          {view === "pending" && <><Back /><Pending lang={lang} onChange={refresh} /></>}
          {view === "settings" && <><Back /><Settings lang={lang} user={user} onUser={setUser} /></>}
        </Suspense>
      </main>

      {caption && <div className="captions" role="status" aria-live="polite">{caption}</div>}
      <SosButton />
    </div>
  );
}
