# auth — Diseño del módulo

> **Objetivo:** Gestionar cuentas `offline` (no premium) y `microsoft` (premium). Es el único lugar que genera UUIDs offline y que habla con `minecraft_launcher_lib.microsoft_account`. Sin Qt, 100% testeable.

---

## 1. Archivos y responsabilildad

| Archivo | Rol |
|---|---|
| `core/auth/models.py` | Dataclasses puras, sin lógica. Desacopladas de la lib. |
| `core/auth/offline.py` | Lógica offline: validación + generación UUID v3 determinística. |
| `core/auth/microsoft.py` | Wrapper sobre `minecraft_launcher_lib.microsoft_account`. Maneja OAuth, refresh y fallback offline. |
| `core/auth/store.py` *(a crear si hace falta)* | Persistencia de `List[Account]` + `selected_uuid` en `data/accounts.json` |

**Regla de oro:** `core/auth` NUNCA importa `PySide6`. Solo `uuid`, `re`, `datetime`, y `minecraft_launcher_lib`.

---

## 2. Modelos — `models.py`

```python
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional
from datetime import datetime

class AccountType(StrEnum):
    OFFLINE = "offline"
    MICROSOFT = "microsoft"

@dataclass(frozen=True, slots=True)
class Account:
    uuid: str              # con guiones: 8-4-4-4-12
    name: str              # username / gamertag
    type: AccountType
    access_token: Optional[str] = None   # solo microsoft
    refresh_token: Optional[str] = None  # solo microsoft
    expires_at: Optional[datetime] = None
    # para skins
    skin_variant: str = "classic"  # "classic" | "slim"

    def is_expired(self) -> bool: ...
    def to_dict(self) -> dict: ...
    @staticmethod
    def from_dict(data: dict) -> "Account": ...
```

**Variables/constantes:**
- `OFFLINE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")` — se usa como namespace para UUID v3 (formato Mojang offline: `OfflinePlayer:<name>`).
- `USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,16}$")`

---

## 3. `offline.py` — Funciones

```python
import uuid, re

USERNAME_REGEX: re.Pattern
OFFLINE_NAMESPACE: uuid.UUID

def validate_username(username: str) -> tuple[bool, str]:
    """Valida 3-16 chars, alfanumérico + _. Retorna (ok, motivo)."""
    ...

def generate_offline_uuid(username: str) -> str:
    """UUID v3 determinístico. Ej: uuid3(NAMESPACE, f'OfflinePlayer:{username}'). 
       Retorna con guiones."""
    raw: str = str(uuid.uuid3(OFFLINE_NAMESPACE, f"OfflinePlayer:{username}"))
    return raw  # ya viene con guiones

def create_offline_account(username: str) -> Account:
    """Valida -> genera UUID -> retorna Account(type=OFFLINE). 
       Lanza ValueError si username inválido."""
    username_stripped: str = username.strip()
    account_uuid: str = generate_offline_uuid(username_stripped)
    return Account(uuid=account_uuid, name=username_stripped, type=AccountType.OFFLINE)

def format_uuid_no_dashes(uuid_str: str) -> str: ...
def format_uuid_with_dashes(uuid_str: str) -> str: ...
```

**Flujo `create_offline_account`:**
1. `username_stripped = username.strip()`
2. `ok, reason = validate_username(username_stripped)` → si falla, `raise ValueError(reason)`
3. `account_uuid = generate_offline_uuid(username_stripped)`
4. `return Account(...)`

---

## 4. `microsoft.py` — Clase Wrapper

