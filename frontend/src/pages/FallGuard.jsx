// src/pages/FallGuard.jsx
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { isYes, listen, speak } from "../voice.js";

export default function FallGuard({ lang }) {
  const [alert, setAlert] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(60);
  const last = useRef(0);
  const timerRef = useRef(null);

  const trigger = async () => {
    const r = await api.post("/fall", {}).catch(() => null);
    if (!r) return;
    setAlert(r);
    setSecondsLeft(60);
    speak("Are you okay? Say yes, or press I am fine.", lang);
    listen(lang).then((t) => isYes(t) && fine(r.alert_id)).catch(() => {});
  };

  useEffect(() => {
    const onMotion = (e) => {
      const a = e.accelerationIncludingGravity;
      if (!a) return;
      const g = Math.sqrt((a.x || 0) ** 2 + (a.y || 0) ** 2 + (a.z || 0) ** 2) / 9.81;
      if (g > 3.2 && Date.now() - last.current > 30000) {
        last.current = Date.now();
        trigger();
      }
    };
    const onSimulate = () => trigger();
    
    window.addEventListener("devicemotion", onMotion);
    window.addEventListener("db-simulate-fall", onSimulate);
    return () => {
      window.removeEventListener("devicemotion", onMotion);
      window.removeEventListener("db-simulate-fall", onSimulate);
    };
  }, []);

  useEffect(() => {
    if (alert) {
      timerRef.current = setInterval(() => {
        setSecondsLeft((s) => {
          if (s <= 1) {
            clearInterval(timerRef.current);
            setAlert(null);
            speak("Emergency contacts have been notified.", lang);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [alert]);

  const fine = async (id) => {
    clearInterval(timerRef.current);
    await api.post(`/alerts/${id}/respond`, { allow: false });
    setAlert(null);
    speak("Good. Stay safe.", lang);
  };

  if (!alert) return null;

  return (
    <div className="modal" role="alertdialog" aria-label="Are you okay?">
      <div style={{ fontSize: "3rem" }}>⚠️</div>
      <h2>Are you okay?</h2>
      <p style={{ fontSize: "1.2rem", fontWeight: "bold", color: "var(--sos)" }}>
        Emergency contacts will be called in {secondsLeft} seconds...
      </p>
      <button className="big ok" onClick={() => fine(alert.alert_id)}>
        👍 I AM FINE
      </button>
      <a className="big" href="tel:112" style={{ background: "var(--sos)", color: "#fff", textDecoration: "none" }}>
        🚨 Call 112 Now
      </a>
    </div>
  );
}
