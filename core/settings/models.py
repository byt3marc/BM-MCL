from __future__ import annotations

import typing
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RAM_MIN = 1024
DEFAULT_RAM_MAX = 4096
MIN_RAM_MB = 512
MAX_RAM_MB = 32768
DEFAULT_THEME = "dark"
SUPPORTED_THEMES = {"dark", "light"}

JsonPrimitive: typing.TypeAlias = str | int | float | bool | None
JsonValue: typing.TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: typing.TypeAlias = dict[str, JsonValue]


@dataclass(slots=True)
class Settings:
    install_dir: Path = field(default_factory=lambda: Path.home() / ".minecraft_bml")
    ram_min_mb: int = DEFAULT_RAM_MIN
    ram_max_mb: int = DEFAULT_RAM_MAX
    java_path: Path | None = None
    show_snapshots: bool = False
    keep_launcher_open: bool = True
    window_width: int = 1280
    window_height: int = 720
    selected_account_uuid: str | None = None
    theme: str = DEFAULT_THEME
    language: str = "es"
    concurrent_downloads: int = 4

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not _is_path(self.install_dir) or not str(self.install_dir).strip():
            errors.append("install_dir debe ser una ruta válida")
        if not _is_integer(self.ram_min_mb) or self.ram_min_mb < MIN_RAM_MB:
            errors.append(f"ram_min_mb debe ser un entero mayor o igual a {MIN_RAM_MB}")
        if not _is_integer(self.ram_max_mb) or self.ram_max_mb > MAX_RAM_MB:
            errors.append(f"ram_max_mb debe ser un entero menor o igual a {MAX_RAM_MB}")
        if _is_integer(self.ram_min_mb) and _is_integer(self.ram_max_mb) and self.ram_max_mb < self.ram_min_mb:
            errors.append("ram_max_mb debe ser mayor o igual a ram_min_mb")
        if self.java_path is not None and not _is_path(self.java_path):
            errors.append("java_path debe ser una ruta o nulo")
        if not _is_boolean(self.show_snapshots):
            errors.append("show_snapshots debe ser booleano")
        if not _is_boolean(self.keep_launcher_open):
            errors.append("keep_launcher_open debe ser booleano")
        if not _is_integer(self.window_width) or self.window_width <= 0:
            errors.append("window_width debe ser un entero positivo")
        if not _is_integer(self.window_height) or self.window_height <= 0:
            errors.append("window_height debe ser un entero positivo")
        if self.selected_account_uuid is not None and not _is_text(self.selected_account_uuid):
            errors.append("selected_account_uuid debe ser texto o nulo")
        if self.theme not in SUPPORTED_THEMES:
            errors.append("theme debe ser 'dark' o 'light'")
        if not _is_text(self.language) or not self.language.strip():
            errors.append("language debe ser texto no vacío")
        if not _is_integer(self.concurrent_downloads) or not 1 <= self.concurrent_downloads <= 16:
            errors.append("concurrent_downloads debe estar entre 1 y 16")
        return errors

    def clamp_ram(self) -> None:
        ram_min = self.ram_min_mb if _is_integer(self.ram_min_mb) else DEFAULT_RAM_MIN
        ram_max = self.ram_max_mb if _is_integer(self.ram_max_mb) else DEFAULT_RAM_MAX
        self.ram_min_mb = min(max(ram_min, MIN_RAM_MB), MAX_RAM_MB)
        self.ram_max_mb = min(max(ram_max, self.ram_min_mb), MAX_RAM_MB)

    def to_dict(self) -> dict[str, object]:
        return {
            "install_dir": str(self.install_dir),
            "ram_min_mb": self.ram_min_mb,
            "ram_max_mb": self.ram_max_mb,
            "java_path": str(self.java_path) if self.java_path else None,
            "show_snapshots": self.show_snapshots,
            "keep_launcher_open": self.keep_launcher_open,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "selected_account_uuid": self.selected_account_uuid,
            "theme": self.theme,
            "language": self.language,
            "concurrent_downloads": self.concurrent_downloads,
        }

    @staticmethod
    def from_dict(data: object) -> Settings:
        if not is_json_object(data):
            raise TypeError("Los ajustes deben ser un objeto JSON.")
        defaults = Settings.defaults()
        values = defaults.to_dict()
        if not is_json_object(values):
            raise RuntimeError("Los valores predeterminados no son serializables como JSON.")
        fields = set(values)
        values.update({key: value for key, value in data.items() if key in fields})
        try:
            return Settings(
                install_dir=_require_path(values["install_dir"]),
                ram_min_mb=_require_integer(values["ram_min_mb"]),
                ram_max_mb=_require_integer(values["ram_max_mb"]),
                java_path=_require_optional_path(values["java_path"]),
                show_snapshots=_require_boolean(values["show_snapshots"]),
                keep_launcher_open=_require_boolean(values["keep_launcher_open"]),
                window_width=_require_integer(values["window_width"]),
                window_height=_require_integer(values["window_height"]),
                selected_account_uuid=_require_optional_text(values["selected_account_uuid"]),
                theme=_require_text(values["theme"]),
                language=_require_text(values["language"]),
                concurrent_downloads=_require_integer(values["concurrent_downloads"]),
            )
        except ValueError as error:
            raise ValueError("Los ajustes contienen valores de tipo inválido.") from error

    @staticmethod
    def defaults(data_dir: Path | None = None) -> Settings:
        if data_dir is None:
            return Settings()
        return Settings(install_dir=Path(data_dir).expanduser() / "minecraft")


def is_json_object(value: object) -> typing.TypeGuard[JsonObject]:
    if not isinstance(value, dict):
        return False
    items = typing.cast(dict[object, object], value).items()
    return all(isinstance(key, str) and _is_json_value(item) for key, item in items)


def _is_json_value(value: object) -> typing.TypeGuard[JsonValue]:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        items = typing.cast(list[object], value)
        return all(_is_json_value(item) for item in items)
    return is_json_object(value)


def _is_path(value: object) -> typing.TypeGuard[Path]:
    return isinstance(value, Path)


def _is_boolean(value: object) -> typing.TypeGuard[bool]:
    return isinstance(value, bool)


def _is_text(value: object) -> typing.TypeGuard[str]:
    return isinstance(value, str)


def _is_integer(value: object) -> typing.TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_path(value: JsonValue) -> Path:
    if not _is_text(value):
        raise ValueError
    return Path(value).expanduser()


def _require_optional_path(value: JsonValue) -> Path | None:
    if value is None:
        return None
    return _require_path(value)


def _require_boolean(value: JsonValue) -> bool:
    if not _is_boolean(value):
        raise ValueError
    return value


def _require_text(value: JsonValue) -> str:
    if not _is_text(value):
        raise ValueError
    return value


def _require_optional_text(value: JsonValue) -> str | None:
    if value is None:
        return None
    return _require_text(value)


def _require_integer(value: JsonValue) -> int:
    if not _is_integer(value):
        raise ValueError
    return value
