import { lazy, Suspense, useState, useEffect, useCallback } from "react";
import { TRANSLATIONS } from "../i18n.js";
import { t as tr } from "../translate.js";
import { api, syncNow } from "../api.js";
import { applySettings, attention } from "../a11y.js";
import { scheduleDoseAlarms } from "../offline.js";
import { speak, hearAgain, slowDown, canListen, listen, voiceNav, loadLexicon } from "../voice.js";

import SosButton from "./SosButton.jsx";
import FallGuard from "./FallGuard.jsx";
import CheckIn from "./CheckIn.jsx";
import Medicines from "./Medicines.jsx";
import Doctor from "./Doctor.jsx";
import Sharing from "./Sharing.jsx";
import Health from "./Health.jsx";
import Pending from "./Pending.jsx";

const Records = lazy(() => import("./Records.jsx"));
const Companion = lazy(() => import("./Companion.jsx"));
const SafetyHub = lazy(() => import("./SafetyHub.jsx"));
const Daily = lazy(() => import("./Daily.jsx"));
const Community = lazy(() => import("./Community.jsx"));
const Settings = lazy(() => import("./Settings.jsx"));

export default function ElderApp({ user: u0, onLogout }) {
  const [user, setUser] = useState(u0);
  const [view, setView] = useState("home");
  const [home, setHome] = useState(null);
  const [fine, setFine] = useState(null);      // the message waiting for "Yes, send it"
  const [fineSent, setFineSent] = useState(false);
  const [fineErr, setFineErr] = useState("");
  const [call, setCall] = useState(null);      // incoming video call
  const [alarm, setAlarm] = useState(null);    // medicine time reached
  const [navModal, setNavModal] = useState(false);
  const [listening, setListening] = useState(false);
  const [spokenFeedback, setSpokenFeedback] = useState("");

  const lang = user.language || "en-IN";
  const t = TRANSLATIONS[lang] || TRANSLATIONS["en-IN"];
  const due = home?.due || [];

  // text size, dialect words, and any actions saved while offline
  useEffect(() => { applySettings(u0.settings || {}); loadLexicon(api.get); syncNow(); }, []);

  // one small request feeds the home screen (and is cached for offline use)
  const refresh = useCallback(() => api.get("/lite/home").then((h) => {
    setHome(h);
    scheduleDoseAlarms(h.medicines, (d) => { attention(); speak(tr("Time for {name}. Tap I took it when done.", lang, { name: d.name }), lang); setAlarm(d); });
  }).catch(() => {}), [lang]);
  useEffect(() => { refresh(); const id = setInterval(refresh, 60000); return () => clearInterval(id); }, [view, refresh]);

  // family video calls ring here
  useEffect(() => {
    const id = setInterval(() => api.get("/video/incoming").then((v) => { if (v[0]) { setCall((c) => c || v[0]); attention(); } }).catch(() => {}), 15000);
    return () => clearInterval(id);
  }, []);

  // spoken greeting when the home screen opens
  useEffect(() => {
    if (view !== "home" || !home) return;
    const parts = [tr("Namaste {name}.", lang, { name: user.name || "" }), due.length ? tr("You have {n} medicine(s) to take.", lang, { n: due.length }) : tr("Everything is on track.", lang)];
    speak(parts.join(" "), lang);
    if (due.length) attention();
  }, [view, !!home, due.length, lang]);

  const bump = (d) => {
    let s = {}; try { s = JSON.parse(localStorage.getItem("db_a11y")) || {}; } catch { /* none */ }
    s.font_scale = Math.min(2, Math.max(1, +((s.font_scale || 1) + d).toFixed(1)));
    applySettings(s); api.put("/settings", { font_scale: s.font_scale }).catch(() => {});
  };

  // "Go to..." navigation: speech recognition + visual fallback modal
  const openVoiceNavigation = async () => {
    setNavModal(true);
    setSpokenFeedback("");
    speak(t.goToModalTitle || "Where would you like to go?", lang);
    if (canListen()) {
      setListening(true);
      try {
        const query = await listen(lang);
        if (query) {
          setSpokenFeedback(`"${query}"`);
          const matchedRoute = voiceNav(query);
          if (matchedRoute) {
            setNavModal(false);
            setListening(false);
            setView(matchedRoute);
            speak(`Opening ${t.tiles[matchedRoute] || matchedRoute}`, lang);
            return;
          }
        }
      } catch (e) {
        // the buttons stay open as a fallback
      }
      setListening(false);
    }
  };

  const handleTileClick = (route) => { setNavModal(false); setView(route); };

  // "Tell my family I am fine": the server drafts it, the senior says yes, then it is sent
  const askFine = async () => {
    setFineErr("");
    try {
      const d = await api.post("/imfine");
      if (d.draft) { setFine(d); speak(d.speak || d.draft, lang); } else { setFineSent(true); speak(t.fineSentMsg, lang); }
    } catch (e) { setFineErr(e.message); }
  };
  const sendFine = async () => {
    try { await api.post("/imfine?approve=true"); setFine(null); setFineSent(true); speak(t.fineSentMsg, lang); setTimeout(() => setFineSent(false), 6000); }
    catch (e) { setFineErr(e.message); }
  };
  const answerCall = async () => { try { const r = await api.post(`/video/${call.id}`, { accept: true }); window.open(r.room_url, "_blank"); } catch { /* ignore */ } setCall(null); };
  const declineCall = async () => { try { await api.post(`/video/${call.id}`, { accept: false }); } catch { /* ignore */ } setCall(null); };

  const TILES = [
    { id: "checkin", label: t.tiles.checkin, icon: "🌸", bg: "var(--rose-subtle)", color: "var(--rose-hover)" },
    { id: "meds", label: t.tiles.meds, icon: "💊", bg: "var(--peach-pastel)", color: "var(--peach-ink)", badge: due.length },
    { id: "health", label: t.tiles.health, icon: "🩺", bg: "var(--sky-pastel)", color: "var(--sky-ink)" },
    { id: "sharing", label: t.tiles.sharing, icon: "🛡️", bg: "var(--sage-pastel)", color: "var(--sage-ink)" },
    { id: "records", label: t.tiles.records, icon: "📋", bg: "var(--card-soft)", color: "var(--rose-primary)" },
    { id: "doctor", label: t.tiles.doctor, icon: "📞", bg: "var(--sky-pastel)", color: "var(--sky-ink)" },
    { id: "companion", label: t.tiles.companion, icon: "🌺", bg: "var(--lavender-pastel)", color: "var(--lavender-ink)", badge: home?.unread_messages || 0 },
    { id: "safety", label: t.tiles.safety, icon: "🔍", bg: "var(--rose-subtle)", color: "var(--rose-hover)" },
    { id: "daily", label: t.tiles.daily, icon: "📜", bg: "var(--peach-pastel)", color: "var(--peach-ink)" },
    { id: "community", label: t.tiles.community, icon: "🤝", bg: "var(--sage-pastel)", color: "var(--sage-ink)" },
    { id: "pending", label: t.tiles.pending, icon: "🔔", bg: "var(--rose-subtle)", color: "var(--rose-hover)", badge: home?.pending || 0 },
    { id: "settings", label: t.tiles.settings, icon: "⚙️", bg: "var(--card-soft)", color: "var(--ink-muted)" },
  ];

  return (
    <div className="app-shell">
      <header className="clean-header">
        <div className="clean-brand">
          <span>🌸</span>
          <span>{t.brandName}</span>
        </div>
        <div className="header-actions">
          <button className="header-btn" onClick={() => bump(-0.1)} aria-label="Smaller text">A−</button>
          <button className="header-btn" onClick={() => bump(0.1)} aria-label="Bigger text"><b>A+</b></button>
          <button className="header-btn" onClick={hearAgain} title="Hear voice again">{t.repeatBtn}</button>
          <button className="header-btn" onClick={slowDown} title="Slow down speaking rate">{t.slowBtn}</button>
          <button className="header-btn" style={{ background: "var(--rose-primary)", color: "#fff" }} onClick={openVoiceNavigation}>{t.goToBtn}</button>
          <button className="header-btn" onClick={onLogout}>Sign out</button>
        </div>
      </header>

      <FallGuard lang={lang} />

      {call && (
        <div className="modal-overlay">
          <div className="modal-card" role="alertdialog" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "3rem" }}>📹</div>
            <h2 style={{ margin: 0 }}>{call.from} {tr("is calling you", lang)}</h2>
            <button className="big-action sage-filled" onClick={answerCall}>{tr("Answer", lang)}</button>
            <button className="big-action" onClick={declineCall}>{tr("Not now", lang)}</button>
          </div>
        </div>
      )}
      {alarm && (
        <div className="modal-overlay">
          <div className="modal-card" role="alertdialog" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "3rem" }}>💊</div>
            <h2 style={{ margin: 0 }}>{tr("Time for {name}.", lang, { name: alarm.name })}</h2>
            <button className="big-action sage-filled" onClick={() => { setAlarm(null); setView("meds"); }}>{tr("Open medicines", lang)}</button>
            <button className="big-action" onClick={() => setAlarm(null)}>{tr("Later", lang)}</button>
          </div>
        </div>
      )}

      <main className="main-content">
        {view === "home" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.8rem" }}>
              <h1 style={{ fontSize: "2.1rem", margin: 0, color: "var(--ink)" }}>
                {t.greeting}, {user.name || "friend"}
              </h1>
              <span style={{ fontSize: "0.95rem", color: "var(--ink-muted)", fontWeight: 700 }}>
                {lang.split("-")[0].toUpperCase()}
              </span>
            </div>

            {/* Medicines that are due right now (real data) */}
            {due.length > 0 && (
              <div
                onClick={() => setView("meds")}
                style={{ background: "var(--peach-pastel)", border: "2px solid var(--peach-border)", borderRadius: "var(--radius-md)", padding: "1.1rem 1.25rem", marginBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div>
                  <b style={{ color: "var(--peach-ink)", fontSize: "1.15rem" }}>💊 {t.tiles.meds}</b>
                  <p style={{ margin: "0.2rem 0 0", color: "var(--ink-muted)", fontSize: "0.95rem" }}>
                    {due[0].name} · {due[0].tablets} · {due[0].slot}{due.length > 1 ? ` · ${tr("{n} more", lang, { n: due.length - 1 })}` : ""}
                  </p>
                </div>
                <span style={{ fontWeight: 800, color: "var(--peach-ink)" }}>{tr("Open →", lang)}</span>
              </div>
            )}
            {home && !due.length && !(home.medicines || []).length && (
              <div
                onClick={() => setView("meds")}
                style={{ background: "var(--peach-pastel)", border: "2px dashed var(--peach-border)", borderRadius: "var(--radius-md)", padding: "1.1rem 1.25rem", marginBottom: "1rem", cursor: "pointer", fontWeight: 800, color: "var(--peach-ink)" }}
              >
                ➕ {tr("Add your first medicine", lang)} →
              </div>
            )}
            {(home?.appointments || []).map((a) => (
              <div key={a.id} className="card" style={{ marginBottom: "0.8rem", cursor: "pointer" }} onClick={() => setView("health")}><p>🩺 {a.speak}</p></div>
            ))}
            {(home?.reminders || []).map((r, i) => <div key={i} className="card good" style={{ marginBottom: "0.8rem" }}><p>🎉 {r.say}</p></div>)}

            {/* Pastel Action Tiles */}
            <div className="tiles-grid">
              {TILES.map((tile) => (
                <button
                  key={tile.id}
                  className="pastel-tile"
                  style={{ background: tile.bg, borderColor: tile.bg }}
                  onClick={() => handleTileClick(tile.id)}
                >
                  <span className="tile-icon" aria-hidden="true">{tile.icon}</span>
                  <span style={{ color: tile.color }}>{tile.label}</span>
                  {tile.badge > 0 && (
                    <span style={{ position: "absolute", top: 10, right: 10, background: "var(--rose-primary)", color: "#fff", fontSize: "0.75rem", fontWeight: 800, padding: "0.15rem 0.5rem", borderRadius: "var(--radius-full)" }}>
                      {tile.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tell Family I Am Fine */}
            <div style={{ marginTop: "1.5rem" }}>
              {!fine && <button className="big-action sage-filled" onClick={askFine}>{t.tellFineBtn}</button>}
              {fine && (
                <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
                  <p style={{ margin: 0 }}>{fine.draft}</p>
                  <button className="big-action sage-filled" onClick={sendFine}>{tr("Yes, send it", lang)}</button>
                  <button className="big-action" onClick={() => setFine(null)}>{tr("No", lang)}</button>
                </div>
              )}
              {fineErr && <p className="error" style={{ textAlign: "center" }}>{fineErr}</p>}
              {fineSent && (
                <p style={{ textAlign: "center", color: "var(--sage-ink)", fontWeight: 700, marginTop: "0.6rem" }}>✔ {t.fineSentMsg}</p>
              )}
            </div>
          </div>
        )}

        {view !== "home" && (
          <div>
            <button
              onClick={() => setView("home")}
              style={{ background: "none", border: "none", color: "var(--rose-primary)", fontWeight: 800, fontSize: "1.1rem", padding: "0.4rem 0 0.8rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
            >
              {t.backBtn || "← Back"}
            </button>

            <Suspense fallback={<p style={{ textAlign: "center" }}>Loading…</p>}>
              {view === "checkin" && <CheckIn lang={lang} onDone={() => setView("home")} />}
              {view === "meds" && <Medicines lang={lang} onPending={refresh} />}
              {view === "health" && <Health lang={lang} />}
              {view === "sharing" && <Sharing lang={lang} />}
              {view === "records" && <Records lang={lang} onPending={refresh} />}
              {view === "doctor" && <Doctor lang={lang} />}
              {view === "companion" && <Companion lang={lang} />}
              {view === "safety" && <SafetyHub lang={lang} />}
              {view === "daily" && <Daily lang={lang} />}
              {view === "community" && <Community lang={lang} />}
              {view === "pending" && <Pending lang={lang} onChange={refresh} />}
              {view === "settings" && <Settings lang={lang} user={user} onUser={setUser} />}
            </Suspense>
          </div>
        )}
      </main>

      {/* "Go To..." Voice Navigation Modal with Visual Fallback */}
      {navModal && (
        <div className="modal-overlay" onClick={() => setNavModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "2.4rem" }}>🎙️</span>
              <h2 style={{ margin: "0.4rem 0 0.2rem", fontSize: "1.5rem" }}>{t.goToModalTitle}</h2>
              <p style={{ color: "var(--ink-muted)", fontSize: "0.95rem", margin: 0 }}>{listening ? t.navListening : t.goToModalSub}</p>
              {spokenFeedback && (
                <p style={{ color: "var(--rose-primary)", fontWeight: 700, margin: "0.4rem 0 0" }}>Heard: {spokenFeedback}</p>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.6rem", maxHeight: "40vh", overflowY: "auto" }}>
              {TILES.map((tile) => (
                <button
                  key={tile.id}
                  onClick={() => handleTileClick(tile.id)}
                  style={{ padding: "0.8rem 0.6rem", borderRadius: "var(--radius-sm)", border: "1.5px solid var(--line)", background: tile.bg, color: tile.color, fontWeight: 700, fontSize: "0.95rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem" }}
                >
                  <span>{tile.icon}</span>
                  <span style={{ textAlign: "left" }}>{tile.label}</span>
                </button>
              ))}
            </div>

            <button className="big-action" onClick={() => setNavModal(false)}>{tr("Close", lang)}</button>
          </div>
        </div>
      )}

      <SosButton lang={lang} />
    </div>
  );
}
