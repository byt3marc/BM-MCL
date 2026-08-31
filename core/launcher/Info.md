# launcher — Diseño del módulo

> **Objetivo:** Lanzar Minecraft. Gestiona Java (auto-instalación vía `minecraft_launcher_lib.runtime`) y construye el comando de lanzamiento (`minecraft_launcher_lib.command`). Sin Qt en `core`; `bridge` lo envuelve con `QProcess`/`QThread`.

---

## 1. Archivos y responsabilidad

| Archivo | Rol |
|---|---|
| `core/launcher/java_manager.py` | Detecta/instala Java runtime correcto para cada versión. Wrapper sobre `minecraft_launcher_lib.java_utils` y `runtime`. |
| `core/launcher/service.py` | `LauncherService` — construye comando y lanza el proceso. Único que importa `minecraft_launcher_lib.command`. |

**Dependencias:** `minecraft_launcher_lib.command`, `minecraft_launcher_lib.runtime`, `minecraft_launcher_lib.java_utils`, `subprocess`, `pathlib`, `shlex`.

---

## 2. `java_manager.py` — Clase

```python
from pathlib import Path
from typing import Optional, Callable
import minecraft_launcher_lib.java_utils as jutils
import minecraft_launcher_lib.runtime as runtime

JAVA_RUNTIME_MAP: dict[str, str] = {
    # Mapeo simplificado; la lib ya lo hace, pero útil para logs
    "8": "java-runtime-gamma",
    "17": "java-runtime-gamma",
    "21": "java-runtime-delta",
}

class JavaManager:
    def __init__(self, minecraft_dir: Path | str):
        self.minecraft_dir: Path = Path(minecraft_dir)
        self._java_cache: dict[str, str] = {}  # version_id -> java_path

    def get_java_executable(self, version_id: str | None = None) -> str:
        """Retorna path al java.exe/javaw.
           Prioridad: 1) settings.java_path si existe, 2) runtime de Mojang, 3) java del sistema."""
        ...

    def find_system_java(self) -> Optional[str]:
        """Usa jutils.get_java_information() / shutil.which('java').
           Retorna None si no hay."""
        ...

    def ensure_java_for_version(
        self,
        version_id: str,
        callback: Callable[[str], None] | None = None
        # callback(status_text)
    ) -> str:
        """Asegura Java para esa versión.
           1. Lee <minecraft_dir>/versions/<version_id>/<version_id>.json -> javaVersion.majorVersion
           2. runtime.get_executable_path(jvmVersion, minecraft_dir, callback)
           3. Cachea y retorna path.
           Lanza JavaNotFoundError si falla."""
        ...

    def get_jvm_version_for(self, version_id: str) -> str:
        """Parsea el json de la versión para extraer javaVersion.component."""
        ...

    def is_java_available(self, java_path: str | Path) -> bool:
        """Comprueba exists() y ejecutable."""
        ...

    def clear_cache(self) -> None: ...
```

**Variables internas:**
- `minecraft_dir: Path`
- `_java_cache: dict[str, str]` — evita re-resolver
- `jvm_version: str` — ej. "17", "21"
- `java_executable: str` — path absoluto
- `callback_status: Callable[[str], None]`

**Flujo `ensure_java_for_version("1.20.1")`:**
```
jvm_version = get_jvm_version_for("1.20.1")  # lee json, fallback "17"
if jvm_version in _java_cache and is_java_available(_java_cache[jvm_version]): return _cached
try:
  java_path = runtime.get_executable_path(jvm_version, str(minecraft_dir), callback_dict)
  # callback_dict = {"setStatus": fn, "setProgress": fn}
except Exception as e: raise JavaInstallError(...)
_java_cache[jvm_version] = java_path
return java_path
```

---

## 3. `service.py` — Clase principal

