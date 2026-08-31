from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, cast

try:
    import minecraft_launcher_lib.install as mll_install
    import minecraft_launcher_lib.utils as mll_utils
except ImportError:
    mll_install = None
    mll_utils = None

from .models import VersionInfo, VersionType


MANIFEST_CACHE_SEC = 3600
ProgressCallback = Callable[[int], None]
MaxCallback = Callable[[int], None]
StatusCallback = Callable[[str], None]


class VersionError(Exception):
    pass


class VersionNotFoundError(VersionError):
    pass


class InstallError(VersionError):
    pass


class NetworkError(VersionError):
    pass


class VersionService:
    def __init__(self, minecraft_dir: Path | str) -> None:
        self.minecraft_dir = Path(minecraft_dir)
        self._cache: list[VersionInfo] | None = None
        self._cache_timestamp: float | None = None
        self._installed_cache: set[str] | None = None
        self._callbacks: dict[str, Callable[[Any], None]] = {}

    def get_available_versions(
        self,
        force_refresh: bool = False,
        include_snapshots: bool = False,
    ) -> list[VersionInfo]:
        if not force_refresh and self._cache_is_valid():
            versions = self._cache or []
        else:
            try:
                versions = self._parse_raw_list(self._fetch_raw_list())
            except VersionError:
                raise
            except Exception as error:
                raise NetworkError("No se pudo obtener la lista de versiones.") from error
            installed_ids = set(self.get_installed_versions())
            versions = [replace(version, installed=version.id in installed_ids) for version in versions]
            versions.sort(key=lambda version: version.release_time, reverse=True)
            self._cache = versions
            self._cache_timestamp = time.time()
        return self._filter_snapshots(versions, include_snapshots)

    def get_installed_versions(self) -> list[str]:
        if self._installed_cache is not None:
            return sorted(self._installed_cache)
        installed_ids: set[str] = set()
        if mll_utils is not None:
            try:
                raw_versions = mll_utils.get_installed_versions(str(self.minecraft_dir))
            except Exception as error:
                raise VersionError("No se pudieron leer las versiones instaladas.") from error
            for version in raw_versions:
                if isinstance(version, str):
                    installed_ids.add(version)
                elif isinstance(version, dict) and isinstance(version.get("id"), str):
                    installed_ids.add(version["id"])
        else:
            versions_dir = self.minecraft_dir / "versions"
            if versions_dir.is_dir():
                installed_ids = {
                    child.name
                    for child in versions_dir.iterdir()
                    if child.is_dir() and (child / f"{child.name}.json").is_file()
                }
        self._installed_cache = installed_ids
        return sorted(installed_ids)

    def is_installed(self, version_id: str) -> bool:
        return version_id in self.get_installed_versions()

    def get_version_info(self, version_id: str) -> VersionInfo | None:
        if not isinstance(version_id, str) or not version_id:
            return None
        return next(
            (
                version
                for version in self.get_available_versions(include_snapshots=True)
                if version.id == version_id
            ),
            None,
        )

    def install_version(
        self,
        version_id: str,
        callbacks: dict[str, Callable[[Any], None]] | None = None,
        java_callback: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(version_id, str) or not version_id:
            raise VersionNotFoundError("El identificador de versión es obligatorio.")
        if self.is_installed(version_id):
            return
        if self.get_version_info(version_id) is None:
            raise VersionNotFoundError(f"No existe la versión {version_id}.")
        if mll_install is None:
            raise InstallError("minecraft_launcher_lib no está instalado.")
        if callbacks is not None and not isinstance(callbacks, dict):
            raise TypeError("callbacks debe ser un diccionario o nulo.")
        self._callbacks = callbacks or {}
        if java_callback is not None:
            if not callable(java_callback):
                raise TypeError("java_callback debe ser invocable.")
            java_callback(f"Instalando Minecraft {version_id}...")
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        callback_dict = {
            "setStatus": self._map_set_status,
            "setProgress": self._map_set_progress,
            "setMax": self._map_set_max,
        }
        try:
            mll_install.install_minecraft_version(
                version=version_id,
                minecraft_directory=str(self.minecraft_dir),
                callback=cast(Any, callback_dict),
            )
        except Exception as error:
            raise InstallError(f"No se pudo instalar la versión {version_id}.") from error
        finally:
            self._callbacks = {}
        self.clear_cache()

    def _map_set_status(self, text: str) -> None:
        callback = self._callbacks.get("setStatus")
        if callable(callback):
            callback(str(text))

    def _map_set_progress(self, value: int) -> None:
        callback = self._callbacks.get("setProgress")
        if callable(callback):
            callback(int(value))

    def _map_set_max(self, value: int) -> None:
        callback = self._callbacks.get("setMax")
        if callable(callback):
            callback(int(value))

    def _fetch_raw_list(self) -> object:
        if mll_utils is None:
            raise NetworkError("minecraft_launcher_lib no está instalado.")
        return mll_utils.get_version_list()

    def _parse_raw_list(self, raw: object) -> list[VersionInfo]:
        raw_versions = raw.get("versions", []) if isinstance(raw, dict) else raw
        if not isinstance(raw_versions, list):
            raise ValueError("La lista de versiones es inválida.")
        versions: list[VersionInfo] = []
        for raw_version in raw_versions:
            if not isinstance(raw_version, dict):
                continue
            try:
                versions.append(VersionInfo.from_mojang_dict(raw_version))
            except ValueError:
                continue
        return versions

    @staticmethod
    def _filter_snapshots(versions: list[VersionInfo], include: bool) -> list[VersionInfo]:
        if include:
            return list(versions)
        return [version for version in versions if version.type is VersionType.RELEASE]

    def clear_cache(self) -> None:
        self._cache = None
        self._cache_timestamp = None
        self._installed_cache = None

    def _cache_is_valid(self) -> bool:
        return (
            self._cache is not None
            and self._cache_timestamp is not None
            and time.time() - self._cache_timestamp < MANIFEST_CACHE_SEC
        )
