"""Repositories : couche d'accès DB par entité.

Pattern :
- Toutes les fonctions prennent (session, user_id) en paramètres
- Toutes les queries filtrent par user_id → multi-tenant safe by design
- Retournent des objets SQLAlchemy ORM ou des dataclasses simples

Avantage : si t'oublies de passer user_id, la fonction ne compile pas. Pas
d'oubli silencieux possible.
"""