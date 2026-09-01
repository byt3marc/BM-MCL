from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol, TextIO, cast, final

import minecraft_launcher_lib.command as mll_cmd
from minecraft_launcher_lib.types import MinecraftOptions

from core.auth.models import Account
from core.settings.models import Settings

from .java_manager import JavaManager, LauncherError


class _MinecraftCommandApi(Protocol):
    def get_minecraft_command(
        self,
        version: str,
        minecraft_directory: str,
        options: MinecraftOptions,
    ) -> list[str]: ...


def _as_minecraft_command_api(command_module: object) -> _MinecraftCommandApi:
    return cast(_MinecraftCommandApi, command_module)


_minecraft_command_api = _as_minecraft_command_api(mll_cmd)


@final
class VersionNotInstalledError(LauncherError):
    pass


@final
class LaunchValidationError(LauncherError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@final
class LaunchFailedError(LauncherError):
    pass


@dataclass(frozen=True, slots=True)
class LaunchOptions:
    version_id: str
    account: Account
    settings: Settings
    minecraft_dir: Path
    java_path: str | None = None
    extra_jvm_args: list[str] | None = None
    extra_game_args: list[str] | None = None
    quick_play_singleplayer: str | None = None


@dataclass(slots=True)
class LaunchResult:
    command: list[str]
    process: subprocess.Popen[str] | None
    java_path: str
    minecraft_dir: Path


@final
class LauncherService:
    def __init__(
        self,
        minecraft_dir: Path | str,
        java_manager: JavaManager | None = None,
    ) -> None:
        self.minecraft_dir = Path(minecraft_dir)
        self.java_manager = java_manager or JavaManager(self.minecraft_dir)
        self._process: subprocess.Popen[str] | None = None
        self._is_running = False
        self._logs: list[str] = []

    def validate_preconditions(self, options: LaunchOptions) -> list[str]:
        errors: list[str] = []
        if not options.version_id:
            errors.append("Debe seleccionarse una versión.")
        elif not (options.minecraft_dir / "versions" / options.version_id / f"{options.version_id}.json").is_file():
            errors.append(f"La versión {options.version_id} no está instalada.")
        errors.extend(options.settings.validate())
        if options.java_path is not None and not self.java_manager.is_java_available(options.java_path):
            errors.append("La ruta de Java configurada no es ejecutable.")
        return errors

    def build_command(self, options: LaunchOptions) -> list[str]:
        errors = self.validate_preconditions(options)
        if errors:
            raise LaunchValidationError(errors)
        mll_options = self._build_mll_options(options)
        try:
            command = _minecraft_command_api.get_minecraft_command(
                options.version_id,
                str(options.minecraft_dir),
                mll_options,
            )
        except Exception as error:
            raise LaunchFailedError("No se pudo construir el comando de Minecraft.") from error
        return command + (options.extra_game_args or [])

    def _build_mll_options(self, options: LaunchOptions) -> MinecraftOptions:
        java_path = options.java_path or self.java_manager.get_java_executable(options.version_id)
        mll_options: MinecraftOptions = {
            "username": options.account.name,
            "uuid": options.account.uuid,
            "token": options.account.access_token or "0",
            "executablePath": java_path,
            "jvmArguments": [
                f"-Xmx{options.settings.ram_max_mb}M",
                f"-Xms{options.settings.ram_min_mb}M",
                *(options.extra_jvm_args or []),
            ],
            "gameDirectory": str(options.minecraft_dir),
        }
        if options.quick_play_singleplayer:
            mll_options["quickPlaySingleplayer"] = options.quick_play_singleplayer
        return mll_options

    def launch(
        self,
        options: LaunchOptions,
        on_log: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
        on_java_status: Callable[[str], None] | None = None,
        on_started: Callable[[], None] | None = None,
        detach: bool = False,
    ) -> LaunchResult:
        errors = self.validate_preconditions(options)
        if errors:
            raise LaunchValidationError(errors)
        java_path = options.java_path or self.java_manager.ensure_java_for_version(
            options.version_id,
            on_java_status,
        )
        resolved_options = replace(options, java_path=java_path)
        command = self.build_command(resolved_options)
        self._logs.clear()
        try:
            process = subprocess.Popen(
                command,
                cwd=str(resolved_options.minecraft_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as error:
            raise LaunchFailedError("No se pudo iniciar el proceso de Minecraft.") from error
        self._process = process
        self._is_running = True
        result = LaunchResult(command, process, java_path, resolved_options.minecraft_dir)
        if on_started is not None:
            on_started()
        if detach:
            return result
        try:
            if process.stdout is not None:
                output = cast(TextIO, process.stdout)
                for line in output:
                    self._logs.append(line.rstrip("\r\n"))
                    if on_log is not None:
                        on_log(line)
        finally:
            exit_code = process.wait()
            self._is_running = False
        if on_exit is not None:
            on_exit(exit_code)
        return result

    def launch_detached(self, options: LaunchOptions) -> LaunchResult:
        return self.launch(options, detach=True)

    def is_running(self) -> bool:
        return self._is_running and self._process is not None and self._process.poll() is None

    def terminate(self) -> None:
        if self._process is not None and self.is_running():
            self._process.terminate()

    def get_logs(self) -> list[str]:
        return list(self._logs)
