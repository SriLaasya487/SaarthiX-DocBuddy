// Voice helpers on top of the browser Web Speech API.
// Production: swap for Bhashini / AI4Bharat (or Google/Azure fallback) behind the same two functions.
import { t, hasTx } from "./i18n.js";
export const LANGUAGES = [
  { code: "hi-IN", label: "हिन्दी" }, { code: "te-IN", label: "తెలుగు" }, { code: "ta-IN", label: "தமிழ்" },
  { code: "bn-IN", label: "বাংলা" }, { code: "mr-IN", label: "मराठी" }, { code: "kn-IN", label: "ಕನ್ನಡ" },
  { code: "gu-IN", label: "ગુજરાતી" }, { code: "en-IN", label: "English" },
];

let lastText = "", lastLang = "en-IN", rate = 0.9;
export const setRate = (r) => { rate = r; };
export const getRate = () => rate;

export function speak(text, lang = lastLang) {
  // Indic text -> speak in that language. English text with a translation -> translate. Otherwise read English in an English voice.
  if (!/[^\u0000-\u024F]/.test(text)) { if (!lang.startsWith("en") && hasTx(text, lang)) text = t(text, lang); else lang = "en-IN"; }
  lastText = text; lastLang = lang;
  window.dispatchEvent(new CustomEvent("db-caption", { detail: text }));   // captions for people who cannot hear (DB-077)
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = rate;
  window.speechSynthesis.speak(u);
}
export const hearAgain = () => speak(lastText, lastLang);
export function slowDown() { rate = Math.max(0.5, rate - 0.2); hearAgain(); }

export const canListen = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition);

export function listen(lang = "en-IN") {
  return new Promise((resolve, reject) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return reject(new Error("Voice input is not supported in this browser"));
    const r = new SR();
    r.lang = lang; r.interimResults = false; r.maxAlternatives = 1;
    r.onresult = (e) => resolve(e.results[0][0].transcript);
    r.onerror = (e) => reject(new Error(e.error));
    r.onend = () => resolve("");
    r.start();
  });
}

// "My BP is 140 over 90" / "sugar is 180"
export function parseVital(text) {
  const t = text.toLowerCase();
  const nums = (t.match(/\d+(\.\d+)?/g) || []).map(Number);
  if (/bp|pressure/.test(t) && nums.length >= 2) return { kind: "bp", value1: nums[0], value2: nums[1] };
  if (/sugar|glucose/.test(t) && nums.length) return { kind: "sugar", value1: nums[0] };
  if (/oxygen|spo2/.test(t) && nums.length) return { kind: "spo2", value1: nums[0] };
  if (/pulse|heart rate/.test(t) && nums.length) return { kind: "pulse", value1: nums[0] };
  return null;
}
export const isYes = (t) => /\b(yes|yeah|ha|haan|han|ok|okay|sare|avunu|ஆம்|हाँ|हां)\b/i.test(t);
export const isNo = (t) => /\b(no|nahi|nahin|illa|kaadu|இல்லை|नहीं)\b/i.test(t);

// ---- dialects (DB-075): starter lexicon from the server, cached for offline use ----
let lex = null;
try { lex = JSON.parse(localStorage.getItem("db_lex")); } catch { /* none yet */ }
export async function loadLexicon(get) { try { lex = await get("/dialect/lexicon"); localStorage.setItem("db_lex", JSON.stringify(lex)); } catch { /* keep cached */ } }
export function interpret(text, dialect = "") {
  const t = (text || "").toLowerCase(); if (!lex) return [];
  const hits = [];
  const phrases = [...Object.entries(lex.dialects?.[dialect] || {}), ...Object.entries(lex.intents).flatMap(([i, ws]) => ws.map((w) => [w, i]))];
  for (const [p, intent] of phrases) { const i = t.indexOf(p.toLowerCase()); if (i >= 0) hits.push([i, intent]); }
  hits.sort((a, b) => a[0] - b[0]);
  const out = [...new Set(hits.map((h) => h[1]))];
  if (out.includes("yes") && out.includes("no")) { const last = hits.filter((h) => h[1] === "yes" || h[1] === "no").pop()[1]; return out.filter((x) => x !== "yes" && x !== "no").concat(last); }
  return out;
}
export const saysYes = (t, d) => interpret(t, d).includes("yes") || isYes(t);
export const saysNo = (t, d) => interpret(t, d).includes("no") || isNo(t);

// Ask a yes/no question out loud and listen; falls back to null (caller shows buttons).
export async function confirmByVoice(question, lang, dialect = "") {
  speak(question, lang);
  if (!canListen()) return null;
  await new Promise((r) => setTimeout(r, Math.min(6000, 600 + question.length * 55)));
  try { const t = await listen(lang); if (saysNo(t, dialect)) return false; if (saysYes(t, dialect)) return true; } catch { /* ignore */ }
  return null;
}

// Spoken digits: "nine eight four" / "नौ आठ चार" / "9 8 4"
const DIGITS = { zero: 0, oh: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  शून्य: 0, एक: 1, दो: 2, तीन: 3, चार: 4, पांच: 5, पाँच: 5, छह: 6, छः: 6, सात: 7, आठ: 8, नौ: 9 };
export function parseDigits(text) {
  return (text || "").toLowerCase().split(/[\s,.-]+/).map((w) => (/^\d+$/.test(w) ? w : w in DIGITS ? String(DIGITS[w]) : "")).join("");
}

// Voice navigation (DB-001/DB-011): works in several languages by keyword.
const NAV = [
  ["meds", /medicine|tablet|dawai|dawa|मेडिसिन|दवा|మందు|மருந்து/i], ["checkin", /check.?in|how am i|feeling|हालचाल|चेक/i], ["health", /\bbp\b|sugar|reading|appointment|visit|शुगर|రక్త|சர்க்கரை/i],
  ["records", /record|report|document|diary|lab|रिपोर्ट/i], ["safety", /safe|scam|hospital|pharmacy|weather|सुरक्षा/i], ["companion", /music|story|game|news|pray|bhajan|संगीत|कहानी/i],
  ["sharing", /share|who can see|privacy|consent|गोपनीय/i], ["assistant", /assistant|call|alarm|bus|train|सहायक/i], ["settings", /setting|language|font|size|सेटिंग/i], ["home", /home|back|घर|होम/i],
];
export function voiceNav(text) { const hit = NAV.find(([, re]) => re.test(text || "")); return hit ? hit[0] : null; }

// speech-to-text for dictation fields
export async function dictate(lang) { try { return await listen(lang); } catch { return ""; } }
