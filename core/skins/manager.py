from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .cache import SkinCache


MOJANG_PROFILE_URL = "https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
CRAFATAR_SKIN_URL = "https://crafatar.com/skins/{uuid}"
CRAFATAR_RENDER_URL = "https://crafatar.com/renders/body/{uuid}?overlay"
MINECRAFT_TEXTURE_URL = "https://textures.minecraft.net/texture/{hash}"
DEFAULT_SKIN_VARIANT = "classic"
SKIN_WIDTH = 64
SKIN_HEIGHT = 64


class SkinError(Exception):
    pass


class SkinNotFoundError(SkinError):
    pass


class InvalidSkinError(SkinError):
    pass


class SkinDownloadError(SkinError):
    pass


class SkinManager:
    def __init__(self, cache: SkinCache, http_session: Any | None = None) -> None:
        self.cache = cache
        self.session = http_session
        if self.session is not None and hasattr(self.session, "headers"):
            self.session.headers.update({"User-Agent": "BML/1.0"})

    def get_skin_url(self, account_uuid: str) -> str:
        clean_uuid = self._clean_uuid(account_uuid)
        return CRAFATAR_SKIN_URL.format(uuid=clean_uuid)

    def get_render_url(self, account_uuid: str) -> str:
        clean_uuid = self._clean_uuid(account_uuid)
        return CRAFATAR_RENDER_URL.format(uuid=clean_uuid)

    def fetch_skin(self, account_uuid: str, force_refresh: bool = False) -> Path | None:
        if self.cache.is_cached(account_uuid) and not self.cache.is_expired(account_uuid) and not force_refresh:
            return self.cache.get_skin_path(account_uuid)
        clean_uuid = self._clean_uuid(account_uuid)
        image_bytes = self._fetch_from_crafatar(clean_uuid)
        variant = DEFAULT_SKIN_VARIANT
        if image_bytes is None:
            result = self._fetch_from_mojang(clean_uuid)
            if result is None:
                return None
            image_bytes, variant = result
        valid, _ = self._validate_png_bytes(image_bytes)
        if not valid:
            return None
        return self.cache.put(account_uuid, image_bytes, variant)

    def fetch_skin_bytes(self, account_uuid: str) -> tuple[bytes, str] | None:
        skin_path = self.fetch_skin(account_uuid)
        if skin_path is None:
            return None
        image_bytes = skin_path.read_bytes()
        return image_bytes, self.get_variant(account_uuid)

    def _fetch_from_crafatar(self, account_uuid: str) -> bytes | None:
        return self._download(CRAFATAR_SKIN_URL.format(uuid=self._clean_uuid(account_uuid)))

    def _fetch_from_mojang(self, account_uuid: str) -> tuple[bytes, str] | None:
        profile = self._get_json(MOJANG_PROFILE_URL.format(uuid=self._clean_uuid(account_uuid)))
        if profile is None:
            return None
        properties = profile.get("properties")
        if not isinstance(properties, list):
            return None
        encoded_textures = next(
            (
                property_.get("value")
                for property_ in properties
                if isinstance(property_, dict) and property_.get("name") == "textures"
            ),
            None,
        )
        if not isinstance(encoded_textures, str):
            return None
        try:
            textures_data = json.loads(base64.b64decode(encoded_textures, validate=True))
            skin_data = textures_data["textures"]["SKIN"]
            texture_url = skin_data["url"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise SkinDownloadError("El perfil de Mojang contiene datos de skin inválidos.") from error
        if not isinstance(texture_url, str):
            return None
        metadata = skin_data.get("metadata", {})
        variant = "slim" if isinstance(metadata, dict) and metadata.get("model") == "slim" else "classic"
        image_bytes = self._download(texture_url)
        return (image_bytes, variant) if image_bytes is not None else None

    def _download(self, url: str) -> bytes | None:
        try:
            if self.session is not None:
                response = self.session.get(url, timeout=10)
                status_code = getattr(response, "status_code", None)
                headers = getattr(response, "headers", {})
                content = getattr(response, "content", b"")
            else:
                request = Request(url, headers={"User-Agent": "BML/1.0"})
                with urlopen(request, timeout=10) as response:
                    status_code = response.getcode()
                    headers = response.headers
                    content = response.read()
        except (OSError, URLError, Exception):
            return None
        content_type = headers.get("Content-Type", "") if hasattr(headers, "get") else ""
        if status_code != 200 or "image/png" not in content_type.lower() or not isinstance(content, bytes):
            return None
        return content

    def apply_local_skin(
        self,
        account_uuid: str,
        skin_path: Path | str,
        variant: str = DEFAULT_SKIN_VARIANT,
    ) -> Path:
        path = Path(skin_path)
        valid, reason = self.validate_skin_file(path)
        if not valid:
            raise InvalidSkinError(reason)
        if variant not in {"classic", "slim"}:
            raise InvalidSkinError("El modelo de skin debe ser 'classic' o 'slim'.")
        return self.cache.put_from_path(account_uuid, path, variant)

    def get_variant(self, account_uuid: str) -> str:
        variant = self.cache.get_metadata(account_uuid).get("variant")
        return variant if variant in {"classic", "slim"} else DEFAULT_SKIN_VARIANT

    def set_variant(self, account_uuid: str, variant: str) -> None:
        if variant not in {"classic", "slim"}:
            raise InvalidSkinError("El modelo de skin debe ser 'classic' o 'slim'.")
        try:
            self.cache.update_variant(account_uuid, variant)
        except (FileNotFoundError, ValueError) as error:
            raise InvalidSkinError("No hay una skin almacenada para actualizar.") from error

    def get_fallback_skin(self, variant: str = DEFAULT_SKIN_VARIANT) -> Path:
        if variant not in {"classic", "slim"}:
            raise InvalidSkinError("El modelo de skin debe ser 'classic' o 'slim'.")
        filename = "default_alex.png" if variant == "slim" else "default_steve.png"
        return Path(__file__).resolve().parents[2] / "assets" / filename

    def validate_skin_file(self, path: Path | str) -> tuple[bool, str]:
        candidate = Path(path)
        if not candidate.is_file():
            return False, "El archivo de skin no existe."
        if candidate.suffix.lower() != ".png":
            return False, "La skin debe ser un archivo PNG."
        try:
            return self._validate_png_bytes(candidate.read_bytes())
        except OSError:
            return False, "No se pudo leer el archivo de skin."

    @staticmethod
    def _clean_uuid(account_uuid: str) -> str:
        try:
            return SkinCache._normalize_uuid(account_uuid)
        except (TypeError, ValueError) as error:
            raise SkinError("UUID inválido.") from error

    @staticmethod
    def _validate_png_bytes(data: bytes) -> tuple[bool, str]:
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            return False, "El archivo no es un PNG válido."
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if width != SKIN_WIDTH or height not in {32, SKIN_HEIGHT}:
            return False, "La skin debe medir 64x64 o 64x32 píxeles."
        return True, ""

    def _get_json(self, url: str) -> dict[str, Any] | None:
        try:
            if self.session is not None:
                response = self.session.get(url, timeout=10)
                if getattr(response, "status_code", None) != 200:
                    return None
                payload = response.json()
            else:
                request = Request(url, headers={"User-Agent": "BML/1.0"})
                with urlopen(request, timeout=10) as response:
                    if response.getcode() != 200:
                        return None
                    payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError, json.JSONDecodeError, Exception):
            return None
        return payload if isinstance(payload, dict) else None
