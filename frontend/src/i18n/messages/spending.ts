/** « Dépenses »: the month's figures, in/out columns, category stack, deltas, merchants, tables. */
const fr = {
  "spending.intro":
    "Un virement vers un autre de tes comptes connectés, ton épargne ou un remboursement de prêt n'est pas une dépense. Un virement vers un compte que Tangent ne connaît pas en est une : l'argent est parti.",
  "spending.months.one": "{count} mois",
  "spending.months.other": "{count} mois",
  "spending.empty":
    "Aucun mouvement synchronisé sur tes comptes courants pour l'instant. Tout apparaîtra ici dès la prochaine synchronisation.",
  "spending.showCharts": "Voir les graphiques",
  "spending.showTable": "Voir le tableau",
  "spending.nothingToShow": "Rien à montrer sur cette période.",
  "spending.currentMonthNote": "Le mois en cours est plus clair : il n'est pas fini.",

  "spending.received": "Reçu",
  "spending.spent": "Dépensé",
  "spending.left": "Reste",

  "spending.kpi.spent": "Dépensé ce mois-ci",
  "spending.kpi.vsAverage": "{delta} vs {average} en moyenne",
  "spending.kpi.noCompleteMonth": "pas encore de mois complet",
  "spending.kpi.received": "Reçu ce mois-ci",
  "spending.kpi.average": "{average} en moyenne",
  "spending.kpi.left": "Reste ce mois-ci",
  "spending.kpi.leftSub": "reçu moins dépensé",
  "spending.kpi.saved": "Épargné, mois complets",
  "spending.kpi.savedSub": "part du reçu non dépensée",

  "spending.inOut.title": "Entrées et sorties, par mois",
  "spending.inOut.aria": "Reçu et dépensé par mois",

  "spending.stack.title": "Dans quoi, mois par mois",
  "spending.stack.unlabelled": "{share} des dépenses n'ont pas encore de catégorie.",
  "spending.stack.aria": "Dépenses par catégorie et par mois",
  "spending.stack.note":
    "Les {count} plus grosses catégories de la période ont leur couleur ; le reste est en gris.",
  "spending.otherCategories": "Autres catégories",

  "spending.where.title": "Où ça part",
  "spending.where.sub": "Sur toute la période.",
  "spending.others": "Autres",

  "spending.moved.title": "Ce qui a bougé",
  "spending.moved.needTwo": "Il faut deux mois complets pour comparer. Reviens le mois prochain.",
  "spending.moved.nothing": "Rien de notable en {month}.",
  "spending.moved.baseline.one": "{month}, contre la moyenne du mois précédent.",
  "spending.moved.baseline.other":
    "{month}, contre la moyenne des {count} mois complets précédents.",
  "spending.moved.usual": "{last} contre {average} d'habitude",
  "spending.moved.legend": "À droite en rouge : plus que d'habitude. À gauche en vert : moins.",

  "spending.who.title": "Chez qui",
  "spending.times.one": "{count} fois",
  "spending.times.other": "{count} fois",

  "spending.table.month": "Mois",
  "spending.table.byCategory": "Par catégorie",
  "spending.table.category": "Catégorie",

  "spending.category.alimentation": "Alimentation",
  "spending.category.restaurant": "Restaurants",
  "spending.category.transport": "Transport",
  "spending.category.carburant": "Carburant",
  "spending.category.loyer": "Loyer",
  "spending.category.charges_logement": "Charges du logement",
  "spending.category.telecom_internet": "Télécom & internet",
  "spending.category.assurance": "Assurances",
  "spending.category.sante": "Santé",
  "spending.category.loisirs": "Loisirs",
  "spending.category.abonnements": "Abonnements",
  "spending.category.shopping": "Shopping",
  "spending.category.voyages": "Voyages",
  "spending.category.education": "Éducation",
  "spending.category.impots_taxes": "Impôts & taxes",
  "spending.category.salaire": "Salaire",
  "spending.category.remboursement": "Remboursements",
  "spending.category.virement_interne": "Virements internes",
  "spending.category.virement_sortant": "Virements sortants",
  "spending.category.epargne_investissement": "Épargne & investissement",
  "spending.category.frais_bancaires": "Frais bancaires",
  "spending.category.cadeaux_dons": "Cadeaux & dons",
  "spending.category.autre": "Sans catégorie",
};

