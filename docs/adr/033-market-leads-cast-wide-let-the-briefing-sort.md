# ADR-033: « Pistes de marché » : ratisser large, laisser le briefing trier

- **Status** : accepted
- **Date** : 2026-09-15
- **Deciders** : Clem

## Contexte

Tangent sait dire ce que l'épargnant détient et ce que la méthode en pense. Il ne sait rien de ce qui se passe autour : des dirigeants qui achètent l'action de leur propre société, un grand gérant qui solde une ligne, un pari collectif sur la prochaine décision de la Fed qui se retourne en une semaine. Ce sont des faits déclarés par des gens qui engagent leur argent, publics, et personne ne les lit pour lui.

L'envie de départ était de « récupérer les signaux de traders connus » sur les réseaux, et Polymarket. Le premier n'existe pas proprement : ni API gratuite ni légale sur X, eToro ou TradingView, un contenu non structuré, et c'est précisément là qu'est le bruit. Le second existe, et à côté de lui deux sources officielles disent la même chose en mieux : ce que les gens *font*, pas ce qu'ils disent.

La contrainte reste celle de l'ADR-024 : des sources qui se lisent seules, sans clé ni compte, et rien de recopié à la main. Et celle de l'ADR-031 : Tangent n'émet pas d'opinion, il applique une règle publiée. Une piste n'est jamais un ordre.

## Décision

Chaque nuit, un job ratisse trois sources et écrit tout ce qui dépasse un seuil dans `data/market_leads.json`, sans juger. Le briefing du matin reçoit la liste brute et en garde zéro à trois, avec la raison ; le reste est jeté. Le bruit est voulu en amont : c'est le tri qui fait la valeur, et il se fait au dernier moment, par le seul composant qui connaît le patrimoine de la personne.

| Source | Ce qu'on lit | Ce qui devient une piste |
|---|---|---|
| Polymarket (API Gamma) | les événements portant une étiquette économique (`fed`, `recession`, `oil`…), leurs marchés, cotes et volumes | une cote qui bouge de plus de N points en une semaine ; l'issue la plus probable des marchés les plus échangés, comme état des attentes |
| SEC EDGAR, Form 4 | chaque dépôt du jour, un document par dépôt | plusieurs dirigeants distincts qui achètent en bourse la même action en trente jours ; un achat isolé au-dessus d'un montant |
| SEC EDGAR, 13F-HR | le dernier tableau de positions de gérants suivis, comparé au précédent | une ligne ouverte, une ligne soldée, une variation forte du nombre de titres, sur les grosses positions seulement |

Les seuils, les étiquettes et la liste des gérants suivis vivent dans `config/market_leads.yaml`. Ce sont des règles ; aucune piste, aucun chiffre de marché n'y est écrit.

Le périmètre est mondial dès le départ, États-Unis compris, alors que l'univers de la liste de l'année est européen : il s'agit de ratisser, pas de sélectionner. Une piste sur une société américaine peut concerner un fonds Monde.

Le job tourne à 02:15 (Paris), avant le lot de briefings de 03:00. Un administrateur peut le lancer à la demande. Une source hors de portée coûte ses pistes, jamais celles des autres. `GET /api/market-leads` sert la liste brute ; il n'y a pas d'écran pour l'instant, le briefing est la première interface. Un onglet sous Placements viendra si les pistes prouvent leur intérêt.

Le system prompt du briefing gagne une section « Pistes à regarder » : garder ce qui peut concerner un épargnant en fonds indiciels (taux, récession, inflation, un secteur ou une région détenue), dire pourquoi, ne jamais transformer une piste en achat ou vente, ne citer une société que comme un fait déclaré.

## Conséquences

### Positives

- Trois sources de vérité qui se mettent à jour seules, sans clé, dans l'esprit de l'ADR-024.
- Le tri est fait par le composant qui connaît le patrimoine ; le même fait est retenu pour l'un et ignoré pour l'autre.
- Les règles sont lisibles et modifiables sans code ; les pistes brutes sont consultables pour vérifier ce que le tri a laissé.
- Rien ne pousse à agir : le briefing reste « rien à faire, continue tes versements » sauf raison structurelle.

### Négatives

- EDGAR se lit dépôt par dépôt : un millier de requêtes par nuit, à dix par seconde au plus, quelques minutes de travail et une dépendance à la disponibilité de la SEC.
- Un 13F arrive 45 jours après le trimestre : c'est un fait daté, pas une nouvelle.
- Polymarket est dominé par la politique et le sport ; le filtre par étiquettes laisse passer des marchés sans intérêt, que le briefing devra ignorer.
- Le tri repose sur le modèle : un mauvais matin, il gardera une piste sans intérêt ou en ratera une. La liste brute permet de le constater.
- Les déclarations de dirigeants européens (AMF, BaFin) ne sont pas lues : pas d'API exploitable.

## Alternatives considérées

### Option A — Les « signaux de traders » sur les réseaux

Pas d'API gratuite ni légale, contenu non structuré, aucune trace de ce que la personne a réellement fait de son argent. Écartée.

### Option B — Un fournisseur payant de données alternatives (Quiver, Finnhub, FMP)

Ils agrègent les mêmes sources publiques et y ajoutent une clé et une facture. Contraire à l'ADR-024. Écartée.

### Option C — Trier par des règles plutôt que par le briefing

Une règle qui décide qu'un achat d'initié « compte » pour telle personne aurait besoin de connaître son patrimoine, ses fonds, sa tolérance : c'est déjà ce que le briefing sait. Les règles ne font que fixer les seuils de collecte ; le jugement reste au dernier maillon.

### Option D — Les transactions des élus américains (STOCK Act)

Publiques, mais servies en PDF et en archives à parser, avec des montants par tranche. Faisable, pas pour un premier pas. Réservée pour plus tard.

## Notes

- Polymarket, API Gamma : `https://gamma-api.polymarket.com/events?tag_slug=…`
- SEC EDGAR : index quotidien par type de formulaire, fiches par CIK, dossiers de dépôt. La SEC demande un User-Agent identifié et au plus dix requêtes par seconde.
- [ADR-024](024-external-data-sources.md) — sources externes, sans clé
- [ADR-031](031-the-list-of-the-year.md) — une règle publiée, pas une opinion
