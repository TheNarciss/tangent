"""Auth backend : transport (cookie) + strategy (JWT).

Combinaison choisie :
- Cookie HTTP-only (immune au XSS) + Secure (HTTPS only en prod) + SameSite=lax (anti-CSRF)
- JWT (stateless, pas de table sessions à maintenir, simple à scale)
- Lifetime 7 jours (suffisant pour usage perso, à raccourcir en prod)
"""

import os

from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

# ── Cookie config ─────────────────────────────────────────────────────

COOKIE_NAME = os.getenv("COOKIE_NAME", "tangent_auth")
COOKIE_LIFETIME = int(os.getenv("COOKIE_LIFETIME_SECONDS", 7 * 24 * 3600))  # 7 jours par défaut
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # false en dev local (HTTP)

cookie_transport = CookieTransport(
    cookie_name=COOKIE_NAME,
    cookie_max_age=None,  # session cookie: cleared when browser closes (JWT lifetime is the hard ceiling)
    cookie_secure=COOKIE_SECURE,  # HTTPS only quand true
    cookie_httponly=True,  # PAS accessible via JS → XSS-proof
    cookie_samesite="lax",  # CSRF protection (lax permet les liens cross-site simples, suffisant)
)

# ── JWT strategy ──────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET or JWT_SECRET == "GENERATE_ME_WITH_SECRETS_TOKEN_URLSAFE":
    raise RuntimeError(
        "JWT_SECRET manquant ou laissé au placeholder. "
        'Génère-en un fort : python -c "import secrets; print(secrets.token_urlsafe(32))" '
        "puis mets-le dans backend/.env"
    )


def get_jwt_strategy() -> JWTStrategy:
    """JWT strategy — appelée à chaque request pour valider/créer le token."""
    return JWTStrategy(
        secret=JWT_SECRET,
        lifetime_seconds=COOKIE_LIFETIME,
        algorithm="HS256",
    )


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