```python
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, List
import subprocess
import minecraft_launcher_lib.command as mll_cmd

from core.auth.models import Account
from core.settings.models import Settings
from .java_manager import JavaManager

@dataclass(frozen=True, slots=True)
class LaunchOptions:
    version_id: str
    account: Account
    settings: Settings
    minecraft_dir: Path
    java_path: Optional[str] = None  # override
    extra_jvm_args: list[str] | None = None
    extra_game_args: list[str] | None = None
    # para logs
    quick_play_singleplayer: Optional[str] = None

@dataclass(slots=True)
class LaunchResult:
    command: list[str]
    process: subprocess.Popen | None
    java_path: str
    minecraft_dir: Path

class LauncherService:
    def __init__(self, minecraft_dir: Path | str, java_manager: JavaManager | None = None):
        self.minecraft_dir: Path = Path(minecraft_dir)
        self.java_manager: JavaManager = java_manager or JavaManager(self.minecraft_dir)
        self._process: subprocess.Popen | None = None
        self._is_running: bool = False

    # ---------- Validación ----------
    def validate_preconditions(self, options: LaunchOptions) -> list[str]:
        """Retorna errores (vacío si OK). Chequea: versión instalada, account no None, ram válida."""
        ...

    # ---------- Construcción del comando ----------
    def build_command(self, options: LaunchOptions) -> list[str]:
        """Construye el comando usando mll_cmd.get_minecraft_command().
           Inyecta ram, java_path, resolution, etc."""
        ...

    def _build_mll_options(self, options: LaunchOptions) -> dict:
        """Convierte LaunchOptions -> dict que espera get_minecraft_command."""
        mll_options: dict = {
            "username": options.account.name,
            "uuid": options.account.uuid,
            "token": options.account.access_token or "0",  # offline token dummy
            # java
            "executablePath": options.java_path or self.java_manager.get_java_executable(options.version_id),
            # ram
            "jvmArguments": [f"-Xmx{options.settings.ram_max_mb}M", f"-Xms{options.settings.ram_min_mb}M"] + (options.extra_jvm_args or []),
            # resolución opcional
            # "gameDirectory": str(options.minecraft_dir),
        }
        return mll_options

    # ---------- Lanzamiento ----------
    def launch(
        self,
        options: LaunchOptions,
        on_log: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
        detach: bool = False
    ) -> LaunchResult:
        """Bloqueante si detach=False (espera y stream logs).
           Si detach=True lanza y retorna inmediatamente.
           Usa subprocess.Popen."""
        ...

    def launch_detached(self, options: LaunchOptions) -> LaunchResult:
        """Alias de launch(detach=True). Para QProcess en bridge."""
        ...

    def is_running(self) -> bool:
        return self._is_running and self._process is not None and self._process.poll() is None

    def terminate(self) -> None:
        """Mata proceso hijo si existe."""
        if self._process and self.is_running():
            self._process.terminate()

    def get_logs(self) -> list[str]: ...
```

**Firma de `minecraft_launcher_lib.command.get_minecraft_command`:**
```python
# Real:
mll_cmd.get_minecraft_command(
    version: str,
    minecraft_directory: str | Path,
    options: dict  # username, uuid, token, etc.
) -> list[str]
```

**Flujo `launch()`:**
```
validate_preconditions(options) -> si errores: raise LaunchValidationError
java_path = java_manager.ensure_java_for_version(version_id, callback)
options.java_path = java_path
command: list[str] = build_command(options)  # -> ["C:/.../java.exe", "-Xmx4096M", ..., "net.minecraft.client.main.Main", ...]
log_command: str = shlex.join(command)  # para debug (sin token)
_process = subprocess.Popen(command, cwd=str(minecraft_dir), stdout=PIPE, stderr=STDOUT, text=True, bufsize=1)
_is_running = True
if not detach:
  for line in _process.stdout: on_log(line)
  exit_code = _process.wait()
  _is_running = False
  on_exit(exit_code)
return LaunchResult(command, _process, java_path, minecraft_dir)
```

---

## 4. Errores

```python
class LauncherError(Exception): ...
class JavaNotFoundError(LauncherError): ...
class JavaInstallError(LauncherError): ...
class VersionNotInstalledError(LauncherError): ...
class LaunchValidationError(LauncherError): ...
class LaunchFailedError(LauncherError): ...
```

---

## 5. Conexión con `bridge` (QProcess / QThread)

`core/launcher/service.py` usa `subprocess` (testeable). El `bridge/launcher_bridge.py` lo adapta a Qt:

- `LauncherBridge.launch(versionId: str)` → crea `QThread` → dentro llama `launcherService.launch(options, on_log=emit logLine, on_exit=emit exited)`
- Alternativa Qt-nativa: usa `QProcess` en vez de `subprocess.Popen` para no bloquear UI.
- Señales: `logLine(str)`, `launched()`, `exited(int code)`, `launchError(str)`, `javaProgress(str)`
- Propiedad `isRunning: bool`

---

## 6. Tests sugeridos

- Mock `mll_cmd.get_minecraft_command` → `test_build_command_includes_ram_args`
- Mock `runtime.get_executable_path` → `test_ensure_java_caches_result`
- `test_validate_fails_if_version_not_installed` (mock `get_installed_versions`)
- `test_launch_calls_popen_with_correct_cwd` (mock `subprocess.Popen`)
- `test_terminate_kills_process`

---

## 7. Variables resumen

| Variable | Tipo | Propósito |
|---|---|---|
| `minecraft_dir` | `Path` | Directorio de instalación |
| `version_id` | `str` | Ej. "1.20.1" |
| `java_executable` | `str` | Path a java.exe |
| `jvm_version` | `str` | "8"/"17"/"21" |
| `mll_options` | `dict` | Dict para get_minecraft_command |
| `command` | `list[str]` | Comando final |
| `_process` | `Popen\|None` | Proceso hijo |
| `_is_running` | `bool` | Estado |
| `ram_max_mb` / `ram_min_mb` | `int` | De Settings |
| `account` | `Account` | Cuenta con uuid/token |
