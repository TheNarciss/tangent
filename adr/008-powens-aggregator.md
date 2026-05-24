# ADR-008: Powens comme aggregateur bancaire

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Pour devenir un vrai outil de gestion patrimoniale, Tangent doit accéder aux données bancaires de l'utilisateur. Le faire soi-même via scraping ou intégration directe DSP2 par banque = mois de travail par banque, fragile, et illégal sans agrément.

Solution : passer par un aggregateur DSP2 agréé qui fournit une API unifiée.

Options principales sur le marché EU : Powens (ex-Budgea/Linxo), Bridge, Tink, Plaid, Yapily.

## Décision

**Powens** comme aggregateur bancaire unique.

Justifications :
- **Sandbox gratuite** sans engagement
- **96.5% de taux de refresh quotidien** annoncé
- **Couverture France excellente** (BNP, Banque Populaire, etc.)
- **API REST documentée et stable**
- **Support de tous les types de comptes** : checking, savings, pea, cto, lifeinsurance, loan, crypto
- **Webhooks granulaires** : `ACCOUNT_FOUND`, `ACCOUNT_CATEGORIZED`, `CONNECTION_SYNCED`, etc.
- **Webview hosted** pour l'OAuth (pas à gérer le UX bancaire)
- **Catégorisation auto** des transactions inclus

**Architecture d'intégration** :
- Module dédié `app/powens/` qui isole tout ce qui est Powens-specific
- Couche d'abstraction `aggregator/interface.py` (à introduire en Phase A) qui permet de switcher d'aggregator sans refacto profonde
- Tokens user chiffrés en DB via Fernet (cf ADR-012)
- Webhooks sécurisés via HMAC (header `X-Powens-Signature`)
- Domain sandbox : `riskybusiness-sandbox.biapi.pro`

## Conséquences

### Positives

- Time-to-market massivement réduit (jours vs mois)
- Agrément DSP2 délégué à Powens (légal et conforme)
- Couverture multi-banques gratuite
- Catégorisation initiale auto fournie
- Webhooks = sync incrémental possible

### Négatives

- **Vendor lock-in** : si Powens change ses prix ou ferme la sandbox, migration douloureuse → mitigation : couche d'abstraction
- **Dépendance externe** : si Powens tombe, l'app perd la sync mais reste utilisable en lecture sur les données déjà sync
- **Coûts à terme inconnus** : la sandbox est gratuite, production peut être payante au-delà d'un certain volume → à monitorer

## Alternatives considérées

### Option A — Bridge (ex-Bankin' for Business)

Aggregateur français mature. Écarté car onboarding entreprise plus lourd, moins de transparence sur la sandbox gratuite.

### Option B — Tink (acquis par Visa)

Couverture EU excellente. Écarté car pricing opaque et orientation B2B grand compte.

### Option C — Plaid

Leader US, présence EU. Écarté car couverture France moins forte que Powens et historique de procès aux US.

### Option D — Yapily

API-only, sans webview. Écarté car force à recoder l'UX OAuth = travail énorme par banque.

### Option E — Pas d'aggregator (import CSV manuel)

Liberté totale, zéro vendor lock-in. Écarté car friction utilisateur insupportable (export CSV manuel chaque mois) → conflit avec le principe "simplicité d'usage".

## Notes

- **À surveiller** : pricing Powens en cas de passage en production avec >100 connexions
- **Couche d'abstraction à introduire en Phase A** : interface `IBankAggregator` avec méthodes `list_accounts`, `list_transactions`, `webhook_handler` → implémentations `PowensAggregator`, à terme `BridgeAggregator` si besoin
- **Webhook secret** : à configurer dès la mise en prod (actuellement vide dans `.env`)
- **Powens client_id actuel** : `20079335` (sandbox)
- **Mapping types Powens → Tangent** : déjà défini dans `config/powens.yaml`
- **GDPR** : l'endpoint Powens `DELETE /users/{id}/connections/{conn_id}` doit être appelé lors du désengagement d'un user (hard delete chez Powens)
