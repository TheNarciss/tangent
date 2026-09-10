# ADR-030: Chercher la série la plus fine qui existe, sans table tenue à la main

- **Status** : accepted
- **Date** : 2026-09-10
- **Deciders** : Clem

## Contexte

L'[ADR-029](029-measure-the-episodes.md) a remplacé la recopie de chiffres par
une boucle, mais la boucle ne savait lire que ce qu'un humain avait inscrit dans
un registre : deux classes, le NASDAQ 100 et l'or. Pour tout le reste, la
réponse était « quelqu'un devra vérifier à la main jusqu'où remonte l'indice,
puis l'ajouter ».

C'est le même défaut que la recopie, déplacé d'un cran. Une vérification
manuelle par classe ne tient pas plus qu'un calcul manuel par épisode : elle
n'est jamais faite, et les classes restent rejouées avec l'amplitude des actions
monde.

Il manquait surtout un niveau. Une ligne n'est pas sa classe : deux fonds
« actions Europe » n'ont pas le même cours, et pour les crises récentes, le
cours réel de la ligne existe. On le remplaçait par une moyenne alors qu'on
avait la mesure.

## Décision

Trois niveaux, essayés dans l'ordre, **aucun tenu à la main**.

1. **Le cours de la ligne elle-même.** OpenFIGI, déjà interrogé pour classer
   l'instrument, nomme aussi ses places de cotation et son symbole. Quand la
   place est lisible, Yahoo sert l'historique de cette ligne précise, et
   l'épisode est mesuré dessus. Aucune configuration : ça marche pour un titre
   que personne n'a jamais vu.
2. **L'indice de la classe.** `class_series` liste des *candidats* par classe ;
   la boucle garde le premier dont la série couvre la fenêtre, épisode par
   épisode. Personne ne vérifie une profondeur d'historique : la boucle essaie.
3. **Le chiffre déclaré** de l'étude, en dernier recours.

Une classe sans chiffre déclaré **emprunte** celui d'une autre
(`fallback_class`) au lieu de valoir zéro.

## Conséquences

Ce qui devient vrai : ajouter une classe ou une région ne demande plus aucune
vérification humaine, et les crises récentes sont mesurées sur les vraies lignes
du portefeuille plutôt que sur une moyenne de classe.

Ce qui change dans les chiffres : les actions américaines, européennes,
japonaises et émergentes cessent d'emprunter l'amplitude des actions monde dès
qu'une série les couvre. Les écarts peuvent être importants dans les deux sens.

Ce qui reste faux, et qu'aucun code ne corrigera : un ETF européen n'a pas
d'historique avant 2009. La bulle internet et 2008 resteront mesurées sur un
indice ou déclarées, parce que le fonds n'existait pas — ce n'est pas une limite
de la méthode, c'est le monde.

## Ce qu'on a refusé

**Deviner l'indice d'une ligne à partir de son nom.** Rapprocher un « Europe
hedged » du STOXX brut produit un chiffre faux avec l'air d'être mesuré, ce qui
est pire qu'un repli assumé. On ne mesure une ligne que sur *son propre cours*,
jamais sur un indice qu'on lui aurait attribué.

**Londres.** Certaines lignes y cotent en pence, d'autres en livres, et rien
dans la réponse d'OpenFIGI ne tranche. Une erreur d'un facteur cent est pire
qu'une mesure en moins : ces lignes retombent sur leur classe.

**Dépendre de Yahoo.** Aucun contrat de service : chaque silence est un repli,
jamais une erreur. Un test vérifie qu'un marché muet rend les mêmes chiffres
qu'avant, et qu'il n'est interrogé qu'une fois par ligne, pas une fois par
épisode.
