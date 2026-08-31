from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class AccountType(StrEnum):
    OFFLINE = "offline"
    MICROSOFT = "microsoft"


@dataclass(frozen=True, slots=True)
class Account:
    uuid: str
    name: str
    type: AccountType
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    skin_variant: str = "classic"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc) if self.expires_at.tzinfo else datetime.now()
        return self.expires_at <= now

    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "type": self.type.value,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "skin_variant": self.skin_variant,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Account":
        if not isinstance(data, dict):
            raise ValueError("Los datos de la cuenta deben ser un objeto.")
        try:
            account_uuid = str(data["uuid"])
            name = str(data["name"])
            account_type = AccountType(data["type"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Los datos de la cuenta son inválidos.") from error
        if not account_uuid or not name:
            raise ValueError("La cuenta requiere UUID y nombre.")
        raw_expires_at = data.get("expires_at")
        expires_at: datetime | None = None
        if raw_expires_at is not None:
            if not isinstance(raw_expires_at, str):
                raise ValueError("expires_at debe ser una fecha ISO 8601.")
            try:
                expires_at = datetime.fromisoformat(raw_expires_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("expires_at no es una fecha ISO 8601 válida.") from error
        skin_variant = data.get("skin_variant", "classic")
        if skin_variant not in {"classic", "slim"}:
            raise ValueError("skin_variant debe ser 'classic' o 'slim'.")
        return Account(
            uuid=account_uuid,
            name=name,
            type=account_type,
            access_token=_optional_string(data.get("access_token"), "access_token"),
            refresh_token=_optional_string(data.get("refresh_token"), "refresh_token"),
            expires_at=expires_at,
            skin_variant=skin_variant,
        )


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} debe ser texto o nulo.")
    return value
