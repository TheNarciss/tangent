# ADR-031 : « La liste de l'année » — une règle publiée, pas une opinion

- **Status** : accepted
- **Date** : 2026-09-13
- **Deciders** : Clem

## Contexte

L'utilisateur veut que l'app dise « cette année, achète ceux-là, vends
ceux-là ». Les preuves interdisent la version naïve : 97 % des fonds actions
actifs en Europe font moins bien que leur indice sur dix ans (SPIVA 2025) ;
2,4 % des sociétés font toute la création de richesse boursière (Bessembinder) ;
une recette publiée perd 58 % de son rendement après publication (McLean &
Pontiff). Afficher des convictions serait mentir.

Une seule forme de sélection produit vraiment une liste avec un siècle de
preuves : le **momentum** — acheter ce qui a le plus monté sur douze mois en
ignorant le dernier (Jegadeesh & Titman 1993), plus fort encore en Europe
(Rouwenhorst 1998), toujours vivant trente ans après publication (AQR). Son
prix : −45 % en deux mois au rebond de 2009 (Daniel & Moskowitz 2016).

## Décision

Une règle mécanique, lisible dans `config/momentum.yaml`, sur un univers lu en
direct :

1. **Univers** : les constituants actuels du Stoxx Europe 600 cotés en euros,
   lus dans le fichier de positions quotidien de l'ETF Xtrackers qui le
   réplique (un fonds indiciel détient l'indice : ses positions sont les
   constituants du jour), chaque ISIN résolu en cotation par OpenFIGI — places
   de l'UE, pour l'essentiel éligibles au PEA. Rien n'est recopié dans le dépôt. Les pages
   Wikipédia, première source retenue, répondaient 403 ou 429 à un script et
   demandaient de lire un tableau HTML ; les exports des bourses sont chiffrés
   (Euronext) ou vides (Deutsche Börse).
2. **Score** : rendement des douze derniers mois hors le dernier, divisé par
   la volatilité (Barroso & Santa-Clara 2015). Trente titres, à poids égal.
3. **Revue** trimestrielle : la liste dit ce qui entre et ce qui sort. Chaque
   aller-retour paie un coût dans le backtest.
4. **Frein** : quand l'univers à poids égal a perdu sur douze mois, la liste
   est vide et la poche reste en cash jusqu'à la revue suivante — la
   configuration de krach identifiée par Daniel & Moskowitz.
5. **Poche plafonnée** : l'écran présente la liste comme un satellite de 10 à
   20 % des actions, jamais comme le cœur. Le cœur reste l'ETF monde.
6. **Track record visible** : le backtest sur nos propres séries, 2009 inclus,
   et le rendement de chaque liste passée en face de l'univers.

## Conséquences

Ce qu'on peut promettre : une liste reproductible, une espérance de prime
documentée, et un frein contre le pire cas connu. Ce qu'on ne promet pas : un
gain. Le texte de l'écran le dit.

Le backtest est **flatté par le biais du survivant** : l'univers est celui
d'aujourd'hui, les sortants d'hier manquent. Aucune source gratuite ne donne
les constituants historiques. La commande le rappelle en tête de rapport.

## Ce qu'on a refusé

**Des convictions.** Un titre choisi parce qu'il « a l'air bien » — l'app
n'aurait rien à opposer au premier qui plonge.

**Les recettes qualité / valeur** (Piotroski, Magic Formula). Elles demandent
des bilans d'entreprise ; on n'a aucune source gratuite et fiable pour ça. Le
momentum n'a besoin que des cours.

**Rééquilibrer chaque mois.** Entre deux revues, les poids dérivent avec les
cours : à poids égal, un rééquilibrage mensuel coûte plus qu'il ne rapporte.
