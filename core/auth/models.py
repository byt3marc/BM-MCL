from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict, TypeGuard, cast


class AccountType(StrEnum):
    OFFLINE = "offline"
    MICROSOFT = "microsoft"


class AccountData(TypedDict):
    uuid: str
    name: str
    type: str
    access_token: str | None
    refresh_token: str | None
    expires_at: str | None
    skin_variant: str


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
        expires_at = (
            self.expires_at
            if self.expires_at.tzinfo
            else self.expires_at.replace(tzinfo=UTC)
        )
        return expires_at <= datetime.now(UTC)

    def to_dict(self) -> AccountData:
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
    def from_dict(data: object) -> Account:
        if not _is_string_keyed_dict(data):
            raise TypeError("Los datos de la cuenta deben ser un objeto válido.")
        account_uuid = data.get("uuid")
        name = data.get("name")
        raw_account_type = data.get("type")
        if (
            not isinstance(account_uuid, str)
            or not isinstance(name, str)
            or not isinstance(raw_account_type, str)
        ):
            raise TypeError("Los datos de la cuenta son inválidos.")
        if not account_uuid or not name:
            raise ValueError("La cuenta requiere UUID y nombre.")
        try:
            account_type = AccountType(raw_account_type)
        except ValueError as error:
            raise ValueError("Los datos de la cuenta son inválidos.") from error

        raw_expires_at = data.get("expires_at")
        expires_at: datetime | None = None
        if raw_expires_at is not None:
            if not isinstance(raw_expires_at, str):
                raise ValueError("expires_at debe ser una fecha ISO 8601.")
            try:
                expires_at = datetime.fromisoformat(raw_expires_at)
            except ValueError as error:
                raise ValueError("expires_at no es una fecha ISO 8601 válida.") from error

        skin_variant = data.get("skin_variant", "classic")
        if not isinstance(skin_variant, str) or skin_variant not in {"classic", "slim"}:
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


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} debe ser texto o nulo.")
    return value


def _is_string_keyed_dict(value: object) -> TypeGuard[dict[str, object]]:
    if not isinstance(value, dict):
        return False
    dictionary = cast(dict[object, object], value)
    return all(isinstance(key, str) for key in dictionary)
