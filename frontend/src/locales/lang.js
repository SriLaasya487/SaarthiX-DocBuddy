import { LANG_LIST } from "../i18n.js";
import { setDomLanguage } from "../domtranslate.js";

export const LANG_KEY = "db_lang";
export const DEFAULT_LANG = "en-IN";

export const isSupportedLang = (code) => LANG_LIST.some((l) => l.code === code);

export function readSavedLang() {
  try {
    const v = localStorage.getItem(LANG_KEY);
    if (v && isSupportedLang(v)) return v;
  } catch { /* private mode */ }
  return DEFAULT_LANG;
}

export function persistLang(code) {
  const next = isSupportedLang(code) ? code : DEFAULT_LANG;
  try { localStorage.setItem(LANG_KEY, next); } catch { /* private mode */ }
  setDomLanguage(next);
  return next;
}
