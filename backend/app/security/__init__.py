"""Couche sécurité (spec §8) — issue #5.

Modules :

- ``passwords`` : hachage Argon2id + politique mot de passe figée (DESIGN P1) ;
- ``sessions`` : sessions opaques 256 bits, stockées hachées (SHA-256) ;
- ``csrf`` : jeton CSRF par session (haché) + middleware ASGI global ;
- ``rate_limit`` : limiteur fenêtre glissante en mémoire (D-07) ;
- ``email`` : transport SMTP (Mailpit) ou log ``DEV-EMAIL`` (D-12).

Aucun secret n'est loggé hors du transport de dev documenté par D-12 ;
les tokens ne circulent qu'en clair dans leur canal dédié (cookie,
e-mail, header ``X-CSRF-Token``).
"""