```python
from minecraft_launcher_lib import microsoft_account as msa
from .models import Account, AccountType

# Constantes
MICROSOFT_CLIENT_ID: str = "00000000402b5328"  # client público de MSA (o el tuyo)
MICROSOFT_REDIRECT_URI: str = "https://login.live.com/oauth20_desktop.srf"
TOKEN_REFRESH_MARGIN_SEC: int = 60  # refresca 60s antes de expirar

class MicrosoftAuthService:
    def __init__(self, client_id: str = MICROSOFT_CLIENT_ID): 
        self.client_id: str = client_id
        self._auth_state: dict | None = None

    # --- OAuth ---
    def get_login_url(self) -> str:
        """Retorna URL de login. Guarda state interno. Usa msa.get_login_url()."""
        login_url: str
        state: str
        login_url, state, code_verifier = msa.get_secure_login_data(self.client_id, MICROSOFT_REDIRECT_URI)
        self._auth_state = {"state": state, "code_verifier": code_verifier}
        return login_url

    def complete_login(self, auth_code_or_url: str) -> Account:
        """Intercambia code/url por Account. 
           Internamente: msa.complete_login(...) -> {access_token, refresh_token, ...}
           Luego msa.get_minecraft_profile(token) para uuid/name."""
        ...

    def refresh_account(self, account: Account) -> Account:
        """Si is_expired() intenta msa.refresh_token(). Si falla, lanza TokenRefreshError."""
        ...

    def is_token_valid(self, account: Account) -> bool:
        """True si account.type==MICROSOFT y not is_expired() y tokens no None."""
        ...

    # --- Helpers ---
    def _parse_auth_code_from_url(self, url: str) -> str: ...
    def _build_account_from_msa_response(self, msa_data: dict) -> Account: ...
```

**Excepciones propias:**
```python
class AuthError(Exception): ...
class TokenRefreshError(AuthError): ...
class InvalidUsernameError(ValueError): ...
```

**Flujo login Microsoft (OAuth):**
```
QML -> auth_bridge.getLoginUrl() -> MicrosoftAuthService.get_login_url() -> abre navegador
Usuario loguea -> redirect con ?code=XXX -> QML captura URL -> complete_login(url)
  -> extrae code -> msa.complete_login(client_id, None, redirect_uri, code, code_verifier)
  -> msa_data = {access_token, ...}
  -> profile = msa_data["minecraft_profile"]  # uuid, name
  -> Account(uuid=profile["id_formatted"], name=profile["name"], type=MICROSOFT, ...)
```

---

## 5. Persistencia (propuesto `store.py`)

```python
from pathlib import Path
import json

ACCOUNTS_FILE: str = "accounts.json"

class AuthStore:
    def __init__(self, data_dir: Path): 
        self.data_dir: Path = data_dir
        self.accounts_file: Path = data_dir / ACCOUNTS_FILE

    def load_accounts(self) -> list[Account]: ...
    def save_accounts(self, accounts: list[Account]) -> None: ...
    def get_selected_uuid(self) -> str | None: ...
    def set_selected_uuid(self, uuid: str | None) -> None: ...
    def add_or_update(self, account: Account) -> None: ...
    def remove(self, uuid: str) -> None: ...
```

---

## 6. Conexión con `bridge/auth_bridge.py`

- `AuthBridge.login_offline(username: str)` → llama `create_offline_account` → `authStore.add_or_update` → emite `accountChanged` + `loginSuccess`
- `AuthBridge.get_login_url()` → `msa_service.get_login_url()`
- `AuthBridge.complete_microsoft_login(url: str)` → corre en `QThread` porque es red → al terminar emite `loginSuccess(Account.to_dict())` o `loginError(str)`

---

## 7. Tests sugeridos (`tests/test_auth.py`)

- `test_generate_offline_uuid_is_deterministic` — mismo nombre → mismo UUID
- `test_validate_username_rejects_invalid_chars`
- `test_create_offline_account_raises_on_empty`
- Mock de `minecraft_launcher_lib.microsoft_account` para `test_complete_login_builds_account`
- `test_refresh_returns_new_tokens`

---

## 8. Variables resumen

| Variable | Tipo | Dónde | Propósito |
|---|---|---|---|
| `account_uuid` | `str` | offline.py | UUID con guiones |
| `username_stripped` | `str` | offline.py | Nombre saneado |
| `msa_data` | `dict` | microsoft.py | Respuesta cruda de MSA |
| `code_verifier` | `str` | microsoft.py | PKCE verifier |
| `access_token` | `str` | models.py | Token Bearer |
| `expires_at` | `datetime` | models.py | Expiración para refresh |
