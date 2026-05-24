"""Rate limiting helper — pour Phase future si on a besoin de logiques plus complexes.

Pour l'instant, la rate-limit auth est gérée directement dans main.py via un middleware
maison (tracking in-memory, sliding window). Voir _AUTH_RATE_LIMITS dans main.py.

Si on scale horizontalement (plusieurs instances backend) il faudra :
- Soit passer le tracking en Redis (lib slowapi avec Redis storage)
- Soit utiliser un reverse proxy avec rate limit (nginx, Caddy, Cloudflare)
"""
