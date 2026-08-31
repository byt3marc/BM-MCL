from __future__ import annotations

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Settings


APP_NAME = "BML"
SETTINGS_FILE = "settings.json"
DATA_DIR_ENV = "BML_DATA_DIR"
CURRENT_SCHEMA_VERSION = 1


class SettingsError(Exception):
    pass


class SettingsValidationError(SettingsError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class SettingsCorruptError(SettingsError):
    pass


class SettingsStore:
    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir).expanduser() if data_dir is not None else self.resolve_data_dir()
        self.settings_path = self.data_dir / SETTINGS_FILE
        self._cached_settings: Settings | None = None
        self._cached_mtime_ns: int | None = None

    @staticmethod
    def resolve_data_dir() -> Path:
        env_override = os.getenv(DATA_DIR_ENV)
        if env_override:
            return Path(env_override).expanduser()
        system = platform.system()
        if system == "Windows":
            return Path(os.getenv("APPDATA", str(Path.home()))) / APP_NAME
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        return Path.home() / ".config" / APP_NAME

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_minecraft_dir(self) -> Path:
        return self.load().install_dir.expanduser()

    def load(self) -> Settings:
        if self._is_cache_current() and self._cached_settings is not None:
            return self._cached_settings
        if not self.settings_path.exists():
            settings = Settings.defaults(self.data_dir)
            self.save(settings)
            return settings
        try:
            raw = self._read_json()
            migrated = self._migrate(raw)
            settings = Settings.from_dict(migrated)
        except (SettingsCorruptError, ValueError, TypeError):
            self._backup_corrupt_file()
            settings = Settings.defaults(self.data_dir)
            self.save(settings)
            return settings
        if settings.validate():
            settings.clamp_ram()
            if settings.validate():
                settings = Settings.defaults(self.data_dir)
            self.save(settings)
            return settings
        self._cached_settings = settings
        self._cached_mtime_ns = self._get_mtime_ns()
        return settings

    def save(self, settings: Settings) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("settings debe ser una instancia de Settings.")
        errors = settings.validate()
        if errors:
            raise SettingsValidationError(errors)
        data = settings.to_dict()
        data["__version__"] = CURRENT_SCHEMA_VERSION
        self._write_json(data)
        self._cached_settings = settings
        self._cached_mtime_ns = self._get_mtime_ns()

    def update(self, patch: dict[str, Any]) -> Settings:
        if not isinstance(patch, dict):
            raise TypeError("patch debe ser un objeto.")
        allowed_fields = set(Settings().to_dict())
        unknown_fields = set(patch) - allowed_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise SettingsValidationError([f"Campos de ajustes desconocidos: {names}"])
        data = self.load().to_dict()
        data.update(patch)
        settings = Settings.from_dict(data)
        self.save(settings)
        return settings

    def reset_to_defaults(self) -> Settings:
        settings = Settings.defaults(self.data_dir)
        self.save(settings)
        return settings

    def _migrate(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise SettingsCorruptError("El archivo de ajustes debe contener un objeto JSON.")
        version = raw.get("__version__", 1)
        if not isinstance(version, int) or version < 1:
            raise SettingsCorruptError("La versión del archivo de ajustes es inválida.")
        migrated = dict(raw)
        migrated.pop("__version__", None)
        if version <= 1:
            migrated.setdefault("theme", "dark")
            migrated.setdefault("language", "es")
            migrated.setdefault("concurrent_downloads", 4)
        return migrated

    def _backup_corrupt_file(self) -> None:
        if not self.settings_path.exists():
            return
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = self.settings_path.with_name(f"{SETTINGS_FILE}.bak.{timestamp}")
        try:
            self.settings_path.replace(backup_path)
        except OSError as error:
            raise SettingsCorruptError("No se pudo respaldar el archivo de ajustes corrupto.") from error

    def _read_json(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SettingsCorruptError("No se pudo leer el archivo de ajustes.") from error
        if not isinstance(raw, dict):
            raise SettingsCorruptError("El archivo de ajustes debe contener un objeto JSON.")
        return raw

    def _write_json(self, data: dict[str, Any]) -> None:
        self.ensure_data_dir()
        temporary_path = self.settings_path.with_suffix(".tmp")
        try:
            temporary_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(self.settings_path)
        except OSError as error:
            raise SettingsError("No se pudo guardar el archivo de ajustes.") from error

    def _is_cache_current(self) -> bool:
        return (
            self._cached_settings is not None
            and self._cached_mtime_ns is not None
            and self._cached_mtime_ns == self._get_mtime_ns()
        )

    def _get_mtime_ns(self) -> int | None:
        try:
            return self.settings_path.stat().st_mtime_ns
        except FileNotFoundError:
            return None
