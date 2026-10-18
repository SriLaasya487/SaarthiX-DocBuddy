import { lazy, Suspense, useState, useEffect } from "react";
import { TRANSLATIONS } from "../i18n.js";
import { speak, hearAgain, slowDown, canListen, listen, voiceNav } from "../voice.js";

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

export default function ElderApp({ user, onLogout }) {
  const [view, setView] = useState("home");
  const [fineSent, setFineSent] = useState(false);
  const [navModal, setNavModal] = useState(false);
  const [listening, setListening] = useState(false);
  const [spokenFeedback, setSpokenFeedback] = useState("");

  const lang = user.language || "en-IN";
  const t = TRANSLATIONS[lang] || TRANSLATIONS["en-IN"];

  useEffect(() => {
    if (view === "home") {
      speak(`${t.greeting} ${user.name || "friend"}. ${t.allGoodMsg}`, lang);
    }
  }, [view, lang]);

  // Robust "Go to..." navigation: speech recognition + visual fallback modal
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
        // Fallback: visual touch buttons are open and ready
      }
      setListening(false);
    }
  };

  const handleTileClick = (route) => {
    setNavModal(false);
    setView(route);
  };

  const TILES = [
    { id: "checkin", label: t.tiles.checkin, icon: "🌸", bg: "var(--rose-subtle)", color: "var(--rose-hover)" },
    { id: "meds", label: t.tiles.meds, icon: "💊", bg: "var(--peach-pastel)", color: "var(--peach-ink)", badge: 1 },
    { id: "health", label: t.tiles.health, icon: "🩺", bg: "var(--sky-pastel)", color: "var(--sky-ink)" },
    { id: "sharing", label: t.tiles.sharing, icon: "🛡️", bg: "var(--sage-pastel)", color: "var(--sage-ink)" },
    { id: "records", label: t.tiles.records, icon: "📋", bg: "var(--card-soft)", color: "var(--rose-primary)" },
    { id: "doctor", label: t.tiles.doctor, icon: "📞", bg: "var(--sky-pastel)", color: "var(--sky-ink)" },
    { id: "companion", label: t.tiles.companion, icon: "🌺", bg: "var(--lavender-pastel)", color: "var(--lavender-ink)" },
    { id: "safety", label: t.tiles.safety, icon: "🔍", bg: "var(--rose-subtle)", color: "var(--rose-hover)" },
    { id: "daily", label: t.tiles.daily, icon: "📜", bg: "var(--peach-pastel)", color: "var(--peach-ink)" },
    { id: "community", label: t.tiles.community, icon: "🤝", bg: "var(--sage-pastel)", color: "var(--sage-ink)" },
    { id: "pending", label: t.tiles.pending, icon: "🔔", bg: "var(--rose-subtle)", color: "var(--rose-hover)", badge: 1 },
    { id: "settings", label: t.tiles.settings, icon: "⚙️", bg: "var(--card-soft)", color: "var(--ink-muted)" }
  ];

  return (
    <div className="app-shell">
      <header className="clean-header">
        <div className="clean-brand">
          <span>🌸</span>
          <span>{t.brandName}</span>
        </div>
        <div className="header-actions">
          <button className="header-btn" onClick={hearAgain} title="Hear voice again">
            {t.repeatBtn}
          </button>
          <button className="header-btn" onClick={slowDown} title="Slow down speaking rate">
            {t.slowBtn}
          </button>
          <button className="header-btn" style={{ background: "var(--rose-primary)", color: "#fff" }} onClick={openVoiceNavigation}>
            {t.goToBtn}
          </button>
          <button className="header-btn" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <FallGuard lang={lang} />

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

            {/* Medicine Due Banner in Soft Peach Pastel */}
            <div
              onClick={() => setView("meds")}
              style={{
                background: "var(--peach-pastel)",
                border: "2px solid var(--peach-border)",
                borderRadius: "var(--radius-md)",
                padding: "1.1rem 1.25rem",
                marginBottom: "1rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer"
              }}
            >
              <div>
                <b style={{ color: "var(--peach-ink)", fontSize: "1.15rem" }}>💊 {t.tiles.meds}</b>
                <p style={{ margin: "0.2rem 0 0", color: "var(--ink-muted)", fontSize: "0.95rem" }}>
                  Metformin 500mg · 1 tablet due after lunch
                </p>
              </div>
              <span style={{ fontWeight: 800, color: "var(--peach-ink)" }}>Open →</span>
            </div>

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
                  {tile.badge && (
                    <span style={{
                      position: "absolute", top: 10, right: 10,
                      background: "var(--rose-primary)", color: "#fff",
                      fontSize: "0.75rem", fontWeight: 800,
                      padding: "0.15rem 0.5rem", borderRadius: "var(--radius-full)"
                    }}>
                      {tile.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tell Family I Am Fine Button */}
            <div style={{ marginTop: "1.5rem" }}>
              <button
                className="big-action sage-filled"
                onClick={() => {
                  setFineSent(true);
                  speak(t.fineSentMsg, lang);
                  setTimeout(() => setFineSent(false), 5000);
                }}
              >
                {t.tellFineBtn}
              </button>
              {fineSent && (
                <p style={{ textAlign: "center", color: "var(--sage-ink)", fontWeight: 700, marginTop: "0.6rem" }}>
                  ✔ {t.fineSentMsg}
                </p>
              )}
            </div>
          </div>
        )}

        {view !== "home" && (
          <div>
            <button
              onClick={() => setView("home")}
              style={{
                background: "none",
                border: "none",
                color: "var(--rose-primary)",
                fontWeight: 800,
                fontSize: "1.1rem",
                padding: "0.4rem 0 0.8rem",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem"
              }}
            >
              ← {t.backBtn || "Back to Home"}
            </button>

            <Suspense fallback={<p style={{ textAlign: "center" }}>Loading…</p>}>
              {view === "checkin" && <CheckIn lang={lang} onDone={() => setView("home")} />}
              {view === "meds" && <Medicines lang={lang} />}
              {view === "health" && <Health lang={lang} />}
              {view === "sharing" && <Sharing lang={lang} />}
              {view === "records" && <Records lang={lang} />}
              {view === "doctor" && <Doctor lang={lang} />}
              {view === "companion" && <Companion lang={lang} />}
              {view === "safety" && <SafetyHub lang={lang} />}
              {view === "daily" && <Daily lang={lang} />}
              {view === "community" && <Community lang={lang} />}
              {view === "pending" && <Pending lang={lang} />}
              {view === "settings" && <Settings lang={lang} user={user} />}
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
              <h2 style={{ margin: "0.4rem 0 0.2rem", fontSize: "1.5rem" }}>
                {t.goToModalTitle}
              </h2>
              <p style={{ color: "var(--ink-muted)", fontSize: "0.95rem", margin: 0 }}>
                {listening ? t.navListening : t.goToModalSub}
              </p>
              {spokenFeedback && (
                <p style={{ color: "var(--rose-primary)", fontWeight: 700, margin: "0.4rem 0 0" }}>
                  Heard: {spokenFeedback}
                </p>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.6rem", maxHeight: "40vh", overflowY: "auto" }}>
              {TILES.map((tile) => (
                <button
                  key={tile.id}
                  onClick={() => handleTileClick(tile.id)}
                  style={{
                    padding: "0.8rem 0.6rem",
                    borderRadius: "var(--radius-sm)",
                    border: "1.5px solid var(--line)",
                    background: tile.bg,
                    color: tile.color,
                    fontWeight: 700,
                    fontSize: "0.95rem",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem"
                  }}
                >
                  <span>{tile.icon}</span>
                  <span style={{ textAlign: "left" }}>{tile.label}</span>
                </button>
              ))}
            </div>

            <button className="big-action" onClick={() => setNavModal(false)}>
              Close
            </button>
          </div>
        </div>
      )}

      <SosButton />
    </div>
  );
}
