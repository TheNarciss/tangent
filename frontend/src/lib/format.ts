import { LOCALE_TAGS, getLocale, type Locale } from "@/i18n";

/** Number formatters for one locale — built once per language, on first use. */
function build(locale: Locale) {
  const tag = LOCALE_TAGS[locale];
  return {
    eur: new Intl.NumberFormat(tag, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 2,
    }),
    eur0: new Intl.NumberFormat(tag, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }),
    pct: new Intl.NumberFormat(tag, {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
    pct0: new Intl.NumberFormat(tag, { style: "percent", maximumFractionDigits: 0 }),
    signedPct: new Intl.NumberFormat(tag, {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: "exceptZero",
    }),
    signedEur: new Intl.NumberFormat(tag, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 2,
      signDisplay: "exceptZero",
    }),
    signedEur0: new Intl.NumberFormat(tag, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
      signDisplay: "exceptZero",
    }),
    dec: new Intl.NumberFormat(tag, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  };
}

const cache: Partial<Record<Locale, ReturnType<typeof build>>> = {};

/** The formatters of the language in effect right now. */
function F() {
  const locale = getLocale();
  return (cache[locale] ??= build(locale));
}

/** « environ » : au millier près au-dessus de 10 k€, à la centaine en dessous. */
function approxEur(v: number): string {
  const step = Math.abs(v) >= 10_000 ? 1000 : 100;
  return F().eur0.format(Math.round(v / step) * step);
}

/** 35 k€ / 3,5 k€ / 850 € (fr) — €35k / €3.5k / €850 (en) — for axis ticks and ranges. */
function kEur(v: number): string {
  const en = getLocale() === "en";
  if (Math.abs(v) >= 1000) {
    const k = (v / 1000).toFixed(v >= 10_000 ? 0 : 1);
    return en ? `€${k}k` : `${k.replace(".", ",")} k€`;
  }
  return en ? `€${Math.round(v)}` : `${Math.round(v)} €`;
}

export const fmt = {
  eur: (v: number) => F().eur.format(v),
  /** Whole euros — yearly fees, amounts « en jeu ». */
  eur0: (v: number) => F().eur0.format(v),
  approxEur,
  kEur,
  signedEur: (v: number) => F().signedEur.format(v),
  /** Whole euros with a sign — a move against a habit: « +110 € ». */
  signedEur0: (v: number) => F().signedEur0.format(v),
  pct: (v: number) => F().pct.format(v),
  /** Whole percent: « 80 % ». For shares of a portfolio, where decimals are noise. */
  pct0: (v: number) => F().pct0.format(v),
  signedPct: (v: number) => F().signedPct.format(v),
  num: (v: number) => F().dec.format(v),
};
