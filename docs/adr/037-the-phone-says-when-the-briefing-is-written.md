# ADR-037: Le téléphone prévient quand le briefing est écrit, et rien d'autre

- **Status** : accepted
- **Date** : 2026-09-18
- **Deciders** : Clem

## Contexte

Le briefing du matin est écrit dans la nuit par un lot LLM (ADR-018). Personne ne le sait avant d'ouvrir l'app, donc un texte écrit à trois heures du matin attend souvent la fin de la journée. Une notification règle ça.

Une app finance qui notifie est regardée de près : Apple refuse les notifications commerciales sans consentement séparé, et une notification qui affiche un montant sur un écran verrouillé expose le patrimoine de la personne à qui regarde par-dessus son épaule.

## Décision

Une seule notification existe : **« ton briefing du matin est prêt »**, envoyée quand le briefing vient d'être écrit pour cette personne.

| Point | Choix |
|---|---|
| Contenu | une phrase fixe, dans la langue de la personne. **Jamais un chiffre, jamais un nom.** Ce dont il s'agit est dans l'app, derrière Face ID |
| Consentement | une case dans « Mon compte », sous l'interrupteur du briefing, et seulement là. Rien n'est demandé au lancement |
| Adresse du téléphone | table `device_tokens` : le jeton APNs, en clair (c'est une adresse, pas un secret), unique, avec la langue que l'app affichait |
| Langue | celle enregistrée par l'appareil : la nuit, aucune requête ne porte d'en-tête `Accept-Language` |
| Envoi | `app/push.py` : JWT ES256 signé par la clé APNs, HTTP/2 vers Apple, jeton réutilisé trois quarts d'heure comme Apple le demande |
| Jeton mort | Apple répond `BadDeviceToken`, `Unregistered` ou `DeviceTokenNotForTopic` → la ligne est supprimée sur-le-champ |
| Empilement | un `apns-collapse-id` fixe : le briefing du jour remplace celui d'hier sur l'écran verrouillé |
| Panne | pas de clé, Apple injoignable, jeton refusé : c'est journalisé et le briefing est écrit quand même. Une notification n'est pas l'application |
| Déconnexion | le jeton est oublié côté serveur ; le réglage iOS, lui, appartient à la personne |

Le seul ajout de dépendance est `httpx[http2]` : APNs ne parle que HTTP/2, et `httpx` était déjà là.

## Conséquences

### Positives

- Le briefing est lu le matin plutôt qu'au hasard d'une ouverture.
- Rien de confidentiel ne sort de l'app : la notification dit qu'il y a quelque chose à lire, pas ce qu'il y a dedans.
- La liste des téléphones se nettoie toute seule, sans tâche d'entretien.

### Négatives

- Une capacité Push sur l'App ID et une clé APNs à créer dans le portail Apple, donc un profil de provisionnement à régénérer (`docs/ios-app-store.md`).
- Le briefing reste réservé aux administrateurs (ADR-018) : la plomberie existe, mais elle ne prévient aujourd'hui que ceux qui reçoivent un briefing.
- Deux appareils d'une même personne dans deux langues reçoivent chacun la sienne, ce qui est voulu, mais le briefing lui-même n'est écrit que dans la langue du profil.
