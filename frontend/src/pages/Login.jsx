import { useState } from "react";
import { TRANSLATIONS } from "../i18n.js";
import { t as tr } from "../translate.js";
import { api, setToken } from "../api.js";
import { speak } from "../voice.js";

// Fixed test accounts for the quick-demo buttons. They are real accounts on the real server.
const DEMO = { elder: { phone: "9000000001", name: "Sarala Devi" }, family: { phone: "9000000002", name: "Rohan" } };

// First time Sarala signs in, give her a believable week so no screen is empty. Each step is optional.
async function seedElder() {
  const tryit = async (fn) => { try { await fn(); } catch { /* skip */ } };
  let meds = [];
  try { meds = await api.get("/medicines"); } catch { /* none */ }
  if (!meds.length) await seedBasics(tryit);
  await seedExtras(tryit);
}

async function seedBasics(tryit) {
  await tryit(() => api.post("/medicines", { name: "Metformin 500mg", tablets: 1, times: "09:00,21:00", stock: 20, color: "white" }));
  await tryit(() => api.post("/medicines", { name: "Amlodipine 5mg", tablets: 1, times: "09:00", stock: 30, color: "pink" }));
  await tryit(() => api.post("/vitals", { kind: "bp", value1: 138, value2: 88 }));
  await tryit(() => api.post("/vitals", { kind: "sugar", value1: 126 }));
  await tryit(() => api.post("/appointments", { doctor: "Dr. Reddy (Diabetes)", at: new Date(Date.now() + 2 * 864e5).toISOString().replace("Z", "") }));
  await tryit(() => api.put("/emergency-card", { blood_group: "B+", allergies: "Penicillin", conditions: "Diabetes, high BP", doctor_name: "Dr. Reddy", doctor_phone: "9800000000", contacts: "Rohan:9000000002" }));
  for (const dt of ["medicines", "report", "vitals", "mood", "imfine"]) {
    await tryit(() => api.post("/consents", { grantee_phone: DEMO.family.phone, grantee_name: "Rohan", data_type: dt, scope: "view", days: null, relation: "son" }));
  }
}

async function seedExtras(tryit) {
  let notes = null;
  try { notes = await api.get("/symptoms"); } catch { return; }
  if (notes.length) return;
  await tryit(() => api.post("/symptoms", { text: "Knee pain at night, better after rest" }));
  await tryit(() => api.post("/symptoms", { text: "Felt dizzy once in the morning" }));
  await tryit(() => api.post("/documents", { kind: "lab", title: "Blood sugar report (October)", expires_on: null, file_b64: "", file_ext: "jpg" }));
  await tryit(() => api.post("/previsit/questions", { question: "Can I reduce the evening Metformin dose?" }));
  await tryit(() => api.post("/checkin", { mood: "good", pain: "mild", took_medicines: true, needs_help: false, doctor_visit_soon: true }));
  await tryit(() => api.post("/community/join"));
}

export default function Login({ onDone }) {
  const [step, setStep] = useState("who"); // who -> lang -> phone -> otp
  const [role, setRole] = useState("elder");
  const [lang, setLang] = useState("en-IN");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [hint, setHint] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

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

  const clean = (p) => String(p).replace(/[^\d+]/g, "");

  const sendOtp = async () => {
    setErr(""); setBusy(true);
    try { const r = await api.post("/auth/request-otp", { phone: clean(phone) }); setHint(r.dev_otp || ""); setStep("otp"); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const verify = async () => {
    setErr(""); setBusy(true);
    try {
      const r = await api.post("/auth/verify", { phone: clean(phone), otp, name: name || "Friend", role, language: role === "elder" ? lang : "en-IN" });
      setToken(r.token); onDone(r.user);
    } catch (e) { setErr(e.message); setBusy(false); }
  };

  // Quick demo: signs in to a real test account (needs the server in test mode so it returns the code)
  const quickDemo = async (kind) => {
    const d = DEMO[kind]; setErr(""); setBusy(true);
    try {
      const r = await api.post("/auth/request-otp", { phone: d.phone });
      if (!r.dev_otp) throw new Error("Quick demo needs the server in test mode. Please sign in with your own number.");
      const v = await api.post("/auth/verify", { phone: d.phone, otp: r.dev_otp, name: d.name, role: kind, language: kind === "elder" ? lang : "en-IN" });
      setToken(v.token);
      if (kind === "elder") await seedElder();
      onDone(v.user);
    } catch (e) { setErr(e.message); setBusy(false); }
  };
  const startDemoAsSenior = () => quickDemo("elder");
  const startDemoAsFamily = () => quickDemo("family");

  return (
    <div className="app-shell">
      <main className="main-content">
        <div className="login-box">
          <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
            <img src={`${import.meta.env.BASE_URL}logo.svg`} alt="" width={72} height={72} style={{ borderRadius: 18 }} />
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

          {busy && <p className="note" role="status" style={{ textAlign: "center" }}>{tr("Please wait… the server may need up to a minute to wake up the first time.", lang)}</p>}
          {err && <p className="error" role="alert" style={{ textAlign: "center" }}>{err}</p>}

          {/* Quick sign-in to ready-made test accounts */}
          {step === "who" && (
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
          )}

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
              <button className="big-action rose-filled" onClick={sendOtp} disabled={busy || clean(phone).replace(/\D/g, "").length < 10}>
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
              {hint && (
                <p style={{ textAlign: "center", color: "var(--ink-muted)", fontSize: "0.9rem", margin: 0 }}>
                  Test code: <b>{hint}</b>
                </p>
              )}
              <button className="big-action rose-filled" onClick={verify} disabled={busy || otp.length < 6}>
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
