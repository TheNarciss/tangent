# ADR-026: Taux sans risque et inflation deviennent des valeurs observées

- **Status** : accepted
- **Date** : 2026-09-09
- **Deciders** : Clem

## Contexte

Le taux sans risque était écrit trois fois : `analytics.RISK_FREE = 0.025`,
`verdicts.yaml` sous `goal.risk_free: 0.025`, et un commentaire reliant les
deux. L'inflation une quatrième, `verdicts.yaml: inflation: 0.02`.

Quatre copies d'un même chiffre finissent par diverger, et aucune ne se met à
jour. Le taux de la BCE, lui, a changé plusieurs fois depuis que la constante
a été écrite.

## Décision

Un module `finance/macro.py` sert les deux valeurs depuis les sources de
l'ADR-024 :

| Valeur | Source | Fenêtre |
|---|---|---|
| Taux sans risque | taux directeur BCE | dernière observation |
| Inflation | IPC harmonisé France (via FRED) | **moyenne sur trois ans** |

L'inflation est moyennée sur trois ans délibérément : une projection à vingt
ans ne doit pas basculer sur le chiffre d'un seul mois.

Chaque valeur a un repli dans `config/macro.yaml`, égal à l'ancienne
constante. Si la source ne répond pas, l'app affiche exactement ce qu'elle
affichait avant, et une ligne de log le signale. Aucune page ne tombe sur une
lecture macro.

`analytics.py` reste pur : il ne lit rien, il reçoit le taux en argument. Ce
sont les orchestrateurs (`dashboard`, `optimizer`, `projection`, `verdicts`)
qui appellent `macro`.

## Conséquences

### Positives

- Une seule déclaration par valeur, et elle est datée.
- Les chiffres suivent la réalité : le jour où la BCE bouge, la projection
  bouge.
- Les tests ne touchent jamais le réseau : une fixture coupe tout appel
  sortant, donc chaque consommateur emprunte le chemin dégradé qu'il promet.

### Négatives

- Deux valeurs métier changent (voir ci-dessous).
- Un résultat peut varier d'un jour à l'autre sans qu'on ait touché au code.
  C'est le but, mais ça rend une capture d'écran non reproductible.

### ⚠️ Effet sur les chiffres affichés

| Valeur | Avant | Après (au 2026-09-09) |
|---|---|---|
| Taux sans risque | 2,50 % | **2,40 %** (BCE, taux directeur) |
| Inflation | 2,00 % | **2,00 %** (IPC France, moyenne 3 ans) |

L'inflation ne bouge pas aujourd'hui : la moyenne trois ans tombe exactement
sur l'ancienne hypothèse. Le glissement annuel seul aurait donné 2,37 %, et
c'est précisément la volatilité qu'on ne veut pas dans une projection longue.

Le taux sans risque baisse de 0,10 point. Il intervient dans le rapport
rendement/risque affiché et dans le rendement attendu du verdict « objectif ».

## Alternatives considérées

### Option A — Prendre l'OAT 10 ans plutôt que le taux BCE

Écartée : l'OAT à 3,68 % est un taux long avec du risque de duration. Le taux
sans risque d'un raisonnement à horizon court est un taux court.

### Option B — Garder les constantes et les réviser à la main chaque année

C'est ce qu'on faisait. Aucune révision n'a eu lieu.

## Notes

- Sonde : `python -m app.data.probe` affiche l'âge de chaque série.
- L'API Eurostat sert un instantané en retard de plusieurs mois sur l'IPC ;
  c'est FRED qui relaie la série à jour (constaté par la sonde).
