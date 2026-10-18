import { useState } from "react";
import { TRANSLATIONS } from "../i18n.js";
import { speak } from "../voice.js";

export default function Login({ onDone }) {
  const [step, setStep] = useState("who"); // who -> lang -> phone -> otp
  const [role, setRole] = useState("elder");
  const [lang, setLang] = useState("en-IN");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [hint, setHint] = useState("");

  const t = TRANSLATIONS[lang] || TRANSLATIONS["en-IN"];

  const handleRoleSelect = (selectedRole) => {
    setRole(selectedRole);
    if (selectedRole === "elder") {
      setStep("lang");
      speak("Please choose your language", lang);
    } else {
      setStep("phone");
    }
  };

  const handleLangSelect = (selectedCode) => {
    setLang(selectedCode);
    const chosenT = TRANSLATIONS[selectedCode] || TRANSLATIONS["en-IN"];
    speak(chosenT.chooseLangTitle || "Language selected", selectedCode);
  };

  const startDemoAsSenior = () => {
    onDone({ id: 1, name: "Sarala Devi", role: "elder", language: lang || "en-IN" });
  };

  const startDemoAsFamily = () => {
    onDone({ id: 2, name: "Rohan", role: "family", language: lang || "en-IN" });
  };

  return (
    <div className="app-shell">
      <main className="main-content">
        <div className="login-box">
          <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
            <span style={{ fontSize: "2.8rem" }} role="img" aria-label="Flower">🌸</span>
            <h1 style={{ fontSize: "2.2rem", margin: "0.4rem 0 0.2rem", color: "var(--rose-primary)" }}>
              {t.brandName}
            </h1>
            <p style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 0.5rem", color: "var(--ink-muted)" }}>
              {t.brandSubtitle}
            </p>
            <p style={{ fontSize: "0.98rem", color: "var(--ink-muted)", margin: 0 }}>
              {t.tagline}
            </p>
          </div>

          {/* Quick Demo Shortcuts for Hackathon Jury */}
          <div style={{ display: "flex", gap: "0.6rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
            <button
              onClick={startDemoAsSenior}
              style={{
                flex: "1 1 45%",
                padding: "0.65rem 0.8rem",
                borderRadius: "var(--radius-sm)",
                border: "1.5px solid var(--rose-primary)",
                background: "var(--rose-subtle)",
                color: "var(--rose-hover)",
                fontWeight: 700,
                fontSize: "0.95rem",
                cursor: "pointer"
              }}
            >
              👵 {t.demoBypassBtn}
            </button>
            <button
              onClick={startDemoAsFamily}
              style={{
                flex: "1 1 45%",
                padding: "0.65rem 0.8rem",
                borderRadius: "var(--radius-sm)",
                border: "1.5px solid var(--line)",
                background: "var(--card)",
                color: "var(--ink)",
                fontWeight: 700,
                fontSize: "0.95rem",
                cursor: "pointer"
              }}
            >
              👨‍👦 {t.demoBypassFamily}
            </button>
          </div>

          {step === "who" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              <button className="big-action rose-filled" onClick={() => handleRoleSelect("elder")}>
                👵 {t.seniorRole}
              </button>
              <button className="big-action" onClick={() => handleRoleSelect("family")}>
                👨‍👩‍👧 {t.familyRole}
              </button>
              <button className="big-action" onClick={() => handleRoleSelect("chw")}>
                🩺 {t.chwRole}
              </button>
              <button className="big-action" onClick={() => handleRoleSelect("partner")}>
                🏛️ {t.orgRole}
              </button>
            </div>
          )}

          {step === "lang" && (
            <div>
              <h2 style={{ fontSize: "1.45rem", textAlign: "center", marginBottom: "0.3rem" }}>
                {t.chooseLangTitle}
              </h2>
              <p style={{ textAlign: "center", color: "var(--ink-muted)", fontSize: "0.95rem", margin: "0 0 1.2rem" }}>
                {t.chooseLangSub}
              </p>
              
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.75rem", marginBottom: "1.2rem" }}>
                {[
                  { code: "en-IN", name: "English", sub: "English" },
                  { code: "hi-IN", name: "हिन्दी", sub: "Hindi" },
                  { code: "te-IN", name: "తెలుగు", sub: "Telugu" },
                  { code: "ta-IN", name: "தமிழ்", sub: "Tamil" },
                  { code: "kn-IN", name: "ಕನ್ನಡ", sub: "Kannada" },
                  { code: "mr-IN", name: "मराठी", sub: "Marathi" },
                  { code: "gu-IN", name: "ગુજરાતી", sub: "Gujarati" },
                  { code: "bn-IN", name: "বাংলা", sub: "Bengali" }
                ].map((l) => (
                  <button
                    key={l.code}
                    onClick={() => handleLangSelect(l.code)}
                    style={{
                      padding: "1rem 0.5rem",
                      borderRadius: "var(--radius-md)",
                      border: lang === l.code ? "2.5px solid var(--rose-primary)" : "1.5px solid var(--line)",
                      background: lang === l.code ? "var(--rose-subtle)" : "var(--card)",
                      color: lang === l.code ? "var(--rose-hover)" : "var(--ink)",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "0.2rem",
                      fontWeight: 700
                    }}
                  >
                    <span style={{ fontSize: "1.35rem", fontWeight: 800 }}>{l.name}</span>
                    <span style={{ fontSize: "0.85rem", color: "var(--ink-muted)" }}>{l.sub}</span>
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", gap: "0.8rem" }}>
                <button className="big-action" style={{ flex: 1 }} onClick={() => setStep("who")}>
                  {t.backBtn}
                </button>
                <button className="big-action rose-filled" style={{ flex: 1 }} onClick={() => setStep("phone")}>
                  {t.nextBtn} →
                </button>
              </div>
            </div>
          )}

          {step === "phone" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              <label>
                {t.nameLabel}
                <input
                  value={name}
                  placeholder={t.namePlaceholder}
                  onChange={(e) => setName(e.target.value)}
                  style={{ width: "100%", padding: "0.8rem", borderRadius: "var(--radius-sm)", border: "2px solid var(--line)", marginTop: "0.3rem" }}
                />
              </label>
              <label>
                {t.phoneLabel}
                <input
                  value={phone}
                  placeholder={t.phonePlaceholder}
                  inputMode="tel"
                  onChange={(e) => setPhone(e.target.value)}
                  style={{ width: "100%", padding: "0.8rem", borderRadius: "var(--radius-sm)", border: "2px solid var(--line)", marginTop: "0.3rem" }}
                />
              </label>
              <button className="big-action rose-filled" onClick={() => { setHint("123456"); setStep("otp"); }}>
                {t.sendOtpBtn}
              </button>
              <button className="big-action" onClick={() => setStep(role === "elder" ? "lang" : "who")}>
                {t.backBtn}
              </button>
            </div>
          )}

          {step === "otp" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              <label>
                {t.otpLabel}
                <input
                  value={otp}
                  placeholder="123456"
                  maxLength={6}
                  inputMode="numeric"
                  onChange={(e) => setOtp(e.target.value)}
                  style={{ width: "100%", padding: "0.8rem", borderRadius: "var(--radius-sm)", border: "2px solid var(--line)", marginTop: "0.3rem" }}
                />
              </label>
              <p style={{ textAlign: "center", color: "var(--ink-muted)", fontSize: "0.9rem", margin: 0 }}>
                Demo OTP: <b>{hint || "123456"}</b>
              </p>
              <button className="big-action rose-filled" onClick={() => { onDone({ id: 1, name: name || "Sarala Devi", role, language: lang }); }}>
                {t.signInBtn}
              </button>
              <button className="big-action" onClick={() => setStep("phone")}>
                {t.backBtn}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
