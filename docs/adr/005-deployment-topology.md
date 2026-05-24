# ADR-005: Topologie de déploiement

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Tangent doit être accessible publiquement via HTTPS pour permettre l'OAuth Powens (redirect URL exposée) et l'usage mobile. Mais le projet est personnel, le budget est minimal (~10€/an cible), et la latence depuis la France doit être basse.

Contraintes :
- HTTPS obligatoire (DSP2 = données bancaires)
- Domaine custom requis (Powens whitelist par domaine)
- Pas d'IP publique à exposer (NAT chez l'opérateur)
- Tolérance à quelques minutes de downtime mensuel acceptable

## Décision

**Topologie self-host MacBook Air M2 + Cloudflare Tunnel** :

```
Internet
   ↓ HTTPS
[Cloudflare Edge — TLS termination]
   ↓ tunnel (HTTP/2 outbound from Mac, no inbound port)
[cloudflared agent on MacBook]
   ↓ http://localhost:80
[Caddy reverse proxy (Docker)]
   ↓ http://backend:8000 / http://frontend:5173
[FastAPI backend] [Vite frontend] [Postgres]
   (all in same docker-compose stack)
```

**Composants** :

| Composant | Rôle |
|-----------|------|
| Cloudflare Registrar | Achat du domaine `riskybusinesses.uk` (~5€/an) |
| Cloudflare DNS | Routing DNS (CNAME flattening sur apex) |
| Cloudflare Tunnel | Exposition HTTPS sans port forwarding, DDoS protection gratis |
| `cloudflared` (launchd) | Daemon sur Mac, connexion sortante vers Cloudflare edge |
| Caddy 2 (Docker) | Reverse proxy, route `/auth/*` etc. vers backend, le reste vers frontend |
| Docker Compose | Orchestration des services (backend, frontend, postgres, caddy) |
| Docker Desktop (auto-start) | Démarre au login Mac |
| launchd plist | Auto-start de `cloudflared` au boot |
| pmset | Empêche la veille du Mac (sleep 0, displaysleep 10) |

## Conséquences

### Positives

- **Coût** : ~5€/an domaine + ~3€/an électricité = ~8€/an
- **Sécurité** : aucun port ouvert sur la box, Cloudflare DDoS protection, HTTPS auto
- **Latence** : edge Cloudflare CDG (Paris) = < 10ms aller-retour pour les users FR
- **Maintenance** : faible, restart automatique de tous les composants
- **Performance** : Mac M2 = surdimensionné pour les besoins actuels

### Négatives

- **Single point of failure** : si le Mac tombe en panne, downtime jusqu'à réparation
- **Dépendance Cloudflare** : si Cloudflare tombe (rare mais possible), downtime
- **Pas de scalabilité horizontale** : 1 instance unique
- **Bande passante** : limitée par la connexion internet domicile (mais largement OK pour usage perso)

## Alternatives considérées

### Option A — Oracle Cloud ARM Always Free

VPS gratuit 4 cores 24GB RAM. Écartée car "Out of capacity" en EU-Paris-1, attente de 24-48h après demande de service limit increase, complexité de setup.

### Option B — VPS payant (Hetzner CX22, RackNerd 1GB)

Vraie prod sans tuning. Coût 9-50€/an. Écartée pour cette première phase car le Mac est inutilisé H24 et la solution self-host suffit. À considérer si > 10 users actifs ou si downtime du Mac devient un problème.

### Option C — Fly.io / Railway / Render

PaaS managé. Écartée car coût > 10€/mois et lock-in.

### Option D — Tailscale Funnel

Alternative à Cloudflare Tunnel. Écartée car limites de bande passante plus strictes (1Mbps) et moins de fonctionnalités CDN.

## Notes

- **Procédure de redémarrage** : `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`, `launchctl load ~/Library/LaunchAgents/com.tangent.cloudflared.plist`
- **Procédure de monitoring** : checks Cloudflare dashboard (Tunnel status), `curl https://riskybusinesses.uk/health`
- **Plan B** : si le Mac casse, déploiement sur RackNerd 9€/an déjà cartographié — restore DB depuis backup B2 + déployer via docker-compose
- **Tests de reboot** : à exécuter trimestriellement pour valider que tout repart bien
- **Power settings actuels** (validés 2026-05-23) : `sleep 0`, `disksleep 0`, `displaysleep 10`, `hibernatemode 0`, `womp 1`
