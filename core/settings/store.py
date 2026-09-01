from __future__ import annotations

import datetime
import json
import os
import platform
from pathlib import Path
from typing import cast

from .models import JsonObject, Settings, is_json_object

APP_NAME = "BML"
SETTINGS_FILE = "settings.json"
DATA_DIR_ENV = "BML_DATA_DIR"
CURRENT_SCHEMA_VERSION = 1


class SettingsError(Exception):
    pass


class SettingsValidationError(SettingsError):
    def __init__(self, errors: list[str]) -> None:
        self.errors: list[str] = errors
        super().__init__("; ".join(errors))


class SettingsCorruptError(SettingsError):
    pass


class SettingsStore:
    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir: Path = Path(data_dir).expanduser() if data_dir is not None else self.resolve_data_dir()
        self.settings_path: Path = self.data_dir / SETTINGS_FILE
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

    def save(self, settings: object) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("settings debe ser una instancia de Settings.")
        errors = settings.validate()
        if errors:
            raise SettingsValidationError(errors)
        data = settings.to_dict()
        if not is_json_object(data):
            raise SettingsValidationError(["Los ajustes no son serializables como JSON."])
        data["__version__"] = CURRENT_SCHEMA_VERSION
        self._write_json(data)
        self._cached_settings = settings
        self._cached_mtime_ns = self._get_mtime_ns()

    def update(self, patch: object) -> Settings:
        if not is_json_object(patch):
            raise TypeError("patch debe ser un objeto JSON.")
        allowed_fields = set(Settings().to_dict())
        unknown_fields = set(patch) - allowed_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise SettingsValidationError([f"Campos de ajustes desconocidos: {names}"])
        data = self.load().to_dict()
        if not is_json_object(data):
            raise SettingsError("Los ajustes almacenados no son serializables como JSON.")
        data.update(patch)
        settings = Settings.from_dict(data)
        self.save(settings)
        return settings

    def reset_to_defaults(self) -> Settings:
        settings = Settings.defaults(self.data_dir)
        self.save(settings)
        return settings

    def _migrate(self, raw: object) -> JsonObject:
        if not is_json_object(raw):
            raise SettingsCorruptError("El archivo de ajustes debe contener un objeto JSON.")
        version = raw.get("__version__", 1)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise SettingsCorruptError("La versión del archivo de ajustes es inválida.")
        migrated = dict(raw)
        _ = migrated.pop("__version__", None)
        if version <= 1:
            if "theme" not in migrated:
                migrated["theme"] = "dark"
            if "language" not in migrated:
                migrated["language"] = "es"
            if "concurrent_downloads" not in migrated:
                migrated["concurrent_downloads"] = 4
        return migrated

    def _backup_corrupt_file(self) -> None:
        if not self.settings_path.exists():
            return
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S")
        backup_path = self.settings_path.with_name(f"{SETTINGS_FILE}.bak.{timestamp}")
        try:
            _ = self.settings_path.replace(backup_path)
        except OSError as error:
            raise SettingsCorruptError("No se pudo respaldar el archivo de ajustes corrupto.") from error

    def _read_json(self) -> JsonObject:
        try:
            raw = cast(object, json.loads(self.settings_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as error:
            raise SettingsCorruptError("No se pudo leer el archivo de ajustes.") from error
        if not is_json_object(raw):
            raise SettingsCorruptError("El archivo de ajustes debe contener un objeto JSON.")
        return raw

    def _write_json(self, data: JsonObject) -> None:
        self.ensure_data_dir()
        temporary_path = self.settings_path.with_suffix(".tmp")
        try:
            _ = temporary_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _ = temporary_path.replace(self.settings_path)
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
