# ADR-038 : Les montants en devise comptent en euros, au cours de référence BCE

**Date** : 2026-10-27
**Statut** : accepté

## Contexte

Un compte DBS est en dollars de Singapour, une poche Revolut en dollars ou en
livres. Tangent additionnait leurs soldes et leurs dépenses comme des euros :
1 500 SGD comptaient pour 1 500 €, quand ils en valent environ 1 050.

## Décision

- **Tout total est en euros.** Patrimoine, dettes, groupes de comptes,
  dépenses par mois et par catégorie, revenus, dépense mensuelle des verdicts.
- **Le cours est le dernier cours de référence de la BCE** (`EXR/D.<devise>.EUR`),
  publié chaque jour ouvré pour une trentaine de devises, sans clé d'API. Le
  même cours sert pour tout l'historique : l'écart d'un mois à l'autre reste
  de quelques pour cent.
- **La devise est celle du compte.** Un montant est converti selon la devise
  du compte qui le porte, lignes de titres comprises.
- **Sans cours, le compte sort des totaux** au lieu de compter comme des
  euros. Si la BCE ne répond pas, le dernier cours lu sert encore.
- **Chaque compte s'affiche dans sa devise** (« 1 500,00 $SG »), avec son
  équivalent en euros en dessous.

## Conséquences

Les poches Revolut en devise, comptées jusqu'ici comme des euros, changent
de valeur dans les totaux. Un virement de mes euros vers mes dollars de
Singapour n'est pas reconnu comme interne : les deux montants diffèrent, il
compte comme une dépense d'un côté et un revenu de l'autre.

## Ce qu'on a refusé

**Le cours du jour de chaque opération.** Plus juste à la marge, mais une
série historique par devise et un calcul par opération pour un écart de
quelques pour cent.

**Une table de cours tenue à la main.** Elle vieillit sans prévenir.
