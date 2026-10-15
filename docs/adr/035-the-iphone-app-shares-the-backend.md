# ADR-035: L'app iPhone est le site, dans une coque native, sur le même backend

- **Status** : accepted
- **Date** : 2026-09-15
- **Deciders** : Clem

## Contexte

Tangent doit exister sur l'App Store, pour iPhone. Le site est déjà pensé pour le téléphone (navigation basse, écrans à 390 px) et tout ce qui compte vit dans le backend. Réécrire le front en Swift doublerait le travail et ouvrirait deux comportements. La règle est simple : **l'app et le site font la même chose, parce qu'ils parlent au même backend avec le même code**.

Apple pose ses conditions : une app qui n'est qu'un site dans une fenêtre est refusée (règle 4.2) ; si l'on propose Google, il faut proposer Sign in with Apple (4.8) ; les connexions OAuth passent par le navigateur système, pas par une vue web ; une app finance est regardée de près.

## Décision

L'app est le build web actuel embarqué dans **Capacitor**, avec ce que le natif apporte de vrai : Face ID à l'ouverture, écran flouté en arrière-plan, navigateur système pour les connexions, retour à l'app par lien. Les appels HTTP de la coque passent par la pile native du téléphone (`CapacitorHttp`), qui garde et renvoie le cookie de session comme un navigateur : **l'authentification par cookie ne change pas**. Le backend s'adapte sur trois points, valables pour le site aussi :

| Point | Avant | Maintenant |
|---|---|---|
| Durée du cookie | cookie de session, effacé à la fermeture du navigateur | persistant, sept jours ; le jeton reste le plafond |
| Session utilisée | expirait au bout de sept jours quoi qu'il arrive | renouvelée sur `GET /api/users/me` dès que le jeton a plus d'un jour : une session qui sert reste ouverte, une session oubliée meurt |
| Connexion OAuth depuis l'app | impossible : le navigateur système ne partage pas ses cookies avec l'app | `GET /api/auth/app/google/start?challenge=` ouvert dans le navigateur système ; au retour, le backend renvoie vers `tangent://auth?code=` un **code d'échange** de 60 s, à usage unique, lié au challenge PKCE que l'app a créé ; `POST /api/auth/exchange {code, verifier}` ouvre la session dans l'app |

Le code d'échange ne vaut rien sans le verifier resté dans l'app : un autre programme qui capterait le schéma `tangent://` n'en ferait rien. Le cookie lui-même ne transite jamais par une URL.

Sign in with Apple suit le même principe, en tenant compte de ce qu'Apple fait autrement : retour par POST, `id_token` vérifié contre ses clés publiées, client secret signé par le serveur ; depuis l'app, l'`id_token` obtenu nativement se poste sur `/api/auth/apple/native`. Les retours des banques (Powens, Enable Banking) suivent : le backend reconnaît l'utilisateur par un état signé, pas par un cookie que le navigateur système n'a pas.

Le widget d'écran d'accueil suit la même règle que le reste : il n'a ni session ni accès au backend. L'Aperçu lui tend ce qu'il affiche déjà, libellé et montant écrits dans la langue de la personne, et le plugin le dépose dans un App Group que l'extension lit. Le widget ne fait que peindre : pas de traduction ni de format de nombre réécrits en Swift, pas d'authentification à dupliquer, et rien à afficher tant que personne n'a ouvert l'app ou après une déconnexion.

La coque vit dans `frontend/ios` (projet Xcode, Swift Package Manager, iOS 15+) et tient en quatre fichiers Swift à nous : un plugin `TangentNative` (Face ID via LocalAuthentication, navigateur sécurisé via ASWebAuthenticationSession, Sign in with Apple via AuthenticationServices), le contrôleur qui l'enregistre, et un flou posé sur la fenêtre dès que l'app passe en arrière-plan. Côté web, `src/native` expose la même chose et ne fait rien sur le site. Pas de plugin tiers au-delà de `@capacitor/app` (liens entrants, état de l'app). Le manifeste de confidentialité déclare ce que l'app collecte (e-mail, informations financières, identifiant) sans aucun suivi.

## Conséquences

### Positives

- Une seule base de code front, un seul backend, un seul comportement.
- Rien ne change pour le site : mêmes routes, même cookie, même durcissement.
- Le renouvellement glissant améliore aussi le site : plus de déconnexion surprise au septième jour.

### Négatives

- Le cookie persistant survit à la fermeture du navigateur : sur un ordinateur partagé, il faut se déconnecter.
- Capacitor ajoute quatre paquets npm et un projet Xcode au dépôt ; la compilation iOS ne se fait que sur macOS, et le Swift écrit ici n'est vérifié qu'à cette compilation.
- Le widget impose un App Group et un second identifiant d'app, donc deux profils de provisionnement au lieu d'un (`docs/ios-app-store.md`). Le chiffre qu'il montre date de la dernière ouverture de l'app, ce que la ligne « il y a … » dit explicitement plutôt que de le taire.
- Le code d'échange est mémorisé en mémoire pour l'usage unique : valable pour une instance de backend, à revoir si l'on en fait tourner plusieurs.
