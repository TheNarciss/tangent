# ADR-034: L'archive : tout ce que l'app sait, écrit deux fois par jour

- **Status** : accepted
- **Date** : 2026-09-15
- **Deciders** : Clem

## Contexte

Tangent calcule beaucoup et ne garde presque rien. Les positions sont écrasées à chaque synchronisation, les prix sont lus à la demande et oubliés, les verdicts et le tableau de bord sont recalculés à chaque écran. Seule la valeur du patrimoine est relevée chaque nuit (`portfolio_snapshots`). Le jour où l'on veut regarder en arrière avec précision — ce que l'app voyait le 3 mars, ce que valait telle ligne ce soir-là, ce que la méthode concluait — il n'y a rien.

La contrainte est double. Les données personnelles (comptes, positions, profil, dépenses) ne doivent pas s'accumuler en clair dans une table qui grossit chaque jour ; l'ADR-012 a déjà tranché pour les tokens bancaires : chiffrés au repos, clé hors base. Et les données publiques (prix, taux, liste de l'année, pistes) doivent rester lisibles en SQL, sinon la base ne sert à rien.

## Décision

Deux fois par jour, à 07:45 (après la synchronisation bancaire de 07:15) et à 19:30 (Paris), un job écrit dans `data_snapshots` :

| Ligne | Portée | Contenu | Stockage |
|---|---|---|---|
| une par utilisateur et par créneau | `user` | profil, patrimoine, résumé, comptes, positions, dépenses (3 mois), performance, liste de suivi, dernier briefing, verdicts, tableau de bord | `sealed` : jeton Fernet du JSON, clé `ARCHIVE_ENCRYPTION_KEY` |
| une par créneau | `market` | dernier cours de chaque ligne détenue par quelqu'un et des indices, taux directeur, inflation, liste de l'année, pistes de marché | `payload` : JSONB en clair |

Un créneau rejoué remplace sa ligne (deux index uniques partiels). La clé vit dans `.env` et nulle part ailleurs ; sans elle, rien de personnel n'est écrit, la ligne marché l'est quand même, et le journal dit pourquoi. L'échec d'un utilisateur ne coûte que sa ligne.

Le JSON personnel est produit par les mêmes fonctions que les écrans (`get_user_wealth`, `build_summary`, `build_spending`, `verdicts.compute_all`, `dashboard.build`) : l'archive dit exactement ce que l'app disait. Le tableau de bord et les verdicts sont au mieux : une source hors de portée laisse une note, jamais un trou dans la ligne.

Aucun écran ne montre l'archive : ce n'est pas une chose à regarder, c'est une matière pour des questions qu'on ne sait pas encore poser. Une seule route la lit : l'export de données (`GET /api/export`) rend à la personne l'intégralité de ses lignes, ouvertes avec la clé, puisque ce sont ses données. La partie marché se lit en SQL.

## Conséquences

### Positives

- Une base historique qui grossit d'elle-même, prête pour des calculs qu'on n'a pas encore imaginés.
- Le personnel est illisible sans la clé : une fuite de la base ne livre que des jetons.
- Le public est en clair : `SELECT payload->'prices'->'CW8.PA'` marche.

### Négatives

- Une ligne utilisateur pèse quelques dizaines de Ko, deux fois par jour : à surveiller par `size_bytes`.
- Le job du matin lit les prix (Yahoo) : une panne de source laisse une note dans `prices_error`, le créneau n'est pas rejoué automatiquement.
- Perdre la clé, c'est perdre toute l'archive personnelle. Elle se sauvegarde avec le `.env`.
