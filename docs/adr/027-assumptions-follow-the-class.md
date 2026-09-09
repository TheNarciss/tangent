# ADR-027: Les hypothèses suivent la classe d'actifs, plus le ticker

- **Status** : accepted
- **Date** : 2026-09-09
- **Deciders** : Clem

## Contexte

Trois endroits décidaient du sort d'une ligne à partir de son **ticker**, et
chacun ne connaissait que les six tickers du premier utilisateur :

- `stress_scenarios.yaml` : une table `asset_classes` de six entrées, tout le
  reste rejoué en actions monde par défaut.
- `cma.yaml` : six hypothèses de rendement long terme. Le fonds monde de
  n'importe qui d'autre n'en avait aucune et retombait sur son µ historique
  5 ans, gonflé par le bull-run post-COVID.
- `timeseries.py` : un benchmark figé, `CW8.PA`, comparé à tout portefeuille,
  y compris obligataire.

Et une classe manquait complètement : **l'or**. Un détenteur d'ETC or voyait sa
ligne rejouée comme des actions monde, donc −48 % en 2008, alors que l'or a
gagné 32 % en euros pendant cet épisode.

## Décision

Les trois lisent la classe donnée par `finance/classification.py` (ADR-025).

**Stress.** La table de tickers disparaît, remplacée par `class_map` : classe
reconnue → classe rejouée. L'or devient une classe à part entière, avec ses
rendements calculés à partir des fixings LBMA (ADR-024) sur la fenêtre de
chaque épisode — en euros à partir de 1999, en dollars avant, la monnaie
n'existant pas. C'est la seule classe dont le chiffre est calculé et non
recopié de l'étude.

**CMA.** `cma.yaml` est indexé par classe. Les quatre valeurs existantes sont
conservées à l'identique, simplement rattachées à une classe au lieu d'un
ticker. Aucune valeur nouvelle n'est inventée : une classe sans hypothèse
garde son µ historique et l'app le signale, comme avant.

**Benchmark.** La courbe de référence n'apparaît que si les actions font plus
de la moitié du portefeuille. Comparer un portefeuille obligataire aux actions
monde est une comparaison sans objet ; mieux vaut pas de courbe qu'une courbe
trompeuse.

## Conséquences

### Positives

- N'importe quel tracker monde reçoit l'hypothèse « actions monde », pas
  seulement les six qui étaient listés.
- Un portefeuille avec de l'or ne perd plus 48 % en 2008 : il gagne.
- Un portefeuille obligataire n'est plus comparé aux actions.

### Négatives

- Toutes les actions se rejouent encore avec l'amplitude du monde : l'étude ne
  fournit pas de série par région et par épisode, donc un fonds Nasdaq est
  sous-estimé. C'est écrit sous le tableau.
- Les classes obligataire, émergente, japonaise, monétaire et or n'ont pas
  d'hypothèse de rendement long terme. Elles gardent leur µ historique — le
  comportement existant, appliqué à plus de monde.
- Un appel de classification de plus dans le chemin du tableau de bord. Il est
  mutualisé et dégrade sur le libellé de la banque.

### Effet sur les chiffres affichés

Aucun pour un portefeuille composé des six tickers connus : mêmes classes,
mêmes hypothèses, mêmes scénarios. Les changements ne concernent que ce qui
n'était pas couvert : l'or, et les fonds d'un autre utilisateur.

## Notes

- Or en euros par épisode, calculé depuis les fixings LBMA : 2008 **+32,1 %**,
  2011 **+19,7 %**, 2022 **+3,2 %** (le seul épisode où actions et obligations
  tombent ensemble).
- Voir ADR-024 (sources) et ADR-025 (classification).
