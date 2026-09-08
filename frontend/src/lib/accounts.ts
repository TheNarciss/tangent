/**
 * Plain-language vocabulary for bank accounts (Comptes screen + detail sheet).
 *
 * Everything a non-expert reads on the Comptes screen comes from here: account
 * type labels, transaction categories in French, grouping rules and the value
 * shown for each account. No jargon, no ticker, no IBAN.
 */
import type { BankAccountResponse, BankAccountType } from "@/api";

export type AccountGroup =
  "cash" | "savings" | "invest" | "retirement" | "employee" | "loan" | "other";

export const GROUP_ORDER: AccountGroup[] = [
  "cash",
  "savings",
  "invest",
  "retirement",
  "employee",
  "loan",
  "other",
];

export const GROUP_LABELS: Record<AccountGroup, string> = {
  cash: "Comptes courants",
  savings: "Épargne",
  invest: "Placements",
  retirement: "Retraite",
  employee: "Épargne salariale",
  loan: "Prêts",
  other: "Autres",
};

/** Long, spelled-out account types (no acronym a newcomer has to decode). */
export const TYPE_LABELS: Record<BankAccountType, string> = {
  checking: "Compte courant",
  card: "Carte à débit différé",
  joint: "Compte joint",
  savings: "Compte épargne",
  livret_a: "Livret A",
  livret_b: "Livret B",
  ldds: "Livret développement durable (LDDS)",
  lep: "Livret d'épargne populaire (LEP)",
  pel: "Plan épargne logement (PEL)",
  cel: "Compte épargne logement (CEL)",
  csl: "Compte sur livret",
  cat: "Compte à terme",
  deposit: "Dépôt",
  pea: "Plan d'épargne en actions (PEA)",
  cto: "Compte-titres",
  life_insurance: "Assurance vie",
  capitalisation: "Contrat de capitalisation",
  real_estate: "Immobilier",
  crowdlending: "Prêt participatif",
  per: "Plan épargne retraite (PER)",
  perp: "Plan épargne retraite (PERP)",
  perco: "Épargne retraite d'entreprise (PERCO)",
  madelin: "Retraite Madelin",
  article_83: "Retraite d'entreprise (art. 83)",
  pee: "Plan d'épargne entreprise (PEE)",
  rsp: "Réserve spéciale de participation",
  loan: "Prêt",
  mortgage: "Prêt immobilier",
  consumer_credit: "Crédit à la consommation",
  revolving_credit: "Crédit renouvelable",
  crypto: "Cryptomonnaies",
  other: "Autre",
};

export function groupOf(type: BankAccountType): AccountGroup {
  switch (type) {
    case "checking":
    case "card":
    case "joint":
      return "cash";
    case "savings":
    case "livret_a":
    case "livret_b":
    case "ldds":
    case "lep":
    case "pel":
    case "cel":
    case "csl":
    case "cat":
    case "deposit":
      return "savings";
    case "pea":
    case "cto":
    case "life_insurance":
    case "capitalisation":
    case "real_estate":
    case "crowdlending":
    case "crypto":
      return "invest";
    case "per":
    case "perp":
    case "perco":
    case "madelin":
    case "article_83":
      return "retirement";
    case "pee":
    case "rsp":
      return "employee";
    case "loan":
    case "mortgage":
    case "consumer_credit":
    case "revolving_credit":
      return "loan";
    default:
      return "other";
  }
}

/** Accounts whose detail lists positions (funds, shares). */
export function hasHoldings(type: BankAccountType): boolean {
  const g = groupOf(type);
  return g === "invest" || g === "retirement" || g === "employee";
}

/** Accounts whose detail lists movements. */
export function hasTransactions(type: BankAccountType): boolean {
  const g = groupOf(type);
  return g === "cash" || g === "savings";
}

/**
 * The one number shown for an account: valuation for placements, capital
 * still owed for loans (positive), balance otherwise.
 */
export function accountValue(a: BankAccountResponse): number {
  const g = groupOf(a.type);
  if (g === "loan") return a.loan?.used_amount ?? Math.abs(a.balance);
  if (g === "invest" || g === "retirement" || g === "employee") return a.valuation ?? a.balance;
  return a.balance;
}

export function groupTotal(accounts: BankAccountResponse[]): number {
  return accounts.reduce((sum, a) => sum + accountValue(a), 0);
}

/** Drop repeated words some banks put in account names ("Livret A Livret A"). */
export function cleanName(name: string): string {
  const seen = new Set<string>();
  return name
    .split(/\s+/)
    .filter((w) => {
      const k = w.toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .join(" ");
}

/** "il y a 3 min", "il y a 2 h", "il y a 4 j". */
export function relativeTime(iso: string | null): string {
  if (!iso) return "jamais";
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return `il y a ${Math.floor(hours / 24)} j`;
}

const DATE_LONG = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const DATE_SHORT = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });
const MONTH_YEAR = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });

export function longDate(iso: string | null): string {
  return iso ? DATE_LONG.format(new Date(iso)) : "—";
}
export function shortDate(iso: string): string {
  return DATE_SHORT.format(new Date(iso));
}
export function monthYear(iso: string | null): string {
  return iso ? MONTH_YEAR.format(new Date(iso)) : "—";
}

/** Backend taxonomy (finance/gap_filler/fields/transaction_category.py) → French. */
export const TRANSACTION_CATEGORIES: Record<string, string> = {
  alimentation: "Courses",
  restaurant: "Restaurant",
  transport: "Transports",
  carburant: "Carburant",
  loyer: "Loyer",
  charges_logement: "Charges du logement",
  telecom_internet: "Téléphone & internet",
  assurance: "Assurance",
  sante: "Santé",
  loisirs: "Loisirs",
  abonnements: "Abonnements",
  shopping: "Achats",
  voyages: "Voyages",
  education: "Éducation",
  impots_taxes: "Impôts & taxes",
  salaire: "Salaire",
  remboursement: "Remboursement",
  virement_interne: "Virement entre mes comptes",
  epargne_investissement: "Épargne & placements",
  frais_bancaires: "Frais bancaires",
  cadeaux_dons: "Cadeaux & dons",
  autre: "Autre",
};

export function categoryLabel(key: string | null): string {
  if (!key) return "Sans catégorie";
  return TRANSACTION_CATEGORIES[key] ?? key.replace(/_/g, " ");
}
