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

## Conséquences

### Positives

- Zéro dépendance ; le module tient en deux fichiers et des dictionnaires plats, lisibles par n'importe qui.
- Le français et l'anglais d'une même phrase sont sur deux lignes voisines : traduire ou relire se fait dans un seul fichier.
- Les tests unitaires couvrent la détection, l'interpolation, les pluriels et les formats des deux langues.

### Négatives

- Le choix de langue est local à l'appareil : le site et l'iPhone se règlent séparément (à faire suivre par le profil serveur quand le backend parlera anglais lui aussi : verdicts, briefing, e-mails).
- Tout texte en dur qui reste dans un composant est invisible en anglais tant qu'il n'est pas passé par `t()` ; la conversion se fait écran par écran.
- Pas de format de message riche (genre, ordinaux) ; si le besoin apparaît, il se traite au cas par cas.
