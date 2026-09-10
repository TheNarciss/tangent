# ADR-029: Mesurer les crises sur un indice, plutôt que recopier des chiffres

- **Status** : accepted
- **Date** : 2026-09-10
- **Deciders** : Clem

## Contexte

Les stress tests portaient un chiffre recopié à la main par classe et par
épisode. Deux conséquences.

D'abord, ça ne passe pas à l'échelle : ajouter une classe voulait dire
recalculer dix chiffres à la main, donc on ne les ajoutait pas. Une classe sans
chiffre empruntait silencieusement l'amplitude des actions monde.

Ensuite, ça mentait. Un tracker Nasdaq était rejoué à −52,5 % sur la bulle
internet, le chiffre des actions monde. Le NASDAQ 100 a réellement perdu
**82,2 %** sur cette fenêtre, en euros. Trente points d'écart, sur une ligne qui
pèse un cinquième d'un portefeuille réel.

J'avais écarté la correction en disant qu'aucune source ne servait ces séries.
C'était faux : **FRED sert le NASDAQ 100 en quotidien depuis 1986**, sans clé et
sans bridage. Je ne l'avais pas cherché.

## Décision

Une boucle remplace la recopie.

`config/stress_scenarios.yaml` gagne deux choses : une fenêtre lisible par
machine pour chaque épisode, et un registre `class_series` qui dit où trouver
un indice quotidien pour une classe.

Pour chaque classe déclarée et chaque épisode, `finance/episodes.py` mesure la
**baisse pic-à-creux à l'intérieur de la fenêtre**, puis la convertit en euros
au cours BCE **des deux jours qu'il a retenus**. C'est exactement la méthode
derrière les chiffres de l'étude, donc les deux se comparent dans le même
tableau.

Tout le reste retombe sur la valeur déclarée : une série qui ne remonte pas à
l'épisode, un fournisseur qui ne répond pas, une classe que personne n'a
encore mappée. L'écran dit lesquelles sont mesurées et lesquelles empruntent
l'amplitude du monde.

**Ajouter une classe, c'est ajouter trois lignes de YAML.** Rien à coder, rien
à recalculer.

## Conséquences

### Positives

- Un détenteur de Nasdaq voit enfin ce que sa ligne a vraiment pris.
- La couverture s'étend sans code : le jour où on trouve une série quotidienne
  pour l'Europe, elle se branche dans le registre.
- Les deux méthodes coexistent proprement puisqu'elles mesurent la même chose,
  et l'interface nomme les classes de chaque camp.

### Négatives

- Un appel réseau de plus par épisode. Il est mutualisé, mis en cache par
  `app/data`, et dégrade sur la valeur déclarée.
- L'Europe et le Japon restent déclarés : FRED ne les sert qu'en mensuel
  (séries OECD), et une fenêtre en fin de mois ne se compare pas à un
  pic-à-creux. Une série quotidienne, ou rien.
- Avant 1999 il n'y a pas de cours à appliquer : 1990 et 1998 restent sur la
  valeur déclarée, en dollars, et le fichier le dit.

### ⚠️ Effet sur les chiffres affichés

Pour une ligne classée `equity_us_tech`, les pertes affichées **augmentent
nettement** :

| Épisode | Avant (amplitude monde) | Après (NASDAQ 100 réel) |
|---|---|---|
| Bulle internet 2000-03 | −52,5 % | **−82,2 %** |
| Inflation 2022 | −14,2 % | **−24,3 %** |
| Q4 2018 | −12,7 % | **−21,5 %** |
| COVID 2020 | −20,4 % | **−27,4 %** |
| Crise 2008 | −48,2 % | −46,7 % |

Ce ne sont pas des hypothèses revues : ce sont les chiffres qui manquaient.

## Alternatives considérées

### Option A — Des ratios d'amplitude mesurés sur Ken French

Écartée après mesure : les ratios par épisode changent de signe selon la
fenêtre (Japon −0,19× en 2011, Europe 0,08× en 2025). Fenêtres mensuelles
appliquées à des chiffres pic-à-creux : des artefacts, pas des mesures.

### Option B — Continuer à recopier, classe par classe

C'est ce qu'on faisait, et c'est ce qui a produit l'écart de trente points.

## Notes

- Source : `NASDAQ100` sur FRED, quotidien depuis 1986-01-02.
- Voir ADR-024 (sources), ADR-027 (les hypothèses suivent la classe).
