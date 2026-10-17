import { useState } from "react";
import { api, setToken, isDemo } from "../api.js";
import { LANGUAGES, canListen, listen, parseDigits, speak } from "../voice.js";

export default function Login({ onDone }) {
  const [step, setStep] = useState("who");
  const [role, setRole] = useState("elder");
  const [lang, setLang] = useState("hi-IN");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [hint, setHint] = useState("");
  const [err, setErr] = useState("");

  const sendOtp = async (ph = phone) => {
    setErr("");
    try { const r = await api.post("/auth/request-otp", { phone: ph }); setHint(r.dev_otp || ""); setStep("otp"); return true; }
    catch (e) { setErr(e.message); return false; }
  };
  const verify = async (code = otp, ph = phone, nm = name, lg = lang) => {
    setErr("");
    try {
      const r = await api.post("/auth/verify", { phone: ph, otp: code, name: nm, role, language: lg });
      setToken(r.token); onDone(r.user);
    } catch (e) { setErr(e.message); }
  };

  // DB-002: sign up by talking. Every spoken answer can be corrected with the buttons.
  const talk = async () => {
    const ask = async (q, l = "en-IN") => { speak(q, l); await new Promise((r) => setTimeout(r, 2800)); return listen(l).catch(() => ""); };
    const l0 = await ask("Which language do you speak? Say Hindi, Telugu, Tamil, Bengali, Marathi, Kannada, Gujarati or English.");
    const pick = LANGUAGES.find((l) => new RegExp(`${l.label}|${{ "hi-IN": "hindi", "te-IN": "telugu", "ta-IN": "tamil", "bn-IN": "bengali", "mr-IN": "marathi", "kn-IN": "kannada", "gu-IN": "gujarati", "en-IN": "english" }[l.code]}`, "i").test(l0)) || LANGUAGES[0];
    setLang(pick.code);
    const nm = (await ask("What is your name?", pick.code)).trim(); setName(nm);
    const ph = parseDigits(await ask("Please say your mobile number, digit by digit.", pick.code)).slice(-10); setPhone(ph);
    if (ph.length !== 10) { speak("I could not get all ten digits. Please type your number.", pick.code); return setStep("phone"); }
    if (!(await sendOtp(ph))) return;
    const code = parseDigits(await ask("I sent a code by message. Please say the six digits.", pick.code)).slice(0, 6); setOtp(code);
    if (code.length === 6) verify(code, ph, nm, pick.code); else speak("Please type the code.", pick.code);
  };

  return (
    <main className="center">
      <h1 className="brand">AarogyaSaathi</h1>
      <p className="lede">Your care companion. You decide who sees what.</p>

      {step === "who" && (
        <section className="stack">
          {isDemo && <>
            <p className="note">Live demo with sample data. Pick a view:</p>
            <button className="big ok" onClick={() => { setToken("demo-elder"); onDone({}); }}>▶ Try the demo as Sarala (senior, 72)</button>
            <button className="big ok" onClick={() => { setToken("demo-family"); onDone({}); }}>▶ Try the demo as Rohan (her son)</button>
            <button className="big ok" onClick={() => { setToken("demo-chw"); onDone({}); }}>▶ Try the demo as Meena (ASHA worker)</button>
            <hr style={{ width: "100%" }} />
          </>}
          <button className="big primary" onClick={() => { setRole("elder"); setStep("lang"); speak("Please choose your language", "en-IN"); }}>I am the senior</button>
          <button className="big" onClick={() => { setRole("family"); setStep("phone"); }}>I am family or a doctor</button>
          <button className="big" onClick={() => { setRole("chw"); setStep("phone"); }}>I am a health worker (ASHA / nurse)</button>
          <button className="big" onClick={() => { setRole("partner"); setStep("phone"); }}>I represent an organisation</button>
        </section>
      )}

      {step === "lang" && (
        <section className="stack">
          <h2>Choose your language</h2>
          <div className="grid2">
            {LANGUAGES.map((l) => (
              <button key={l.code} className={"big " + (lang === l.code ? "primary" : "")} onClick={() => { setLang(l.code); speak(l.label, l.code); }}>{l.label}</button>
            ))}
          </div>
          <button className="big primary" onClick={() => setStep("phone")}>Next</button>
          {canListen() && <button className="big mic" onClick={talk}>🎤 Sign up by talking</button>}
        </section>
      )}

      {step === "phone" && (
        <section className="stack">
          <label>Your name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></label>
          <label>Mobile number<input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="tel" /></label>
          <button className="big primary" disabled={!phone} onClick={() => sendOtp()}>Send code</button>
        </section>
      )}

      {step === "otp" && (
        <section className="stack">
          <label>Code sent to {phone}<input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" maxLength={6} /></label>
          {hint && <p className="note">Dev mode code: <b>{hint}</b></p>}
          <button className="big primary" disabled={otp.length < 6} onClick={() => verify()}>Sign in</button>
        </section>
      )}
      {err && <p className="error" role="alert">{err}</p>}
    </main>
  );
}
