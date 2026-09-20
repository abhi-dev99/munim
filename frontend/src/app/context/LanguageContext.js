"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import en from "../translations/en";
import hi from "../translations/hi";
import mr from "../translations/mr";
import gu from "../translations/gu";

const translations = { en, hi, mr, gu };

// localStorage slot reserved for a *deliberate* in-app language choice — i.e.
// the user tapped the language picker on this device. Nothing else writes it.
const STORAGE_KEY = "preferred_language";

const LanguageContext = createContext();

function isSupported(code) {
  return typeof code === "string" && Object.prototype.hasOwnProperty.call(translations, code);
}

// Read the explicit in-app choice straight from localStorage at call time
// rather than caching it in state. setProfileLanguage() below is called from
// an async profile fetch whose ordering against this provider's mount effect
// is not guaranteed (child effects run before parent effects, but the fetch
// resolves later still), and a direct read has no such ordering hazard.
function readStoredLanguage() {
  if (typeof window === "undefined") return null;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return isSupported(saved) ? saved : null;
  } catch {
    // Private mode / blocked site data — behave as if nothing was stored.
    return null;
  }
}

// Only warn once per key. t() runs on every render, so an unguarded warn in a
// re-rendering list would flood the console and bury the first occurrence.
const warnedKeys = new Set();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Validate against what actually ships rather than a hardcoded pair, so
    // adding a translation file is the only step needed to enable a language.
    const savedLang = readStoredLanguage();
    if (savedLang) setLang(savedLang);
    setMounted(true);
  }, []);

  const changeLanguage = useCallback((newLang) => {
    if (!isSupported(newLang)) return;
    setLang(newLang);
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // Storage unavailable — the choice still applies for this session.
    }
  }, []);

  /**
   * Seed the UI language from the logged-in trader's `language_pref` column
   * (set during WhatsApp onboarding — see backend/app/api/webhook.py).
   *
   * Precedence, highest first:
   *   1. An explicit in-app choice (localStorage). The user physically picked
   *      a language in this app on this device; that is the most recent and
   *      most deliberate signal there is, and silently overriding it with a
   *      server value every time the profile loads would make the picker look
   *      broken — you'd tap Gujarati and watch it snap back to Hindi.
   *   2. The trader's saved `language_pref`. A shopkeeper onboarded over
   *      WhatsApp in Gujarati has already told us their language once; making
   *      them say it again in the app is exactly the friction this product
   *      exists to remove. This is the case that used to be dropped entirely:
   *      `language_pref` reached the native bridge and the voice components
   *      but never the rendered UI.
   *   3. "en", the existing default.
   *
   * This deliberately does NOT write to localStorage. That slot means "the
   * user chose this here"; keeping the profile seed out of it means a trader
   * who later switches language over WhatsApp sees the app follow, instead of
   * being pinned forever to a value the app invented on their behalf.
   */
  const setProfileLanguage = useCallback((pref) => {
    if (!isSupported(pref)) return;
    if (readStoredLanguage()) return; // rule 1: explicit choice wins
    setLang((current) => (current === pref ? current : pref));
  }, []);

  const t = useCallback(
    (key, vars) => {
      const active = translations[lang] || translations.en;
      let value = active[key];

      if (value === undefined) {
        value = translations.en[key];
        if (value === undefined) {
          // Missing from the active language *and* from the English canon —
          // without this the raw key ("dashboard_itc_total") is what the
          // trader reads, with nothing anywhere to say something went wrong.
          if (process.env.NODE_ENV !== "production" && !warnedKeys.has(key)) {
            warnedKeys.add(key);
            console.warn(
              `[i18n] Missing key "${key}" in "${lang}" and in the "en" fallback — rendering the raw key.`,
            );
          }
          return key;
        }
      }

      // Named placeholders, e.g. t("tr_queued_many", { count: 3 }). Unknown
      // placeholders are left as-is rather than blanked, so a typo shows up
      // as "{cont}" instead of silently vanishing from the sentence.
      if (!vars) return value;
      return String(value).replace(/\{(\w+)\}/g, (match, name) =>
        vars[name] === undefined || vars[name] === null ? match : String(vars[name]),
      );
    },
    [lang],
  );

  if (!mounted) {
    // Language-neutral placeholder: the server renders this too, so anything
    // language-dependent here would be a guaranteed hydration mismatch (the
    // stored language can only be read on the client).
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center" aria-busy="true">
        <div className="h-6 w-6 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin" />
      </div>
    );
  }

  return (
    <LanguageContext.Provider value={{ lang, changeLanguage, setProfileLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
