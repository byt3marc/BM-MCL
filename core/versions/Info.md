# versions — Diseño del módulo

> **Objetivo:** Adaptador (Adapter) sobre `minecraft_launcher_lib`. Convierte los dicts crudos de la lib en `VersionInfo` propio, lista/instala versiones y reporta progreso via callbacks. Sin Qt.

---

## 1. Archivos y responsabilidad

| Archivo | Rol |
|---|---|
| `core/versions/models.py` | `VersionInfo`, `VersionType`, `InstallProgress` — dataclasses desacopladas. |
| `core/versions/service.py` | `VersionService` — ADAPTER. Único que importa `minecraft_launcher_lib.utils` e `install`. |

**Dependencias permitidas:** `minecraft_launcher_lib.utils`, `minecraft_launcher_lib.install`, `minecraft_launcher_lib.forge` (opcional), `pathlib`, `datetime`, `json`.

---

## 2. Modelos — `models.py`

```python
from dataclasses import dataclass
from enum import StrEnum
from datetime import datetime
from typing import Optional

class VersionType(StrEnum):
    RELEASE = "release"
    SNAPSHOT = "snapshot"
    OLD_BETA = "old_beta"
    OLD_ALPHA = "old_alpha"
    # opcional: fabric/forge si los soportas
    # FABRIC = "fabric"

@dataclass(frozen=True, slots=True)
class VersionInfo:
    id: str                 # "1.20.1"
    type: VersionType       # RELEASE / SNAPSHOT
    release_time: datetime  # parseado de "releaseTime"
    time: Optional[datetime] = None  # "time" (último update)
    url: Optional[str] = None        # url del manifest
    installed: bool = False          # calculado al listar

    def to_dict(self) -> dict: ...
    @staticmethod
    def from_mojang_dict(data: dict) -> "VersionInfo": ...

@dataclass(frozen=True, slots=True)
class InstallProgress:
    current: int    # bytes o files actuales
    total: int      # max
    status: str     # "Downloading 1.20.1 ..."

# Para QML: versión instalada local
@dataclass(frozen=True, slots=True)
class InstalledVersion:
    id: str
    path: str       # Path en disco: <minecraft_dir>/versions/1.20.1/
    last_played: Optional[datetime] = None
```

**Variables/constantes:**
- `MANIFEST_CACHE_SEC: int = 3600` — TTL del caché en memoria
- `DATE_FMT: str = "%Y-%m-%dT%H:%M:%S+00:00"` — formato Mojang

---

## 3. `service.py` — Clase principal

```python
from pathlib import Path
from typing import Callable, Optional, List
import minecraft_launcher_lib.utils as mll_utils
import minecraft_launcher_lib.install as mll_install

ProgressCallback = Callable[[int], None]      # setProgress(current)
MaxCallback = Callable[[int], None]          # setMax(total)
StatusCallback = Callable[[str], None]       # setStatus(text)

class VersionService:
    def __init__(self, minecraft_dir: Path | str):
        self.minecraft_dir: Path = Path(minecraft_dir)
        self._cache: list[VersionInfo] | None = None
        self._cache_timestamp: float | None = None  # time.time()
        self._installed_cache: set[str] | None = None

    # ---------- Lectura ----------
    def get_available_versions(
        self,
        force_refresh: bool = False,
        include_snapshots: bool = False
    ) -> list[VersionInfo]:
        """Retorna lista filtrada y ordenada (releaseTime desc).
           Usa caché si no expiró y force_refresh==False."""
        ...

    def get_installed_versions(self) -> list[str]:
        """Lee <minecraft_dir>/versions/*/ *.json -> ids instalados.
           Delega en mll_utils.get_installed_versions(minecraft_dir)."""
        ...

    def is_installed(self, version_id: str) -> bool: ...

    def get_version_info(self, version_id: str) -> VersionInfo | None:
        """Busca en get_available_versions()."""
        ...

    # ---------- Instalación ----------
    def install_version(
        self,
        version_id: str,
        callbacks: dict | None = None,
        # callbacks = {"setStatus": fn, "setProgress": fn, "setMax": fn}
        java_callback: Callable[[str], None] | None = None
    ) -> None:
        """Bloqueante. Llama a mll_install.install_minecraft_version().
           Lanza VersionNotFoundError / InstallError."""
        ...

    def _map_set_status(self, text: str) -> None: ...
    def _map_set_progress(self, value: int) -> None: ...
    def _map_set_max(self, value: int) -> None: ...

    # ---------- Utils ----------
    def _fetch_raw_list(self) -> dict:
        """Wrapper testeable sobre mll_utils.get_version_list()."""
        return mll_utils.get_version_list()

    def _parse_raw_list(self, raw: dict) -> list[VersionInfo]:
        """Convierte raw['versions'] (list[dict]) -> List[VersionInfo]."""
        ...

    def _filter_snapshots(self, versions: list[VersionInfo], include: bool) -> list[VersionInfo]: ...

    def clear_cache(self) -> None: ...
```

