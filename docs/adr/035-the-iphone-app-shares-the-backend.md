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

Les retours des banques (Powens, Enable Banking) et Sign in with Apple suivent dans les lots suivants, sur le même principe : le backend reconnaît l'utilisateur par un état signé, pas par un cookie que le navigateur système n'a pas.

## Conséquences

### Positives

- Une seule base de code front, un seul backend, un seul comportement.
- Rien ne change pour le site : mêmes routes, même cookie, même durcissement.
- Le renouvellement glissant améliore aussi le site : plus de déconnexion surprise au septième jour.

### Négatives

- Le cookie persistant survit à la fermeture du navigateur : sur un ordinateur partagé, il faut se déconnecter.
- Capacitor ajoute trois paquets npm et un projet Xcode au dépôt ; la compilation iOS ne se fait que sur macOS.
- Le code d'échange est mémorisé en mémoire pour l'usage unique : valable pour une instance de backend, à revoir si l'on en fait tourner plusieurs.
