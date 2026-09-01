from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping, MutableMapping
from http.client import HTTPException
from pathlib import Path
from typing import Protocol, TypeGuard, cast
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


class HttpResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> object: ...


class HttpSession(Protocol):
    headers: MutableMapping[str, str]

    def get(self, url: str, *, timeout: float) -> HttpResponse: ...


class HttpHeaders(Protocol):
    def get(self, key: str, default: str = "") -> str | None: ...


class UrllibResponse(Protocol):
    headers: HttpHeaders

    def close(self) -> None: ...

    def getcode(self) -> int | None: ...

    def read(self) -> bytes: ...


class SkinManager:
    def __init__(self, cache: SkinCache, http_session: HttpSession | None = None) -> None:
        self.cache: SkinCache = cache
        self.session: HttpSession | None = http_session
        if self.session is not None:
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
        if not self._is_json_list(properties):
            return None
        encoded_textures = next(
            (
                property_data.get("value")
                for property_ in properties
                if self._is_json_object(property_data := property_)
                and property_data.get("name") == "textures"
            ),
            None,
        )
        if not isinstance(encoded_textures, str):
            return None
        try:
            textures_data = self._decode_json_object(base64.b64decode(encoded_textures, validate=True))
            if textures_data is None:
                raise ValueError("El campo textures debe ser un objeto JSON.")
            textures = textures_data.get("textures")
            if not self._is_json_object(textures):
                raise ValueError("Falta el objeto textures.")
            skin_data = textures.get("SKIN")
            if not self._is_json_object(skin_data):
                raise ValueError("Falta la skin del perfil.")
            texture_url = skin_data.get("url")
        except (binascii.Error, ValueError) as error:
            raise SkinDownloadError("El perfil de Mojang contiene datos de skin inválidos.") from error
        if not isinstance(texture_url, str):
            return None
        metadata = skin_data.get("metadata")
        variant = "slim" if self._is_json_object(metadata) and metadata.get("model") == "slim" else "classic"
        image_bytes = self._download(texture_url)
        return (image_bytes, variant) if image_bytes is not None else None

    def _download(self, url: str) -> bytes | None:
        try:
            if self.session is not None:
                response = self.session.get(url, timeout=10)
                status_code = response.status_code
                content_type = response.headers.get("Content-Type", "")
                content = response.content
            else:
                request = Request(url, headers={"User-Agent": "BML/1.0"})
                response = cast(UrllibResponse, urlopen(request, timeout=10))
                try:
                    status_code = response.getcode()
                    content_type = response.headers.get("Content-Type", "") or ""
                    content = response.read()
                finally:
                    response.close()
        except (HTTPException, OSError, URLError, ValueError):
            return None
        if status_code != 200 or "image/png" not in content_type.lower():
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
    def _clean_uuid(account_uuid: object) -> str:
        if not isinstance(account_uuid, str):
            raise SkinError("UUID inválido.")
        clean_uuid = account_uuid.replace("-", "").lower()
        if len(clean_uuid) != 32 or any(character not in "0123456789abcdef" for character in clean_uuid):
            raise SkinError("UUID inválido.")
        return clean_uuid

    @staticmethod
    def _validate_png_bytes(data: bytes) -> tuple[bool, str]:
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            return False, "El archivo no es un PNG válido."
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if width != SKIN_WIDTH or height not in {32, SKIN_HEIGHT}:
            return False, "La skin debe medir 64x64 o 64x32 píxeles."
        return True, ""

    def _get_json(self, url: str) -> dict[str, object] | None:
        try:
            if self.session is not None:
                response = self.session.get(url, timeout=10)
                if response.status_code != 200:
                    return None
                payload = response.json()
            else:
                request = Request(url, headers={"User-Agent": "BML/1.0"})
                response = cast(UrllibResponse, urlopen(request, timeout=10))
                try:
                    if response.getcode() != 200:
                        return None
                    payload = self._decode_json_object(response.read())
                finally:
                    response.close()
        except (HTTPException, OSError, URLError, ValueError):
            return None
        return payload if self._is_json_object(payload) else None

    @staticmethod
    def _decode_json_object(payload: bytes) -> dict[str, object] | None:
        try:
            decoded = cast(object, json.loads(payload))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return decoded if SkinManager._is_json_object(decoded) else None

    @staticmethod
    def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
        if not isinstance(value, dict):
            return False
        json_object = cast(dict[object, object], value)
        return all(isinstance(key, str) for key in json_object)

    @staticmethod
    def _is_json_list(value: object) -> TypeGuard[list[object]]:
        return isinstance(value, list)
