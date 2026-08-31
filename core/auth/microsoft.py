from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from minecraft_launcher_lib import microsoft_account as msa
except ImportError:
    msa = None

from .models import Account, AccountType
from .offline import format_uuid_with_dashes


MICROSOFT_CLIENT_ID = "00000000402b5328"
MICROSOFT_REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"
TOKEN_REFRESH_MARGIN_SEC = 60


class AuthError(Exception):
    pass


class TokenRefreshError(AuthError):
    pass


class MicrosoftAuthService:
    def __init__(self, client_id: str = MICROSOFT_CLIENT_ID) -> None:
        if not client_id:
            raise ValueError("client_id no puede estar vacío.")
        self.client_id = client_id
        self._auth_state: dict[str, str] | None = None

    def get_login_url(self) -> str:
        service = self._require_service()
        try:
            login_url, state, code_verifier = service.get_secure_login_data(
                self.client_id,
                MICROSOFT_REDIRECT_URI,
            )
        except Exception as error:
            raise AuthError("No se pudo iniciar el inicio de sesión de Microsoft.") from error
        self._auth_state = {"state": state, "code_verifier": code_verifier}
        return login_url

    def complete_login(self, auth_code_or_url: str) -> Account:
        if self._auth_state is None:
            raise AuthError("Primero debe solicitarse la URL de inicio de sesión.")
        service = self._require_service()
        auth_code = self._parse_auth_code_from_url(auth_code_or_url)
        self._validate_state(auth_code_or_url)
        try:
            response = service.complete_login(
                self.client_id,
                None,
                MICROSOFT_REDIRECT_URI,
                auth_code,
                self._auth_state["code_verifier"],
            )
        except Exception as error:
            raise AuthError("No se pudo completar el inicio de sesión de Microsoft.") from error
        self._auth_state = None
        return self._build_account_from_msa_response(response)

    def refresh_account(self, account: Account) -> Account:
        if account.type is not AccountType.MICROSOFT or not account.refresh_token:
            raise TokenRefreshError("La cuenta no dispone de un token de actualización.")
        if not account.is_expired():
            return account
        service = self._require_service()
        try:
            response = service.complete_refresh(
                self.client_id,
                None,
                MICROSOFT_REDIRECT_URI,
                account.refresh_token,
            )
        except Exception as error:
            raise TokenRefreshError("No se pudo actualizar el token de Microsoft.") from error
        try:
            return self._build_account_from_msa_response(response, account)
        except AuthError as error:
            raise TokenRefreshError("La respuesta de actualización de token es inválida.") from error

    def is_token_valid(self, account: Account) -> bool:
        return (
            account.type is AccountType.MICROSOFT
            and bool(account.access_token)
            and bool(account.refresh_token)
            and not account.is_expired()
        )

    def _parse_auth_code_from_url(self, auth_code_or_url: str) -> str:
        if not isinstance(auth_code_or_url, str) or not auth_code_or_url.strip():
            raise AuthError("El código de autorización es obligatorio.")
        parsed = urlparse(auth_code_or_url)
        if not parsed.scheme:
            return auth_code_or_url.strip()
        code = parse_qs(parsed.query).get("code", [""])[0]
        if not code:
            raise AuthError("La URL de redirección no contiene un código de autorización.")
        return code

    def _validate_state(self, auth_code_or_url: str) -> None:
        if self._auth_state is None:
            return
        parsed = urlparse(auth_code_or_url)
        if not parsed.scheme:
            return
        received_state = parse_qs(parsed.query).get("state", [None])[0]
        if received_state is not None and received_state != self._auth_state["state"]:
            raise AuthError("El estado de autorización de Microsoft no coincide.")

    def _build_account_from_msa_response(
        self,
        msa_data: dict[str, Any],
        previous_account: Account | None = None,
    ) -> Account:
        if not isinstance(msa_data, dict):
            raise AuthError("Microsoft devolvió una respuesta inválida.")
        profile = msa_data.get("minecraft_profile")
        if not isinstance(profile, dict):
            profile = msa_data
        raw_uuid = profile.get("id_formatted") or profile.get("id") or (
            previous_account.uuid if previous_account else None
        )
        name = profile.get("name") or (previous_account.name if previous_account else None)
        access_token = msa_data.get("access_token")
        refresh_token = msa_data.get("refresh_token") or (
            previous_account.refresh_token if previous_account else None
        )
        if not isinstance(raw_uuid, str) or not isinstance(name, str) or not isinstance(access_token, str):
            raise AuthError("Microsoft no devolvió un perfil de Minecraft válido.")
        expires_at = self._get_expiration(msa_data)
        if expires_at is None and previous_account is not None:
            expires_at = previous_account.expires_at
        return Account(
            uuid=format_uuid_with_dashes(raw_uuid),
            name=name,
            type=AccountType.MICROSOFT,
            access_token=access_token,
            refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            expires_at=expires_at,
            skin_variant=previous_account.skin_variant if previous_account else "classic",
        )

    def _get_expiration(self, msa_data: dict[str, Any]) -> datetime | None:
        expires_in = msa_data.get("expires_in")
        if expires_in is None:
            return None
        try:
            return datetime.now(timezone.utc) + timedelta(seconds=max(0, int(expires_in)))
        except (TypeError, ValueError) as error:
            raise AuthError("El tiempo de expiración de Microsoft es inválido.") from error

    @staticmethod
    def _require_service() -> Any:
        if msa is None:
            raise AuthError("minecraft_launcher_lib no está instalado.")
        return msa
