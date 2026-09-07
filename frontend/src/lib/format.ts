const eur = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

const pct = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const signedPct = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});

const signedEur = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});

const dec = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** « environ » : au millier près au-dessus de 10 k€, à la centaine en dessous. */
function approxEur(v: number): string {
  const step = Math.abs(v) >= 10_000 ? 1000 : 100;
  return eur.format(Math.round(v / step) * step).replace(",00", "");
}

/** 35 k€ / 3,5 k€ / 850 € — for axis ticks and ranges. */
function kEur(v: number): string {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(v >= 10_000 ? 0 : 1).replace(".", ",")} k€`;
  return `${Math.round(v)} €`;
}

export const fmt = {
  eur: (v: number) => eur.format(v),
  approxEur,
  kEur,
  signedEur: (v: number) => signedEur.format(v),
  pct: (v: number) => pct.format(v),
  signedPct: (v: number) => signedPct.format(v),
  num: (v: number) => dec.format(v),
};