### Firmas detalladas de callbacks

```python
# minecraft_launcher_lib espera:
# install_minecraft_version(versionid, minecraft_directory, callback={...})
callback_dict: dict = {
    "setStatus": lambda text: status_callback(text),   # str
    "setProgress": lambda val: progress_callback(val), # int
    "setMax": lambda val: max_callback(val),           # int
}
# Nombres internos:
status_text: str
progress_value: int
max_value: int
```

---

## 4. Flujos

### Listar versiones
```
get_available_versions(force_refresh=False):
  if _cache valid and not force_refresh: return _cache
  raw: dict = _fetch_raw_list()           # -> {"latest":..., "versions": [...]}
  versions: list[VersionInfo] = _parse_raw_list(raw)
  installed_ids: set[str] = set(get_installed_versions())
  for v in versions: v.installed = v.id in installed_ids
  if not include_snapshots: versions = [v for v in versions if v.type==RELEASE]
  versions.sort(key=lambda v: v.release_time, reverse=True)
  _cache = versions; _cache_timestamp = now()
  return versions
```

### Instalar
```
install_version("1.20.1", callbacks):
  if is_installed("1.20.1"): return (o reinstala si se pide)
  info = get_version_info("1.20.1") -> si None: raise VersionNotFoundError
  # asegura dir
  self.minecraft_dir.mkdir(parents=True, exist_ok=True)
  # llama lib
  mll_install.install_minecraft_version(
      versionid="1.20.1",
      minecraft_directory=str(self.minecraft_dir),
      callback={"setStatus":..., "setProgress":..., "setMax":...}
  )
  # opcional: ensure Java via JavaManager
  clear_cache() # invalida installed
```

---

## 5. Errores

```python
class VersionError(Exception): ...
class VersionNotFoundError(VersionError): ...
class InstallError(VersionError): ...
class NetworkError(VersionError): ...
```

Mapear excepciones de `minecraft_launcher_lib.exceptions` a estas.

---

## 6. Conexión con `bridge/version_bridge.py`

- `VersionBridge` expone `@Slot(result=list)` `getVersions(includeSnapshots: bool)` → llama `service.get_available_versions()` y serializa `VersionInfo.to_dict()`
- `VersionBridge.installVersion(versionId: str)` → crea `QThread` + `Worker` que llama `service.install_version` con callbacks que emiten `progressChanged(int,int)` y `statusChanged(str)`
- Señales Qt: `progress(int current, int max)`, `statusChanged(str)`, `installFinished(str versionId)`, `installError(str msg)`

---

## 7. Tests sugeridos

- Mock `mll_utils.get_version_list` → `test_get_available_filters_snapshots`
- Mock `mll_install.install_minecraft_version` → `test_install_calls_lib_with_correct_dir`
- `test_cache_is_used_within_ttl`
- `test_parse_raw_list_handles_missing_releaseTime`

---

## 8. Variables resumen

| Variable | Tipo | Propósito |
|---|---|---|
| `minecraft_dir` | `Path` | Directorio `.minecraft` |
| `raw_version_list` | `dict` | Respuesta cruda de Mojang |
| `version_id` | `str` | Ej. "1.20.1" |
| `release_time` | `datetime` | Fecha de release |
| `_cache` | `list[VersionInfo]` | Caché en memoria |
| `current_progress` / `max_progress` | `int` | Para barra de progreso |
| `status_text` | `str` | Texto de estado |
