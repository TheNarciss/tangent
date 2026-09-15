/**
 * Homemade translations — no library, two languages, typed keys.
 *
 * Each domain file under messages/ holds the French text and its English
 * mirror side by side; TypeScript refuses an English dictionary missing a
 * key. `t("nav.overview")` picks the current locale, falls back to French,
 * then to the key itself so a hole is visible rather than blank.
 *
 * Plain functions on purpose: `t` works anywhere (helpers, view config), and
 * `useT()` is the same function plus a subscription so the component
 * re-renders when the language changes.
 */
import { account } from "./messages/account";
import { auth } from "./messages/auth";
import { common } from "./messages/common";
import { nav } from "./messages/nav";
import { getLocale, useLocale, type Locale } from "./locale";

export {
  LOCALES,
  LOCALE_TAGS,
  detectLocale,
  getLocale,
  getLocalePreference,
  setLocalePreference,
  useLocale,
  useLocalePreference,
} from "./locale";
export type { Locale, LocalePreference } from "./locale";

const FR = { ...common.fr, ...nav.fr, ...auth.fr, ...account.fr };
const EN: Record<MessageKey, string> = { ...common.en, ...nav.en, ...auth.en, ...account.en };

export type MessageKey = keyof typeof FR;
type Vars = Record<string, string | number>;

const DICT: Record<Locale, Record<MessageKey, string>> = { fr: FR, en: EN };

function interpolate(text: string, vars?: Vars): string {
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (m, name: string) => (name in vars ? String(vars[name]) : m));
}

/** The text for `key` in the current language; `{name}` slots are filled from `vars`. */
export function t(key: MessageKey, vars?: Vars): string {
  const text = DICT[getLocale()][key] ?? FR[key] ?? key;
  return interpolate(text, vars);
}

/**
 * Plural forms: `tn("x.count", 3)` reads `x.count.other`, `tn("x.count", 1)`
 * reads `x.count.one`, by the language's own rules (French says « 0 élément »
 * in the singular). `{count}` is filled in.
 */
export function tn(base: string, count: number, vars?: Vars): string {
  const locale = getLocale();
  const category = new Intl.PluralRules(locale).select(count);
  const exact = `${base}.${category}` as MessageKey;
  const other = `${base}.other` as MessageKey;
  const key = exact in DICT[locale] ? exact : other;
  return t(key, { count, ...vars });
}

/** `t` plus a subscription: the component re-renders when the language changes. */
export function useT() {
  useLocale();
  return { t, tn };
}
