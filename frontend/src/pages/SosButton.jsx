import { useState } from "react";
import { api } from "../api.js";

export default function SosButton() {
  const [msg, setMsg] = useState("");
  const press = async () => {
    let location = "";
    try {
      const p = await new Promise((ok, no) => navigator.geolocation.getCurrentPosition(ok, no, { timeout: 4000 }));
      location = `${p.coords.latitude},${p.coords.longitude}`;
    } catch { /* location is optional */ }
    try {
      const r = await api.post("/sos", { location });
      setMsg(r.contacts_notified ? `Help is being told. ${r.contacts_notified} person(s) informed. You can also call 112.`
        : "You have not chosen anyone for emergencies yet. Please call 112 now.");
    } catch (e) { setMsg("Could not send. Please call 112 now."); }
  };
  return (
    <>
      <button className="sos" onClick={press} aria-label="Emergency SOS">SOS</button>
      {msg && <div className="toast" role="alert">{msg} <a href="tel:112">Call 112</a> <button onClick={() => setMsg("")}>OK</button></div>}
    </>
  );
}
