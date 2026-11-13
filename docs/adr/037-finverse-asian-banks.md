# ADR-037 : Finverse, un troisième agrégateur pour les banques d'Asie

**Date** : 2026-10-27
**Statut** : accepté

## Contexte

Le compte DBS de Singapour n'apparaît nulle part : Powens et Enable Banking
ne couvrent que l'Europe. DBS ouvre une API aux entreprises, pas aux
particuliers. Finverse agrège Singapour, Hong Kong, la Malaisie et la Corée
(DBS, POSB, OCBC…) derrière une seule API.

## Décision

Finverse, sur le même contrat que les deux autres agrégateurs.

- **DTO neutres, `provider = finverse`** dans `bank_accounts` et
  `bank_transactions`. Dépenses, verdicts et briefing ne savent pas d'où
  vient une opération.
- **Une ligne `finverse_connections` par banque liée** (un user, un login
  Finverse). Le refresh token est le secret : chiffré au repos avec la même
  clé Fernet que le jeton Powens, échangé à chaque lecture contre un jeton
  frais, remplacé quand Finverse en rend un nouveau. Les comptes portent l'id
  de la ligne dans `raw_data["finverse_connection"]` pour être retirés avec
  elle.
- **Finverse Link choisit la banque.** Tangent ouvre le lien, Finverse
  renvoie un code en POST sur `/auth/finverse/callback`. Ce POST vient de
  leur domaine, sans cookie de session : l'état signé (JWT, 30 minutes) dit
  seul qui a lancé le parcours.
- **Finverse relit la banque lui-même** (`automatic_data_refresh`) ; le
  scheduler lit Finverse une fois par jour à 07:20, et « Synchroniser » à la
  demande.
- **Les opérations en attente sont ignorées** : elles changent d'id en
  passant, et feraient doublon.
- **Les secrets** (`FINVERSE_CLIENT_ID`, `FINVERSE_CLIENT_SECRET`) vivent dans
  les secrets GitHub Actions ; le déploiement les écrit dans `backend/.env`
  sur la VM, sans les afficher.

## Conséquences

L'application de test ne lie que la « testbank » de Finverse ; les vraies
banques demandent une activation chez Finverse. Les comptes gardent leur
devise (SGD, HKD…) : tant que les soldes ne sont pas convertis en euros, un
total qui mêle les devises est faux.

## Ce qu'on a refusé

**L'API DBS directe.** Réservée aux entreprises clientes de DBS.

**Un import CSV des relevés.** Un relevé oublié, c'est un mois qui manque ;
la vérité doit se mettre à jour seule.
