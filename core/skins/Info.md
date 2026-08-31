# skins — Diseño del módulo

> **Objetivo:** Gestionar skins de cuentas offline y premium. Cache local en `data/skins/`, fetching desde Mojang/Crafatar y soporte para modelo `classic`/`slim`. Sin Qt.

---

## 1. Archivos y responsabilidad

| Archivo | Rol |
|---|---|
| `core/skins/cache.py` | `SkinCache` — I/O de archivos, TTL, hash, limpieza. |
| `core/skins/manager.py` | `SkinManager` — lógica de negocio: resolver URL, descargar, aplicar, fallback. |

**Dependencias:** `requests` (o `urllib.request` para evitar extra), `Pillow` (opcional, validar PNG), `pathlib`, `hashlib`, `datetime`.

---

## 2. `cache.py` — Clase

```python
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

CACHE_DIR_NAME: str = "skins"
CACHE_FILE_EXT: str = ".png"
CACHE_META_EXT: str = ".json"
CACHE_EXPIRY_DAYS: int = 7
MAX_CACHE_SIZE_MB: int = 100

class SkinCache:
    def __init__(self, data_dir: Path | str):
        self.data_dir: Path = Path(data_dir)
        self.cache_dir: Path = self.data_dir / CACHE_DIR_NAME
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, datetime] | None = None  # uuid -> cached_at

    # ---------- Paths ----------
    def get_skin_path(self, uuid: str) -> Path:
        """<cache_dir>/<uuid>.png  (uuid con guiones normalizado a sin guiones lowercase)"""
        clean_uuid: str = uuid.replace("-", "").lower()
        return self.cache_dir / f"{clean_uuid}{CACHE_FILE_EXT}"

    def get_meta_path(self, uuid: str) -> Path:
        return self.get_skin_path(uuid).with_suffix(CACHE_META_EXT)

    def get_cache_dir(self) -> Path: return self.cache_dir

    # ---------- Estado ----------
    def is_cached(self, uuid: str) -> bool:
        return self.get_skin_path(uuid).exists()

    def is_expired(self, uuid: str) -> bool:
        """True si no existe o mtime > CACHE_EXPIRY_DAYS."""
        skin_path: Path = self.get_skin_path(uuid)
        if not skin_path.exists(): return True
        mtime: datetime = datetime.fromtimestamp(skin_path.stat().st_mtime)
        return datetime.now() - mtime > timedelta(days=CACHE_EXPIRY_DAYS)

    def get_cached_bytes(self, uuid: str) -> bytes | None: ...

    # ---------- Escritura ----------
    def put(self, uuid: str, image_bytes: bytes, variant: str = "classic") -> Path:
        """Escribe PNG + meta JSON {variant, hash, cached_at}. Retorna Path."""
        ...

    def put_from_path(self, uuid: str, source_path: Path, variant: str = "classic") -> Path:
        """Copia archivo local al caché."""
        ...

    def invalidate(self, uuid: str) -> None:
        """Borra .png + .json de ese uuid."""
        ...

    def clear(self) -> None:
        """Borra todo el cache_dir."""
        ...

    def clear_expired(self) -> int:
        """Borra solo expirados. Retorna count borrados."""
        ...

    # ---------- Helpers ----------
    def _hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:12]

    def _write_meta(self, uuid: str, variant: str, hash_str: str) -> None: ...

    def get_cache_size_mb(self) -> float: ...

    def ensure_within_limit(self) -> None:
        """Si > MAX_CACHE_SIZE_MB borra los más viejos (LRU)."""
        ...
```

**Variables:**
- `cache_dir: Path` — `data/skins`
- `clean_uuid: str` — uuid sin guiones
- `image_bytes: bytes` — PNG crudo
- `variant: str` — "classic" | "slim"
- `cached_at: datetime`

---

## 3. `manager.py` — Clase principal

