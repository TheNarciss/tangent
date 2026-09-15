/**
 * The language the app speaks — French or English.
 *
 * Nothing is asked: the browser (or the phone) says which language the person
 * reads, and the app follows. A preference set in « Mon compte » wins over it,
 * per device, so the site and the iPhone app can each be told separately.
 *
 * Module-level store + useSyncExternalStore, like lib/profile.ts: every
 * component sees the same locale, no context to thread through.
 */
import { useSyncExternalStore } from "react";

export type Locale = "fr" | "en";
/** What the person chose: a language, or « follow the browser ». */
export type LocalePreference = Locale | "auto";

export const LOCALES: Locale[] = ["fr", "en"];
const STORAGE_KEY = "tangent.locale";

/** The BCP 47 tag behind each locale, for Intl. British English writes € as « €1,234.50 ». */
export const LOCALE_TAGS: Record<Locale, string> = { fr: "fr-FR", en: "en-GB" };

function isLocale(v: unknown): v is Locale {
  return v === "fr" || v === "en";
}

/** English if the browser lists an English variant first; French otherwise. */
export function detectLocale(languages: readonly string[]): Locale {
  for (const lang of languages) {
    const base = lang.toLowerCase().split("-")[0];
    if (base === "en") return "en";
    if (base === "fr") return "fr";
  }
  return "fr";
}

function readPreference(): LocalePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return isLocale(raw) ? raw : "auto";
  } catch {
    return "auto";
  }
}

function browserLanguages(): readonly string[] {
  if (typeof navigator === "undefined") return [];
  return navigator.languages?.length ? navigator.languages : [navigator.language ?? "fr"];
}

function resolve(pref: LocalePreference): Locale {
  return pref === "auto" ? detectLocale(browserLanguages()) : pref;
}

let preference: LocalePreference = readPreference();
let current: Locale = resolve(preference);
const listeners = new Set<() => void>();

function applyToDocument(locale: Locale) {
  if (typeof document !== "undefined") document.documentElement.lang = locale;
}
applyToDocument(current);

export function getLocale(): Locale {
  return current;
}

export function getLocalePreference(): LocalePreference {
  return preference;
}

export function setLocalePreference(pref: LocalePreference): void {
  preference = pref;
  try {
    if (pref === "auto") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    // Private mode or storage disabled: the choice lasts for the session.
  }
  const next = resolve(pref);
  if (next !== current) {
    current = next;
    applyToDocument(current);
  }
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** The locale in effect; the component re-renders when it changes. */
export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, getLocale, getLocale);
}

export function useLocalePreference(): LocalePreference {
  return useSyncExternalStore(subscribe, getLocalePreference, getLocalePreference);
}
