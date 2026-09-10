# ADR-028: Une seule voix par question, un seul sujet par écran

- **Status** : accepted
- **Date** : 2026-09-10
- **Deciders** : Clem

## Contexte

Trois moteurs parlaient en même temps, sans savoir ce que les autres disaient :

- les **verdicts** (ADR-023), qui concluent avec un feu et un montant par an ;
- le **diagnostic**, un moteur de règles qui produisait des « insights » ;
- l'**optimiseur**, qui proposait des arbitrages.

Sur un écran réel, ça donnait : *« ton profil vise 100 % d'actions, tu es dans
la bande, rien à changer »*, et deux blocs plus bas *« place 1 273 € sur ton
Livret A Jeune, allège les cinq lignes »*. L'utilisateur devait arbitrer
lui-même entre deux systèmes qui se contredisent.

À quoi s'ajoutait une répétition dans l'espace : le risque était expliqué à
trois endroits, la baisse sur trois écrans avec cinq chiffres, le gain sous
trois notions différentes sans que rien ne dise laquelle regarder.

## Décision

**Une seule voix.** Les verdicts concluent, seuls.

- Le diagnostic devient le verdict `diversification` (« Répartition ») : les
  doublons d'indice et les lignes non diversifiées, lues sur ce qu'est chaque
  ligne (ADR-025) et non sur des statistiques. `finance/diagnostic.py` et le
  champ `insights` de l'API disparaissent.
- Les deux règles restantes du diagnostic sont abandonnées, et il faut le dire :
  la « mauvaise année » est déjà affichée comme un chiffre daté (pire année
  réelle de la classe), et le « risque rémunéré » comparait un Sharpe estimé sur
  cinq ans à un seuil que sa propre marge d'erreur rendait ininterprétable.
- L'optimiseur n'est plus un bloc autonome : il devient le détail du verdict
  « part d'actions », **et n'apparaît que si ce verdict n'est pas vert**. Un
  écran ne peut plus proposer de tout vendre sous une phrase disant que tout va
  bien.

**Un sujet par écran.**

| Écran | Question | Contenu |
|---|---|---|
| Aperçu | où j'en suis ? | patrimoine, courbe, briefing, et **les verdicts non verts uniquement** |
| Placements | qu'est-ce que je détiens ? | la répartition et les lignes. **Aucun conseil** |
| Méthode | qu'est-ce que j'en fais ? | tous les verdicts, tout le raisonnement |
| Projection | où ça mène ? | inchangé |

**L'ordre est le conseil.** `compute_all` trie : rouge, orange, incomplet, vert,
et à statut égal le plus gros montant par an d'abord. La Méthode se lit de haut
en bas, l'Aperçu n'affiche que le haut de cette liste.

## Conséquences

### Positives

- Deux écrans ne peuvent plus se contredire : un seul moteur conclut.
- Placements passe de cinq blocs à deux ; l'Aperçu n'affiche que ce qui cloche.
- Le verdict « Répartition » ne dit jamais de vendre — orienter les prochains
  versements ne coûte ni courtage ni impôt sur la plus-value.
- Un verdict de plus dans le briefing, sans rien y brancher : il lit la même
  liste.

### Négatives

- Le « risque rémunéré » disparaît de l'interface. C'est une suppression
  assumée, pas un oubli.
- La Méthode porte maintenant tout : elle est longue. Les cartes sont repliées
  et triées, mais c'est l'écran à surveiller si ça devient lourd.
- L'ordre dépend de `impact_eur_per_year`, que tous les verdicts ne remplissent
  pas. Ceux qui ne le remplissent pas se rangent après leurs pairs de même
  couleur ; c'est acceptable, pas satisfaisant.

## Alternatives considérées

### Option A — Garder les trois moteurs et harmoniser leurs textes

Écartée : ça masque la contradiction au lieu de la supprimer. Deux moteurs qui
calculent séparément finiront toujours par diverger.

### Option B — Un seul écran « Ce qu'il faut faire »

La conclusion logique de cette décision. Écartée pour l'instant : elle redéfinit
la navigation entière, et l'ordre par priorité introduit ici en donne déjà
l'essentiel.

## Notes

- Voir ADR-023 (contrat de verdict), ADR-025 (ce qu'est un instrument).
