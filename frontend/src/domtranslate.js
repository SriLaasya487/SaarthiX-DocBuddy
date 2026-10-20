// Translates the on-screen text of every screen into the user's language (Hindi / Telugu) without editing each page.
// It only changes text it recognises (see translate.js) and never wraps or moves elements, so React keeps working.
// It also shows "AarogyaSaathi" wherever older text still says "DocBuddy".
import { translate } from "./translate.js";

const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "NOSCRIPT"]);
let lang = "en-IN", applied = false, started = false;
try { lang = localStorage.getItem("db_lang") || "en-IN"; } catch { /* no storage */ }

export function convertText(s, lg = lang) {
  if (!s || !/[A-Za-z]/.test(s)) return s;
  const out = s.replace(/DocBuddy/g, "AarogyaSaathi");
  if (!lg || lg.startsWith("en")) return out;
  const core = out.trim(); if (!core) return out;
  const at = out.indexOf(core), lead = out.slice(0, at), trail = out.slice(at + core.length);
  let r = translate(core, lg);
  if (!r) {   // text that starts with an emoji or arrow, e.g. "🎤 Speak"
    const m = core.match(/^([^\p{L}\p{N}]*)([\s\S]*)$/u);
    if (m && m[1] && m[2]) { const x = translate(m[2], lg); if (x) r = m[1] + x; }
  }
  return r ? lead + r + trail : out;
}

const fixNode = (n) => { const v = n.nodeValue, o = convertText(v); if (o !== v) { n.nodeValue = o; if (!lang.startsWith("en")) applied = true; } };
function fixAttrs(el) {
  for (const a of ["placeholder", "aria-label", "title"]) {
    const v = el.getAttribute && el.getAttribute(a);
    if (v) { const o = convertText(v); if (o !== v) el.setAttribute(a, o); }
  }
}
function walk(node) {
  if (node.nodeType === 3) return fixNode(node);
  if (node.nodeType !== 1 || SKIP.has(node.tagName)) return;
  fixAttrs(node);
  node.childNodes.forEach(walk);
}

export function setDomLanguage(l) {
  const next = l || "en-IN";
  if (next === lang) {
    try { localStorage.setItem("db_lang", next); } catch { /* no storage */ }
    return;
  }
  lang = next;
  try { localStorage.setItem("db_lang", next); } catch { /* no storage */ }
  document.documentElement.lang = next.slice(0, 2);
  // React re-renders via tr()/t(); do not reload (that reset in-app navigation).
  applied = false;
}

export function startDomTranslate() {
  if (started || typeof document === "undefined") return;
  started = true;
  document.documentElement.lang = lang.slice(0, 2);
  walk(document.body);
  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "characterData") fixNode(m.target);
      else if (m.type === "attributes") fixAttrs(m.target);
      else m.addedNodes.forEach(walk);
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "aria-label", "title"] });
}
