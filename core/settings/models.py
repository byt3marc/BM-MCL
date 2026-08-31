from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_RAM_MIN = 1024
DEFAULT_RAM_MAX = 4096
MIN_RAM_MB = 512
MAX_RAM_MB = 32768
DEFAULT_THEME = "dark"
SUPPORTED_THEMES = {"dark", "light"}


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
        if not isinstance(self.install_dir, Path) or not str(self.install_dir).strip():
            errors.append("install_dir debe ser una ruta válida")
        if not _is_integer(self.ram_min_mb) or self.ram_min_mb < MIN_RAM_MB:
            errors.append(f"ram_min_mb debe ser un entero mayor o igual a {MIN_RAM_MB}")
        if not _is_integer(self.ram_max_mb) or self.ram_max_mb > MAX_RAM_MB:
            errors.append(f"ram_max_mb debe ser un entero menor o igual a {MAX_RAM_MB}")
        if _is_integer(self.ram_min_mb) and _is_integer(self.ram_max_mb) and self.ram_max_mb < self.ram_min_mb:
            errors.append("ram_max_mb debe ser mayor o igual a ram_min_mb")
        if self.java_path is not None and not isinstance(self.java_path, Path):
            errors.append("java_path debe ser una ruta o nulo")
        if not isinstance(self.show_snapshots, bool):
            errors.append("show_snapshots debe ser booleano")
        if not isinstance(self.keep_launcher_open, bool):
            errors.append("keep_launcher_open debe ser booleano")
        if not _is_integer(self.window_width) or self.window_width <= 0:
            errors.append("window_width debe ser un entero positivo")
        if not _is_integer(self.window_height) or self.window_height <= 0:
            errors.append("window_height debe ser un entero positivo")
        if self.selected_account_uuid is not None and not isinstance(self.selected_account_uuid, str):
            errors.append("selected_account_uuid debe ser texto o nulo")
        if self.theme not in SUPPORTED_THEMES:
            errors.append("theme debe ser 'dark' o 'light'")
        if not isinstance(self.language, str) or not self.language.strip():
            errors.append("language debe ser texto no vacío")
        if not _is_integer(self.concurrent_downloads) or not 1 <= self.concurrent_downloads <= 16:
            errors.append("concurrent_downloads debe estar entre 1 y 16")
        return errors

    def clamp_ram(self) -> None:
        ram_min = self.ram_min_mb if _is_integer(self.ram_min_mb) else DEFAULT_RAM_MIN
        ram_max = self.ram_max_mb if _is_integer(self.ram_max_mb) else DEFAULT_RAM_MAX
        self.ram_min_mb = min(max(ram_min, MIN_RAM_MB), MAX_RAM_MB)
        self.ram_max_mb = min(max(ram_max, self.ram_min_mb), MAX_RAM_MB)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["install_dir"] = str(self.install_dir)
        data["java_path"] = str(self.java_path) if self.java_path else None
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Settings":
        if not isinstance(data, dict):
            raise ValueError("Los ajustes deben ser un objeto JSON.")
        defaults = Settings.defaults()
        values = defaults.to_dict()
        fields = set(values)
        values.update({key: value for key, value in data.items() if key in fields})
        try:
            install_dir = Path(str(values["install_dir"])).expanduser()
            raw_java_path = values["java_path"]
            java_path = Path(str(raw_java_path)).expanduser() if raw_java_path else None
        except (TypeError, ValueError) as error:
            raise ValueError("Las rutas de los ajustes son inválidas.") from error
        return Settings(
            install_dir=install_dir,
            ram_min_mb=values["ram_min_mb"],
            ram_max_mb=values["ram_max_mb"],
            java_path=java_path,
            show_snapshots=values["show_snapshots"],
            keep_launcher_open=values["keep_launcher_open"],
            window_width=values["window_width"],
            window_height=values["window_height"],
            selected_account_uuid=values["selected_account_uuid"],
            theme=values["theme"],
            language=values["language"],
            concurrent_downloads=values["concurrent_downloads"],
        )

    @staticmethod
    def defaults(data_dir: Path | None = None) -> "Settings":
        if data_dir is None:
            return Settings()
        return Settings(install_dir=Path(data_dir).expanduser() / "minecraft")


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
