from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


CACHE_DIR_NAME = "skins"
CACHE_FILE_EXT = ".png"
CACHE_META_EXT = ".json"
CACHE_EXPIRY_DAYS = 7
MAX_CACHE_SIZE_MB = 100


class SkinCache:
    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / CACHE_DIR_NAME
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, datetime] | None = None

    def get_skin_path(self, account_uuid: str) -> Path:
        return self.cache_dir / f"{self._normalize_uuid(account_uuid)}{CACHE_FILE_EXT}"

    def get_meta_path(self, account_uuid: str) -> Path:
        return self.get_skin_path(account_uuid).with_suffix(CACHE_META_EXT)

    def get_cache_dir(self) -> Path:
        return self.cache_dir

    def is_cached(self, account_uuid: str) -> bool:
        return self.get_skin_path(account_uuid).is_file()

    def is_expired(self, account_uuid: str) -> bool:
        skin_path = self.get_skin_path(account_uuid)
        if not skin_path.is_file():
            return True
        modified_at = datetime.fromtimestamp(skin_path.stat().st_mtime)
        return datetime.now() - modified_at > timedelta(days=CACHE_EXPIRY_DAYS)

    def get_cached_bytes(self, account_uuid: str) -> bytes | None:
        skin_path = self.get_skin_path(account_uuid)
        return skin_path.read_bytes() if skin_path.is_file() else None

    def put(self, account_uuid: str, image_bytes: bytes, variant: str = "classic") -> Path:
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise ValueError("La imagen de la skin debe contener bytes.")
        self._validate_variant(variant)
        skin_path = self.get_skin_path(account_uuid)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary_path = skin_path.with_suffix(".tmp")
        temporary_path.write_bytes(image_bytes)
        temporary_path.replace(skin_path)
        self._write_meta(account_uuid, variant, self._hash_bytes(image_bytes))
        self.ensure_within_limit()
        return skin_path

    def put_from_path(self, account_uuid: str, source_path: Path | str, variant: str = "classic") -> Path:
        path = Path(source_path)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el archivo de skin: {path}")
        return self.put(account_uuid, path.read_bytes(), variant)

    def invalidate(self, account_uuid: str) -> None:
        for path in (self.get_skin_path(account_uuid), self.get_meta_path(account_uuid)):
            if path.exists():
                path.unlink()

    def clear(self) -> None:
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index = None

    def clear_expired(self) -> int:
        removed = 0
        for skin_path in self.cache_dir.glob(f"*{CACHE_FILE_EXT}"):
            account_uuid = skin_path.stem
            if self.is_expired(account_uuid):
                self.invalidate(account_uuid)
                removed += 1
        return removed

    def get_metadata(self, account_uuid: str) -> dict[str, Any]:
        meta_path = self.get_meta_path(account_uuid)
        if not meta_path.is_file():
            return {}
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return metadata if isinstance(metadata, dict) else {}

    def update_variant(self, account_uuid: str, variant: str) -> None:
        self._validate_variant(variant)
        image_bytes = self.get_cached_bytes(account_uuid)
        if image_bytes is None:
            raise FileNotFoundError("No hay una skin en caché para esta cuenta.")
        self._write_meta(account_uuid, variant, self._hash_bytes(image_bytes))

    def _hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:12]

    def _write_meta(self, account_uuid: str, variant: str, hash_str: str) -> None:
        metadata = {
            "variant": variant,
            "hash": hash_str,
            "cached_at": datetime.now().isoformat(),
        }
        self.get_meta_path(account_uuid).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_cache_size_mb(self) -> float:
        total_bytes = sum(
            path.stat().st_size
            for path in self.cache_dir.glob("*")
            if path.is_file()
        )
        return total_bytes / (1024 * 1024)

    def ensure_within_limit(self) -> None:
        limit_bytes = MAX_CACHE_SIZE_MB * 1024 * 1024
        skin_paths = sorted(
            self.cache_dir.glob(f"*{CACHE_FILE_EXT}"),
            key=lambda path: path.stat().st_mtime,
        )
        total_bytes = sum(
            path.stat().st_size
            for path in self.cache_dir.glob("*")
            if path.is_file()
        )
        for skin_path in skin_paths:
            if total_bytes <= limit_bytes:
                break
            meta_path = skin_path.with_suffix(CACHE_META_EXT)
            total_bytes -= skin_path.stat().st_size
            skin_path.unlink()
            if meta_path.is_file():
                total_bytes -= meta_path.stat().st_size
                meta_path.unlink()

    @staticmethod
    def _normalize_uuid(account_uuid: str) -> str:
        if not isinstance(account_uuid, str):
            raise TypeError("uuid debe ser texto.")
        clean_uuid = account_uuid.replace("-", "").lower()
        if len(clean_uuid) != 32 or any(character not in "0123456789abcdef" for character in clean_uuid):
            raise ValueError("UUID inválido.")
        return clean_uuid

    @staticmethod
    def _validate_variant(variant: str) -> None:
        if variant not in {"classic", "slim"}:
            raise ValueError("variant debe ser 'classic' o 'slim'.")
