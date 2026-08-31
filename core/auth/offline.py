from __future__ import annotations

import re
import uuid

from .models import Account, AccountType


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,16}$")
OFFLINE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class InvalidUsernameError(ValueError):
    pass


def validate_username(username: str) -> tuple[bool, str]:
    if not isinstance(username, str):
        return False, "El nombre de usuario debe ser texto."
    if not username:
        return False, "El nombre de usuario no puede estar vacío."
    if not 3 <= len(username) <= 16:
        return False, "El nombre de usuario debe tener entre 3 y 16 caracteres."
    if not USERNAME_REGEX.fullmatch(username):
        return False, "El nombre de usuario solo admite letras, números y guiones bajos."
    return True, ""


def generate_offline_uuid(username: str) -> str:
    return str(uuid.uuid3(OFFLINE_NAMESPACE, f"OfflinePlayer:{username}"))


def create_offline_account(username: str) -> Account:
    if not isinstance(username, str):
        raise InvalidUsernameError("El nombre de usuario debe ser texto.")
    username_stripped = username.strip()
    valid, reason = validate_username(username_stripped)
    if not valid:
        raise InvalidUsernameError(reason)
    return Account(
        uuid=generate_offline_uuid(username_stripped),
        name=username_stripped,
        type=AccountType.OFFLINE,
    )


def format_uuid_no_dashes(uuid_str: str) -> str:
    try:
        return uuid.UUID(uuid_str).hex
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("UUID inválido.") from error


def format_uuid_with_dashes(uuid_str: str) -> str:
    try:
        return str(uuid.UUID(uuid_str))
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("UUID inválido.") from error
