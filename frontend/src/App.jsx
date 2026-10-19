import { useEffect, useState } from "react";
import { api, hasToken, setToken } from "./api.js";
import Login from "./pages/Login.jsx";
import ElderApp from "./pages/ElderApp.jsx";
import FamilyPortal from "./pages/FamilyPortal.jsx";
import PartnerPortal from "./pages/PartnerPortal.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());

  useEffect(() => {
    if (hasToken()) api.get("/me").then(setUser).catch((e) => { if (/Invalid|Not signed|Unknown/.test(e.message)) setToken(""); }).finally(() => setReady(true));
  }, []);

  const logout = () => { setToken(""); setUser(null); };
  if (!ready) return <main className="center"><p>Loading…</p></main>;
  if (!user) return <Login onDone={() => api.get("/me").then(setUser).catch(() => { setToken(""); window.alert("Could not sign you in. Please try again."); })} />;
  if (user.role === "elder") return <ElderApp user={user} onLogout={logout} />;
  if (user.role === "partner" || user.role === "chw") return <PartnerPortal user={user} onLogout={logout} />;
  return <FamilyPortal user={user} onLogout={logout} />;
}
