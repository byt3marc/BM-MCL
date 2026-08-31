from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Account


ACCOUNTS_FILE = "accounts.json"


class AuthStoreError(Exception):
    pass


class AuthStore:
    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.accounts_file = self.data_dir / ACCOUNTS_FILE

    def load_accounts(self) -> list[Account]:
        raw = self._load_raw()
        accounts_data = raw.get("accounts", [])
        if not isinstance(accounts_data, list):
            raise AuthStoreError("El archivo de cuentas tiene un formato inválido.")
        try:
            return [Account.from_dict(account) for account in accounts_data]
        except ValueError as error:
            raise AuthStoreError("El archivo contiene una cuenta inválida.") from error

    def save_accounts(self, accounts: list[Account]) -> None:
        if not all(isinstance(account, Account) for account in accounts):
            raise TypeError("accounts debe contener únicamente Account.")
        raw = self._load_raw()
        selected_uuid = raw.get("selected_uuid")
        account_uuids = {account.uuid for account in accounts}
        if selected_uuid not in account_uuids:
            selected_uuid = None
        self._save_raw(
            {
                "accounts": [account.to_dict() for account in accounts],
                "selected_uuid": selected_uuid,
            }
        )

    def get_selected_uuid(self) -> str | None:
        selected_uuid = self._load_raw().get("selected_uuid")
        if selected_uuid is None:
            return None
        if not isinstance(selected_uuid, str):
            raise AuthStoreError("selected_uuid debe ser texto o nulo.")
        return selected_uuid

    def set_selected_uuid(self, account_uuid: str | None) -> None:
        if account_uuid is not None and not isinstance(account_uuid, str):
            raise TypeError("uuid debe ser texto o nulo.")
        raw = self._load_raw()
        accounts = self.load_accounts()
        if account_uuid is not None and account_uuid not in {account.uuid for account in accounts}:
            raise AuthStoreError("La cuenta seleccionada no existe.")
        raw["selected_uuid"] = account_uuid
        self._save_raw(raw)

    def add_or_update(self, account: Account) -> None:
        if not isinstance(account, Account):
            raise TypeError("account debe ser una instancia de Account.")
        accounts = self.load_accounts()
        updated_accounts = [stored for stored in accounts if stored.uuid != account.uuid]
        updated_accounts.append(account)
        self.save_accounts(updated_accounts)

    def remove(self, account_uuid: str) -> None:
        if not isinstance(account_uuid, str):
            raise TypeError("uuid debe ser texto.")
        accounts = self.load_accounts()
        remaining_accounts = [account for account in accounts if account.uuid != account_uuid]
        raw = self._load_raw()
        selected_uuid = None if raw.get("selected_uuid") == account_uuid else raw.get("selected_uuid")
        self._save_raw(
            {
                "accounts": [account.to_dict() for account in remaining_accounts],
                "selected_uuid": selected_uuid,
            }
        )

    def _load_raw(self) -> dict[str, Any]:
        if not self.accounts_file.exists():
            return {"accounts": [], "selected_uuid": None}
        try:
            raw = json.loads(self.accounts_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AuthStoreError("No se pudo leer el archivo de cuentas.") from error
        if not isinstance(raw, dict):
            raise AuthStoreError("El archivo de cuentas debe contener un objeto JSON.")
        return raw

    def _save_raw(self, raw: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary_file = self.accounts_file.with_suffix(".tmp")
        try:
            temporary_file.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_file.replace(self.accounts_file)
        except OSError as error:
            raise AuthStoreError("No se pudo guardar el archivo de cuentas.") from error
