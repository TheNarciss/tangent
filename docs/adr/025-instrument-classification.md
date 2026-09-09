# ADR-025: Ce qu'est un instrument, décidé sur son nom officiel

- **Status** : accepted
- **Date** : 2026-09-09
- **Deciders** : Clem

## Contexte

Le diagnostic affiché sur l'écran Placements répondait à deux questions de
fond par des statistiques, et se trompait dès qu'on changeait de portefeuille.

« Ces deux fonds font doublon » était décidé par une corrélation au-dessus de
0,85, calculée sur chaque paire. Trois trackers monde donnaient trois cartes
disant la même chose ; six lignes en donnaient quinze. Et la corrélation est
une mesure indirecte : deux trackers du même indice ne sont pas *corrélés*,
ils sont *identiques*.

« Une seule ligne pèse 60 % » se déclenchait sur n'importe quelle ligne. Un
utilisateur détenant un seul ETF monde à 100 % — la recommandation la plus
répandue — recevait une alerte de concentration.

« Sur une mauvaise année, une baisse de 30 à 40 % est possible » était une
phrase figée, servie à l'identique pour un portefeuille à 21 % de volatilité
et pour un à 45 %.

Enfin les seuils du rapport rendement/risque, 0,30 et 0,60, encadraient une
valeur parfaitement normale : sur 1928-2025, les actions américaines affichent
0,43 (Damodaran). Un portefeuille de marché était donc classé « ni bon ni
mauvais », et un peu en dessous « critique ».

## Décision

Un module `finance/classification.py` répond à deux questions factuelles :
**est-ce un fonds ou une action ?** et **quel indice suit-il ?**

- Le nom officiel vient d'**OpenFIGI** quand on a l'ISIN, du libellé de la
  banque sinon. `securityType2` distingue un fonds d'une action.
- Les motifs de reconnaissance vivent dans `config/asset_classes.yaml`, avec
  un drapeau `broad` : un indice monde est large, un Nasdaq-100 ou un or
  physique ne l'est pas.
- Un instrument non reconnu reste `unknown` et le texte le dit. C'est le
  point important : l'ancien comportement rangeait tout en actions monde.

Le diagnostic est réécrit dessus, et ses seuils partent dans
`config/diagnostic.yaml` :

| Règle | Avant | Après |
|---|---|---|
| Doublons | une carte par paire corrélée > 0,85 | une carte par **indice** partagé, nommant tous les fonds |
| Concentration | toute ligne > 40 % | seulement une ligne **non diversifiée** (action isolée, fonds sectoriel, inconnu) |
| Mauvaise année | « 30 à 40 % » figé | pire année **réellement observée** sur la classe dominante (Ken French), sinon 1,65 σ, et le texte dit lequel |
| Rendement/risque | seuils 0,30 / 0,60 | écart à la **référence de long terme 0,43**, avec une marge de 0,25 pour l'erreur d'estimation |
| Nombre de cartes | illimité | plafonné, les plus graves d'abord |

## Conséquences

### Positives

- Les quatre règles tiennent pour un portefeuille quelconque : trois fonds
  monde donnent une carte, une action isolée à 60 % est signalée, un ETF monde
  à 100 % ne l'est pas.
- La baisse annoncée est un chiffre daté et sourcé. Pour les actions monde,
  la pire année depuis 1990 est −46,9 %, pas « 30 à 40 % ».
- Les seuils sortent du code et portent leur justification.
- L'écran affiche l'indice suivi sous chaque ligne, donc l'utilisateur voit
  lui-même les doublons.

### Négatives

- La reconnaissance repose sur des motifs textuels : un fonds au nom exotique
  restera `unknown`. C'est visible dans l'interface, pas silencieux.
- Un appel réseau de plus sur le tableau de bord (OpenFIGI, puis Ken French
  pour la pire année). Les deux sont en cache et **dégradent proprement** :
  OpenFIGI indisponible → on retombe sur le libellé de la banque ; pas
  d'historique long → on retombe sur le calcul par la volatilité.
- La règle de concentration ne dit plus rien d'un portefeuille fait d'un seul
  fonds monde. C'est voulu, mais ça retire une alerte à laquelle l'utilisateur
  actuel était habitué.

## Alternatives considérées

### Option A — Garder la corrélation, mais grouper les paires

Regrouper les paires corrélées en composantes connexes. Écartée : ça corrige
le symptôme (le nombre de cartes) sans corriger la cause (une corrélation
élevée n'est pas un doublon, et deux fonds identiques peuvent afficher 0,84 sur
une fenêtre courte).

### Option B — Demander la classe d'actifs au gap-filler LLM

Écartée pour ce besoin : le nom officiel suffit, il est gratuit, déterministe
et vérifiable. Le LLM reste la bonne réponse pour le TER, qui n'est écrit nulle
part ailleurs que dans le DIC.

## Notes

- Référence 0,43 : Damodaran, actions américaines 1928-2025, via `app/data`.
- Pire année actions monde depuis 1990 : −46,9 % (Ken French).
- Voir ADR-024 pour les sources.
