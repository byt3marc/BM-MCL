from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol, TypedDict, TypeGuard, cast

from .models import VersionInfo, VersionType

MANIFEST_CACHE_SEC = 3600
ProgressCallback = Callable[[int], None]
MaxCallback = Callable[[int], None]
StatusCallback = Callable[[str], None]


class InstallCallbacks(TypedDict, total=False):
    setStatus: StatusCallback
    setProgress: ProgressCallback
    setMax: MaxCallback


class _LauncherCallbackDict(TypedDict):
    setStatus: StatusCallback
    setProgress: ProgressCallback
    setMax: MaxCallback


class _LauncherInstall(Protocol):
    def install_minecraft_version(
        self,
        version: str,
        minecraft_directory: str,
        callback: _LauncherCallbackDict,
    ) -> None: ...


class _LauncherUtils(Protocol):
    def get_installed_versions(self, minecraft_directory: str) -> list[object]: ...

    def get_version_list(self) -> object: ...


def _as_launcher_install(module: object) -> _LauncherInstall:
    return cast(_LauncherInstall, module)


def _as_launcher_utils(module: object) -> _LauncherUtils:
    return cast(_LauncherUtils, module)


try:
    import minecraft_launcher_lib.install as _mll_install
    import minecraft_launcher_lib.utils as _mll_utils
except ImportError:
    mll_install: _LauncherInstall | None = None
    mll_utils: _LauncherUtils | None = None
else:
    mll_install = _as_launcher_install(_mll_install)
    mll_utils = _as_launcher_utils(_mll_utils)


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
        self.minecraft_dir: Path = Path(minecraft_dir)
        self._cache: list[VersionInfo] | None = None
        self._cache_timestamp: float | None = None
        self._installed_cache: set[str] | None = None
        self._callbacks: InstallCallbacks = {}

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
                match version:
                    case str() as version_id:
                        installed_ids.add(version_id)
                    case {"id": str() as version_id}:
                        installed_ids.add(version_id)
                    case _:
                        pass
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
        if not version_id:
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
        callbacks: InstallCallbacks | None = None,
        java_callback: Callable[[str], None] | None = None,
    ) -> None:
        if not version_id:
            raise VersionNotFoundError("El identificador de versión es obligatorio.")
        if self.is_installed(version_id):
            return
        if self.get_version_info(version_id) is None:
            raise VersionNotFoundError(f"No existe la versión {version_id}.")
        if mll_install is None:
            raise InstallError("minecraft_launcher_lib no está instalado.")
        self._callbacks = callbacks or {}
        if java_callback is not None:
            java_callback(f"Instalando Minecraft {version_id}...")
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        callback_dict: _LauncherCallbackDict = {
            "setStatus": self._map_set_status,
            "setProgress": self._map_set_progress,
            "setMax": self._map_set_max,
        }
        try:
            mll_install.install_minecraft_version(
                version=version_id,
                minecraft_directory=str(self.minecraft_dir),
                callback=callback_dict,
            )
        except Exception as error:
            raise InstallError(f"No se pudo instalar la versión {version_id}.") from error
        finally:
            self._callbacks = {}
        self.clear_cache()

    def _map_set_status(self, text: str) -> None:
        callback = self._callbacks.get("setStatus")
        if callback is not None:
            callback(text)

    def _map_set_progress(self, value: int) -> None:
        callback = self._callbacks.get("setProgress")
        if callback is not None:
            callback(value)

    def _map_set_max(self, value: int) -> None:
        callback = self._callbacks.get("setMax")
        if callback is not None:
            callback(value)

    def _fetch_raw_list(self) -> object:
        if mll_utils is None:
            raise NetworkError("minecraft_launcher_lib no está instalado.")
        return mll_utils.get_version_list()

    def _parse_raw_list(self, raw: object) -> list[VersionInfo]:
        raw_versions = _manifest_versions(raw)
        if raw_versions is None:
            raise TypeError("La lista de versiones es inválida.")
        versions: list[VersionInfo] = []
        for raw_version in raw_versions:
            try:
                versions.append(VersionInfo.from_mojang_dict(raw_version))
            except (TypeError, ValueError):
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


def _manifest_versions(raw: object) -> list[object] | None:
    if _is_object_list(raw):
        return raw
    if not _is_string_keyed_dict(raw):
        return None
    raw_versions = raw.get("versions")
    return raw_versions if _is_object_list(raw_versions) else None


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _is_string_keyed_dict(value: object) -> TypeGuard[dict[str, object]]:
    if not isinstance(value, dict):
        return False
    dictionary = cast(dict[object, object], value)
    return all(isinstance(key, str) for key in dictionary)
