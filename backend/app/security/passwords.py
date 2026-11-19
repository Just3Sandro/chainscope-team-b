"""Mots de passe : hachage Argon2id + politique figée (DESIGN.md P1, spec §8).

Paramètres Argon2id : les **défauts de la bibliothèque argon2-cffi** sont
utilisés explicitement — ``time_cost=3``, ``memory_cost=65536`` Ko (64 Mio),
``parallelism=4``, ``salt_len=16``, ``hash_len=32`` (spec §8 : Argon2id ;
le coût du hachage est le frein offline documenté au threat model T-24).

Anti-oracle : une politique violée renvoie **toujours le même message**
(``PASSWORD_POLICY_MESSAGE``), quel que soit le critère en défaut
(longueur, minuscule, majuscule, chiffre) — jamais de détail par règle
(D-19, issue #5 ; T-21 : aucune information exploitable à l'attaquant).

Anti-enumeration (T-21, D-07) : ``dummy_password_hash()`` fournit un
hachage Argon2id « canard » ; le service de login effectue un
« verify fantôme » contre ce hash quand l'e-mail est inconnu, de sorte
que le délai de calcul est **identique** que le compte existe ou non.
"""
from __future__ import annotations

import re
from typing import Final

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError

# Défauts documentés de argon2-cffi (cf. docstring de module).
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    salt_len=16,
    hash_len=32,
    type=Type.ID,
)

# --- Politique figée (DESIGN.md P1, contrat « DESIGN P1 ») ------------------
PASSWORD_MIN_LENGTH: Final[int] = 10
PASSWORD_MAX_LENGTH: Final[int] = 72
# Message UNIQUE de rejet : ne précise jamais quelle règle échoue (anti-oracle).
PASSWORD_POLICY_MESSAGE: Final[str] = (
    "Mot de passe non conforme à la politique : 10 à 72 caractères, "
    "avec au moins une minuscule, une majuscule et un chiffre."
)

_HAS_LOWERCASE: Final[re.Pattern[str]] = re.compile(r"[a-z]")
_HAS_UPPERCASE: Final[re.Pattern[str]] = re.compile(r"[A-Z]")
_HAS_DIGIT: Final[re.Pattern[str]] = re.compile(r"\d")


def hash_password(password: str) -> str:
    """Hache un mot de passe en clair (Argon2id) — stocker le résultat seul."""
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre un hash ; ``False`` si inconnu,
    invalide ou non conforme (jamais d'exception vers l'appelant)."""
    try:
        return _HASHER.verify(password_hash, password)
    except VerificationError:
        return False


def validate_password_policy(password: str) -> str | None:
    """Valide la politique de mot de passe (DESIGN P1).

    Renvoie ``None`` si conforme, sinon le message de rejet **unique et
    stable** (``PASSWORD_POLICY_MESSAGE``) — même message pour toute règle
    en défaut, sans indication de laquelle (anti-oracle, D-19).
    """
    if not isinstance(password, str):
        return PASSWORD_POLICY_MESSAGE
    if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
        return PASSWORD_POLICY_MESSAGE
    if not _HAS_LOWERCASE.search(password):
        return PASSWORD_POLICY_MESSAGE
    if not _HAS_UPPERCASE.search(password):
        return PASSWORD_POLICY_MESSAGE
    if not _HAS_DIGIT.search(password):
        return PASSWORD_POLICY_MESSAGE
    return None


# --- Hash « canard » pour le verify fantôme (T-21, D-07) --------------------
# Chaîne fictive interne (pas un secret : le hash est publique par nature
# tant que le mot de passe canard est lui-même générique et sans valeur).
_DUMMY_PASSWORD: Final[str] = "chainscope-canary-verify-2026"
_dummy_hash: str | None = None


def dummy_password_hash() -> str:
    """Hash Argon2id du mot de passe canard, calculé une fois (mis en cache).

    Sert au « verify fantôme » du service de login : même coût de calcul
    qu'un vrai ``verify`` (même ``_HASHER``), donc délai de réponse stable
    quel que soit l'existence du compte (T-21).
    """
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _HASHER.hash(_DUMMY_PASSWORD)
    return _dummy_hash


__all__ = [
    "PASSWORD_MAX_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_POLICY_MESSAGE",
    "dummy_password_hash",
    "hash_password",
    "validate_password_policy",
    "verify_password",
]
