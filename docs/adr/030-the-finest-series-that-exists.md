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

**Les actions monde sont mesurées comme les autres.** L'étude donnait des
pic-à-creux de fin de mois ; la boucle mesure en quotidien. Deux conventions
dans un même tableau, c'est dix points d'écart sur le COVID entre une ligne
monde mesurée et une ligne monde déclarée. Ken French sert les rendements
quotidiens des marchés développés depuis 1990 ; convertis au cours BCE, ils
donnent les actions monde en euros au jour le jour, et le tableau passe sur
une seule convention.

**Les dates de chaque crise viennent de cette série.** Une borne de mois tapée
à la main ratait le creux : mars 2009 finit quinze points au-dessus de son 9.
La fenêtre déclarée n'est plus qu'un intervalle de recherche ; le pic et le
creux réels des actions monde en euros à l'intérieur en sortent, et toutes les
classes sont mesurées entre ces deux jours-là. Hors ligne, l'intervalle sert
tel quel.

**Les replis sont alignés sur la mesure**, comme pour le Nasdaq avant : un
même portefeuille donne le même chiffre connecté ou non. 1990 et 1998 gardent
les chiffres de l'étude, faute d'euro.

## Conséquences

Ce qui devient vrai : ajouter une classe ou une région ne demande plus aucune
vérification humaine, et les crises récentes sont mesurées sur les vraies lignes
du portefeuille plutôt que sur une moyenne de classe.

Ce qui change dans les chiffres : toutes les amplitudes bougent, parce que la
convention change — quotidien au lieu de fin de mois, vrai creux au lieu de fin
de mois. Les actions monde passent de −52,5 % à −56,0 % sur 2000-03, de −20,4 %
à −33,6 % sur le COVID. Les actions américaines, européennes, japonaises et
émergentes cessent d'emprunter l'amplitude du monde dès qu'une série les
couvre. Et un fait de l'étude ne tient plus en quotidien : 2025 n'est plus « la
devise, pas le marché » — le marché lui-même a perdu 15,6 % en dollars entre le
13 février et le 7 avril, la devise a ajouté quatre points.

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
