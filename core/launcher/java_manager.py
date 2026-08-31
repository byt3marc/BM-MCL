from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable, cast

try:
    import minecraft_launcher_lib.java_utils as jutils
    import minecraft_launcher_lib.runtime as runtime
except ImportError:
    jutils = None
    runtime = None


JAVA_RUNTIME_MAP = {
    "8": "java-runtime-gamma",
    "17": "java-runtime-gamma",
    "21": "java-runtime-delta",
}


class LauncherError(Exception):
    pass


class JavaNotFoundError(LauncherError):
    pass


class JavaInstallError(LauncherError):
    pass


class JavaManager:
    def __init__(
        self,
        minecraft_dir: Path | str,
        java_path: Path | str | None = None,
    ) -> None:
        self.minecraft_dir = Path(minecraft_dir)
        self.java_path = Path(java_path) if java_path is not None else None
        self._java_cache: dict[str, str] = {}

    def get_java_executable(self, version_id: str | None = None) -> str:
        if self.java_path is not None and self.is_java_available(self.java_path):
            return str(self.java_path)
        if version_id:
            try:
                return self.ensure_java_for_version(version_id)
            except JavaNotFoundError:
                pass
        system_java = self.find_system_java()
        if system_java:
            return system_java
        raise JavaNotFoundError("No se encontró una instalación de Java utilizable.")

    def find_system_java(self) -> str | None:
        candidate = shutil.which("java")
        if not candidate or not self.is_java_available(candidate):
            return None
        if jutils is not None:
            try:
                jutils.get_java_information(candidate)
            except Exception:
                return None
        return candidate

    def ensure_java_for_version(
        self,
        version_id: str,
        callback: Callable[[str], None] | None = None,
    ) -> str:
        if not isinstance(version_id, str) or not version_id:
            raise JavaNotFoundError("El identificador de versión es obligatorio.")
        jvm_version = self.get_jvm_version_for(version_id)
        cached = self._java_cache.get(jvm_version)
        if cached and self.is_java_available(cached):
            return cached
        if runtime is None:
            system_java = self.find_system_java()
            if system_java:
                return system_java
            raise JavaNotFoundError("minecraft_launcher_lib no está instalado y no hay Java del sistema.")
        try:
            java_executable = runtime.get_executable_path(jvm_version, self.minecraft_dir)
            if not java_executable or not self.is_java_available(java_executable):
                self._notify(callback, f"Instalando Java {jvm_version}...")
                runtime.install_jvm_runtime(
                    jvm_version,
                    self.minecraft_dir,
                    callback=cast(Any, self._runtime_callbacks(callback)),
                )
                java_executable = runtime.get_executable_path(jvm_version, self.minecraft_dir)
        except Exception as error:
            raise JavaInstallError(f"No se pudo instalar Java para {version_id}.") from error
        if not java_executable or not self.is_java_available(java_executable):
            raise JavaNotFoundError(f"No se encontró Java para la versión {version_id}.")
        resolved_path = str(java_executable)
        self._java_cache[jvm_version] = resolved_path
        return resolved_path

    def get_jvm_version_for(self, version_id: str) -> str:
        version_json_path = self.minecraft_dir / "versions" / version_id / f"{version_id}.json"
        try:
            version_data = json.loads(version_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return JAVA_RUNTIME_MAP["17"]
        java_version = version_data.get("javaVersion")
        if not isinstance(java_version, dict):
            return JAVA_RUNTIME_MAP["17"]
        component = java_version.get("component")
        if isinstance(component, str) and component:
            return component
        major_version = java_version.get("majorVersion")
        return JAVA_RUNTIME_MAP.get(str(major_version), JAVA_RUNTIME_MAP["17"])

    @staticmethod
    def is_java_available(java_path: str | Path) -> bool:
        path = Path(java_path)
        return path.is_file() and os.access(path, os.X_OK)

    def clear_cache(self) -> None:
        self._java_cache.clear()

    @staticmethod
    def _notify(callback: Callable[[str], None] | None, message: str) -> None:
        if callback is not None:
            callback(message)

    @staticmethod
    def _runtime_callbacks(callback: Callable[[str], None] | None) -> dict[str, Callable[[Any], None]]:
        if callback is None:
            return {}
        return {
            "setStatus": lambda status: callback(str(status)),
            "setProgress": lambda _: None,
            "setMax": lambda _: None,
        }
