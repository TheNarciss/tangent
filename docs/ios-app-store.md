# L'app iPhone sur l'App Store : ce qu'il reste à faire à la main

Le code est dans le dépôt (ADR-035). Ce qui suit se fait dans le compte Apple Developer, dans App Store Connect et sur la VM, une fois. Aucune de ces valeurs ne passe par un chat.

## 1. Apple Developer (developer.apple.com → Certificates, Identifiers & Profiles)

| Quoi | Valeur | Où ça sert |
|---|---|---|
| Team ID | 10 caractères, page Membership | `APPLE_TEAM_ID` (VM et secret GitHub) |
| App ID | `uk.riskybusinesses.tangent`, capacité **Sign in with Apple** cochée | l'app ; `APPLE_BUNDLE_ID` |
| Services ID | `uk.riskybusinesses.tangent.web`, Sign in with Apple configuré : domaine `riskybusinesses.uk`, Return URL `https://riskybusinesses.uk/api/auth/apple/callback`, groupé sous l'App ID | le site ; `APPLE_CLIENT_ID` |
| Clé « Sign in with Apple » | un fichier `.p8` téléchargeable une seule fois, et son Key ID | `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_B64` (`base64 -w0 AuthKey_XXXX.p8`) |
| Certificat Apple Distribution | exporté en `.p12` avec mot de passe | secrets `IOS_CERTIFICATE_P12_B64`, `IOS_CERTIFICATE_PASSWORD` |
| Profil de provisionnement App Store | pour l'App ID ci-dessus | secret `IOS_PROVISIONING_PROFILE_B64` |

Sur la VM, dans `backend/.env` : `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_B64`, `APPLE_CLIENT_ID`, `APPLE_BUNDLE_ID`, puis redémarrer le backend. Le bouton « Continuer avec Apple » apparaît sur le site dès que c'est en place.

## 2. App Store Connect (appstoreconnect.apple.com)

- **Nouvelle app** : nom Tangent, langue principale français, bundle `uk.riskybusinesses.tangent`, SKU libre. Ajouter l'anglais (Royaume-Uni) comme localisation de la fiche : l'app suit la langue du téléphone (ADR-036), la fiche doit exister dans les deux langues.
- **Clé API** (Users and Access → Integrations → App Store Connect API) : rôle App Manager ; Key ID, Issuer ID, fichier `.p8` → secrets `APPSTORE_API_KEY_ID`, `APPSTORE_API_ISSUER_ID`, `APPSTORE_API_KEY_P8_B64`.
- **Confidentialité de l'app** (App Privacy) : données collectées, liées à l'identité, sans suivi :
  adresse e-mail, informations financières (autres), identifiant utilisateur. Politique : `https://riskybusinesses.uk/legal/privacy.html`.
- **Informations** : catégorie Finance, classification 4+, URL d'assistance `https://riskybusinesses.uk/legal/about.html`, contrat de licence standard.
- **Conformité à l'export** : l'app n'utilise que HTTPS ; `ITSAppUsesNonExemptEncryption` est déjà à `NO` dans `Info.plist`.
- **Captures d'écran** : iPhone 6,7" (1290 × 2796) obligatoires ; 6,1" recommandées. Aperçu, Comptes, Placements, Dépenses, l'écran de connexion.
- **Notes pour la revue** : le compte de démonstration (voir 3) avec son mot de passe, et une phrase : « Tangent agrège des comptes bancaires via des prestataires agréés DSP2 (Powens, Enable Banking). Le relecteur ne pourra pas connecter une banque ; le compte fourni contient des données de démonstration. Le briefing du matin est informatif et ne constitue pas un conseil en investissement. »

## 3. Le compte de démonstration

Sur la VM, une fois le backend à jour :

```bash
cd /home/ubuntu/projet_finance
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec \
  -e DEMO_EMAIL=demo@riskybusinesses.uk -e DEMO_PASSWORD='un mot de passe long' \
  backend python -m app.demo
```

Trois comptes (courant, Livret A, PEA avec deux fonds indiciels), trois mois de dépenses catégorisées, soixante jours de relevés. Relancer la commande rafraîchit le compte. Ce compte n'est pas administrateur : il ne voit aucun bouton qui appelle l'IA.

## 4. Construire et envoyer

- **Vérifier que ça compile** : le workflow *iOS → Build for the simulator* tourne sur chaque PR qui touche `frontend/ios` ou `frontend/src/native`, sans signature.
- **Envoyer sur TestFlight** : Actions → iOS → Run workflow, cocher *testflight*. Le numéro de build est le numéro d'exécution du workflow. Puis dans App Store Connect → TestFlight, ajouter un testeur interne (toi) et installer l'app par l'application TestFlight.
- **Soumettre** : quand un build TestFlight tient la route, App Store Connect → la version → choisir ce build → *Ajouter pour révision*. Compter un à trois allers-retours avec la revue Apple.

## 5. Ce qui déclenche un refus, et ce qui est déjà fait

| Règle Apple | État |
|---|---|
| 4.2 Minimum functionality (pas un site dans une fenêtre) | Face ID, flou en arrière-plan, navigateur système, Sign in with Apple natif, liens `tangent://` |
| 4.8 Sign in with Apple si Google est proposé | fait, site et app |
| 5.1.1 Suppression du compte dans l'app | fait (Mon compte → Zone dangereuse) |
| 5.1.1 Politique de confidentialité, manifeste `PrivacyInfo.xcprivacy` | fait |
| 2.1 L'app doit être testable : compte de démo dans les notes | section 3 |
| 3.1.5 / 5.1 Finance : prestataires agréés, pas de conseil | notes de revue, avertissement dans chaque briefing |