const en: Record<keyof typeof fr, string> = {
  "spending.intro":
    "A transfer to another of your connected accounts, your savings or a loan repayment is not spending. A transfer to an account Tangent does not know is: the money has gone.",
  "spending.months.one": "{count} month",
  "spending.months.other": "{count} months",
  "spending.empty":
    "No transactions synced on your current accounts yet. Everything will appear here after the next sync.",
  "spending.showCharts": "Show the charts",
  "spending.showTable": "Show the table",
  "spending.nothingToShow": "Nothing to show over this period.",
  "spending.currentMonthNote": "The current month is lighter: it is not over.",

  "spending.received": "Received",
  "spending.spent": "Spent",
  "spending.left": "Left",

  "spending.kpi.spent": "Spent this month",
  "spending.kpi.vsAverage": "{delta} vs {average} on average",
  "spending.kpi.noCompleteMonth": "no complete month yet",
  "spending.kpi.received": "Received this month",
  "spending.kpi.average": "{average} on average",
  "spending.kpi.left": "Left this month",
  "spending.kpi.leftSub": "received minus spent",
  "spending.kpi.saved": "Saved, complete months",
  "spending.kpi.savedSub": "share of what came in that was not spent",

  "spending.inOut.title": "In and out, by month",
  "spending.inOut.aria": "Received and spent by month",

  "spending.stack.title": "On what, month by month",
  "spending.stack.unlabelled": "{share} of spending has no category yet.",
  "spending.stack.aria": "Spending by category and by month",
  "spending.stack.note":
    "The {count} biggest categories of the period have their own colour; the rest is grey.",
  "spending.otherCategories": "Other categories",

  "spending.where.title": "Where it goes",
  "spending.where.sub": "Over the whole period.",
  "spending.others": "Others",

  "spending.moved.title": "What moved",
  "spending.moved.needTwo": "Two complete months are needed to compare. Come back next month.",
  "spending.moved.nothing": "Nothing notable in {month}.",
  "spending.moved.baseline.one": "{month}, against the average of the previous month.",
  "spending.moved.baseline.other":
    "{month}, against the average of the {count} previous complete months.",
  "spending.moved.usual": "{last} against {average} usually",
  "spending.moved.legend": "Right, in red: more than usual. Left, in green: less.",

  "spending.who.title": "With whom",
  "spending.times.one": "once",
  "spending.times.other": "{count} times",

  "spending.table.month": "Month",
  "spending.table.byCategory": "By category",
  "spending.table.category": "Category",

  "spending.category.alimentation": "Groceries",
  "spending.category.restaurant": "Restaurants",
  "spending.category.transport": "Transport",
  "spending.category.carburant": "Fuel",
  "spending.category.loyer": "Rent",
  "spending.category.charges_logement": "Household bills",
  "spending.category.telecom_internet": "Telecom & internet",
  "spending.category.assurance": "Insurance",
  "spending.category.sante": "Health",
  "spending.category.loisirs": "Leisure",
  "spending.category.abonnements": "Subscriptions",
  "spending.category.shopping": "Shopping",
  "spending.category.voyages": "Travel",
  "spending.category.education": "Education",
  "spending.category.impots_taxes": "Taxes",
  "spending.category.salaire": "Salary",
  "spending.category.remboursement": "Refunds",
  "spending.category.virement_interne": "Internal transfers",
  "spending.category.virement_sortant": "Outgoing transfers",
  "spending.category.epargne_investissement": "Savings & investments",
  "spending.category.frais_bancaires": "Bank fees",
  "spending.category.cadeaux_dons": "Gifts & donations",
  "spending.category.autre": "Uncategorised",
};

export const spending = { fr, en };
