# ADR-032 : Enable Banking, un second agrégateur pour les banques hors Powens

**Date** : 2026-09-14
**Statut** : accepté

## Contexte

Revolut n'est pas dans le catalogue Powens. Ses dépenses manquaient à
l'onglet Dépenses, et les virements vers Revolut y passaient pour des sorties.
L'API Revolut est réservée aux prestataires agréés PSD2 (certificat eIDAS) ;
un particulier ne peut pas l'appeler. Les relevés par mail n'existent pas côté
Revolut particulier. GoCardless Bank Account Data ne prend plus de nouveaux
comptes depuis juillet 2025.

## Décision

Enable Banking, agrégateur PSD2 agréé, en **mode restreint** : l'application
de production n'est active que pour les comptes que le propriétaire a liés
dans la console Enable Banking. Ce mode est prévu par eux pour « individual
non-commercial use », sans contrat ni vérification d'entreprise.

- **Même contrat que Powens** : `IBankAggregator`, DTO neutres, tables
  `bank_accounts` / `bank_transactions` avec `provider = enablebanking`.
  L'onglet Dépenses et les verdicts ne savent pas d'où vient une opération.
- **Une ligne `enablebanking_sessions` par consentement** (un user, une
  banque) ; l'identifiant de session est le secret, chiffré au repos avec la
  même clé Fernet que le jeton Powens. Les comptes portent l'id de la ligne
  dans `raw_data`, comme `id_connection` chez Powens, pour être retirés avec
  elle.
- **Le consentement dure 180 jours** au plus (règle PSD2) ; passé
  `valid_until`, l'écran Comptes dit « à reconnecter ». Pas de renouvellement
  silencieux possible.
- **L'historique complet est lu au retour du consentement**, dans la fenêtre
  de quelques minutes où la banque l'autorise ; ensuite le scheduler relit
  le mois glissant une fois par jour (la règle PSD2 en autorise quatre).
- **Le choix se fait à l'ajout d'une banque** : Revolut par Enable Banking,
  tout le reste par Powens. Le nom de la banque est un paramètre ; rien
  n'est codé en dur côté serveur.

## Conséquences

Le plan gratuit ne couvre que les comptes du propriétaire de l'application.
Le code est par utilisateur comme le reste, mais servir d'autres personnes
demande un contrat chez Enable Banking. Les secrets (`ENABLEBANKING_APP_ID`,
`ENABLEBANKING_PRIVATE_KEY_B64`) vivent dans `backend/.env` sur la VM.

## Ce qu'on a refusé

**Un import CSV manuel.** Un relevé qu'on oublie de déposer est un mois de
dépenses qui manque ; la vérité doit se mettre à jour seule.

**Lire une boîte mail.** Revolut n'envoie rien de planifié, et un robot qui
lit des relevés dans un mail est fragile et met des données bancaires dans
un mail.