```python
from pathlib import Path
from typing import Optional
import requests

from .cache import SkinCache

# Endpoints
MOJANG_PROFILE_URL: str = "https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
CRAFATAR_SKIN_URL: str = "https://crafatar.com/skins/{uuid}"
CRAFATAR_RENDER_URL: str = "https://crafatar.com/renders/body/{uuid}?overlay"
MINECRAFT_TEXTURE_URL: str = "https://textures.minecraft.net/texture/{hash}"

DEFAULT_SKIN_VARIANT: str = "classic"
SKIN_WIDTH: int = 64
SKIN_HEIGHT: int = 64

class SkinManager:
    def __init__(self, cache: SkinCache, http_session: requests.Session | None = None):
        self.cache: SkinCache = cache
        self.session: requests.Session = http_session or requests.Session()
        self.session.headers.update({"User-Agent": "BML/1.0"})

    # ---------- URLs ----------
    def get_skin_url(self, uuid: str) -> str:
        """URL directa para <Image> en QML. Prioriza Crafatar."""
        clean: str = uuid.replace("-", "")
        return CRAFATAR_SKIN_URL.format(uuid=clean)

    def get_render_url(self, uuid: str) -> str:
        """Render 3D body para preview."""
        clean: str = uuid.replace("-", "")
        return CRAFATAR_RENDER_URL.format(uuid=clean)

    # ---------- Fetch ----------
    def fetch_skin(self, uuid: str, force_refresh: bool = False) -> Path | None:
        """Retorna Path al PNG cacheado (descarga si hace falta).
           Flujo: si is_cached y not expired y not force -> retorna.
           Si no: GET Crafatar -> si 200 -> cache.put() -> retorna Path.
           Si falla: intenta Mojang profile -> extrae texture hash -> descarga.
           Si todo falla: retorna None (usar Steve/Alex por defecto)."""
        ...

    def fetch_skin_bytes(self, uuid: str) -> tuple[bytes, str] | None:
        """Retorna (bytes, variant) o None."""
        ...

    def _fetch_from_crafatar(self, uuid: str) -> bytes | None: ...

    def _fetch_from_mojang(self, uuid: str) -> tuple[bytes, str] | None:
        """1. GET sessionserver profile -> textures -> SKIN url + metadata.model (slim)"""
        ...

    def _download(self, url: str) -> bytes | None:
        """GET con timeout=10, valida status 200 y content-type image/png."""
        ...

    # ---------- Aplicación local (offline) ----------
    def apply_local_skin(self, account_uuid: str, skin_path: Path, variant: str = "classic") -> Path:
        """Copia skin_path al caché para ese uuid. Valida PNG 64x64 o 64x32.
           Retorna nuevo Path cacheado. Lanza InvalidSkinError si no es PNG."""
        ...

    def get_variant(self, uuid: str) -> str:
        """Lee meta json -> 'classic'|'slim', default 'classic'."""
        ...

    def set_variant(self, uuid: str, variant: str) -> None:
        """Actualiza meta sin re-descargar."""
        ...

    # ---------- Helpers UI ----------
    def get_fallback_skin(self, variant: str = "classic") -> Path:
        """Retorna path a assets/default_steve.png o alex.png"""
        ...

    def validate_skin_file(self, path: Path) -> tuple[bool, str]:
        """Comprueba existe, es PNG, tamaño 64x64. Retorna (ok, reason)."""
        ...
```

**Flujo `fetch_skin("069a79f4-...")`:**
```
clean_uuid = uuid.replace("-","")
cached_path = cache.get_skin_path(uuid)
if cache.is_cached(uuid) and not cache.is_expired(uuid) and not force_refresh:
    return cached_path

# intenta Crafatar
png_bytes = _fetch_from_crafatar(clean_uuid)
variant = "classic"  # Crafatar no dice, se asume classic hasta Mojang
if png_bytes is None:
    result = _fetch_from_mojang(clean_uuid)  # -> (bytes, variant)
    if result: png_bytes, variant = result
if png_bytes is None:
    return None  # caller usa fallback

return cache.put(uuid, png_bytes, variant)
```

**Flujo `_fetch_from_mojang`:**
```
GET https://sessionserver.mojang.com/session/minecraft/profile/{clean_uuid}
-> json: {properties: [{value: base64}]}
-> decode base64 -> {textures: {SKIN: {url: "http://textures.minecraft.net/texture/<hash>", metadata: {model:"slim"}}}}
-> variant = "slim" if metadata.model=="slim" else "classic"
-> GET url -> bytes
-> return (bytes, variant)
```

---

## 4. Errores

```python
class SkinError(Exception): ...
class SkinNotFoundError(SkinError): ...
class InvalidSkinError(SkinError): ...
class SkinDownloadError(SkinError): ...
```

---

## 5. Conexión con `bridge` / QML

- `SkinBridge` expone:
  - `@Slot(str, result=str) getSkinUrl(uuid: str) -> str` → `manager.get_skin_url(uuid)` (para `Image { source: skinBridge.getSkinUrl(account.uuid) }`)
  - `@Slot(str, result=str) getCachedPath(uuid: str) -> str` → `cache.get_skin_path(uuid)` si existe, sino fallback
  - `@Slot(str, str) fetchSkin(uuid: str)` → lanza `QThread` → `manager.fetch_skin` → emite `skinReady(str uuid, str path)` o `skinError(str)`
- En QML: `Image { source: "file://" + skinBridge.getCachedPath(uuid) }` + `onSkinReady: reload()`
- Para offline: `FileDialog` → `skinBridge.applyLocalSkin(uuid, fileUrl, variant)`

---

## 6. Tests sugeridos

- `test_get_skin_path_normalizes_uuid` (con y sin guiones)
- `test_is_expired_true_if_old` (mock mtime)
- `test_put_and_is_cached_roundtrip` (tmp_path)
- Mock `requests.Session.get` → `test_fetch_skin_uses_cache_if_fresh`
- Mock 404 Crafatar → `test_fetch_falls_back_to_mojang`
- `test_validate_skin_rejects_non_png`

---

## 7. Variables resumen

| Variable | Tipo | Propósito |
|---|---|---|
| `cache_dir` | `Path` | `data/skins` |
| `clean_uuid` | `str` | UUID sin guiones |
| `image_bytes` | `bytes` | PNG de la skin |
| `variant` | `str` | "classic" (Steve) / "slim" (Alex) |
| `skin_path` | `Path` | Ruta final en caché |
| `profile_json` | `dict` | Respuesta de sessionserver |
| `texture_url` | `str` | URL de textures.minecraft.net |
| `fallback_path` | `Path` | Skin por defecto |
