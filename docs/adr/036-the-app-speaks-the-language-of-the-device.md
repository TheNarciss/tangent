# ADR-036: L'app parle la langue de l'appareil, en français ou en anglais, sans bibliothèque

- **Status** : accepted
- **Date** : 2026-09-16
- **Deciders** : Clem

## Contexte

Tangent était écrit en français, dans le code, texte par texte. L'App Store et le site s'adressent aussi à des gens qui lisent l'anglais. La règle voulue : **celui dont le navigateur ou le téléphone est en anglais lit l'anglais, les autres lisent le français**, sans rien demander ; et celui qui veut l'autre langue la choisit dans « Mon compte ».

Une bibliothèque (i18next, react-intl, lingui) apporterait des formats de messages, des plugins de détection, des chargements par fichier, pour deux langues et une seule équipe. Le dépôt a pour règle de ne pas ajouter de dépendance sans besoin.

## Décision

Une solution maison, dans `frontend/src/i18n` :

| Point | Choix |
|---|---|
| Langues | `fr` et `en`, sans variante ; le français est le repli |
| Détection | `navigator.languages` : la première entrée anglaise donne l'anglais, tout le reste donne le français |
| Choix explicite | « Mon compte › Langue » : Automatique / Français / English ; gardé dans `localStorage` (`tangent.locale`), donc **par appareil** ; « Automatique » efface le choix |
| Dictionnaires | un fichier par domaine (`messages/nav.ts`, `auth.ts`, `account.ts`, …) qui contient le français **et** l'anglais côte à côte ; le type de l'anglais est `Record<keyof typeof fr, string>` : une clé manquante ne compile pas |
| Lecture | `t("nav.overview")`, avec des trous `{name}` ; `tn("clé", n)` choisit `.one` / `.other` selon `Intl.PluralRules` de la langue ; `useT()` abonne le composant au changement de langue |
| Nombres et dates | `Intl` avec `fr-FR` ou `en-GB` (`€1,234.50`, `3 March 2026`) ; les formateurs de `lib/format.ts` et `lib/accounts.ts` lisent la langue en vigueur |
| Changement à chaud | la racine de l'app est remontée (`key={locale}`) : tout se relit, y compris ce qui est calculé hors hooks ; l'URL garde la page |
| `<html lang>` | suit la langue en vigueur, pour le navigateur et les lecteurs d'écran |

Les identifiants de routes (`/comptes`, `/placements`) restent en français : ce sont des adresses, pas du texte, et les liens partagés continuent de marcher.

Le backend suit la même règle, avec le même module maison en Python (`app/i18n`, dictionnaires `messages/*.py`, un test vérifie que l'anglais reflète le français) :

| Point | Choix |
|---|---|
| Langue d'une requête | l'en-tête `Accept-Language`, que le front envoie avec la langue affichée ; dépendance FastAPI `current_locale` |
| Langue des tâches sans requête | `profiles.locale`, écrit par le front à chaque synchronisation du profil ; le briefing du matin et l'archive le lisent |
| Verdicts | titres, phrases et actions par `t(locale, clé)` ; nombres en `€1,500` / `7.5%` en anglais |
| Stress tests, crans de risque | `label_en` / `description_en` à côté du français dans les YAML, choisis à la lecture |
| Briefing | un prompt système par langue, mêmes règles et même structure ; le texte généré est dans la langue de la personne |
| Erreurs HTTP, e-mail de réinitialisation | par `t()` dans la langue de la requête |
| Pages légales | `public/legal/en/` traduites ; les liens de l'app suivent la langue, chaque page renvoie vers son jumeau |

## Conséquences

### Positives

- Zéro dépendance ; le module tient en deux fichiers et des dictionnaires plats, lisibles par n'importe qui.
- Le français et l'anglais d'une même phrase sont sur deux lignes voisines : traduire ou relire se fait dans un seul fichier.
- Les tests unitaires couvrent la détection, l'interpolation, les pluriels et les formats des deux langues.

### Négatives

- Le choix de langue est local à l'appareil : le site et l'iPhone se règlent séparément ; le serveur retient la dernière langue synchronisée pour le briefing et l'archive, donc deux appareils dans deux langues se disputent celle du briefing.
- Tout texte en dur qui reste dans un composant est invisible en anglais tant qu'il n'est pas passé par `t()` ; la conversion se fait écran par écran.
- Pas de format de message riche (genre, ordinaux) ; si le besoin apparaît, il se traite au cas par cas.
