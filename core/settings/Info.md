# settings — Diseño del módulo

> **Objetivo:** Persistir preferencias del launcher en JSON. Resolver ruta de datos (`%APPDATA%/BML` en prod, `./data/` en dev), validar y migrar settings. Sin Qt.

---

## 1. Archivos y responsabilidad

| Archivo | Rol |
|---|---|
| `core/settings/models.py` | `Settings` dataclass + defaults + validación. |
| `core/settings/store.py` | `SettingsStore` — load/save JSON, resolución de directorios, migración. |

**Sin dependencias externas.** Solo `json`, `pathlib`, `dataclasses`, `os`, `platform`.

---

## 2. Modelos — `models.py`

```python
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

@dataclass(slots=True)
class Settings:
    # Directorios
    install_dir: Path = field(default_factory=lambda: Path.home() / ".minecraft_bml")  # o resuelto por store
    # Performance
    ram_min_mb: int = 1024
    ram_max_mb: int = 4096
    # Java
    java_path: Optional[Path] = None  # None = auto-detect
    # UI / Filtros
    show_snapshots: bool = False
    keep_launcher_open: bool = True
    # Ventana
    window_width: int = 1280
    window_height: int = 720
    # Cuenta
    selected_account_uuid: Optional[str] = None
    # Misc
    theme: str = "dark"  # "dark" | "light"
    language: str = "es"
    concurrent_downloads: int = 4

    # --- Validación ---
    def validate(self) -> list[str]:
        """Retorna lista de errores. Vacía si OK."""
        errors: list[str] = []
        if self.ram_min_mb < 512: errors.append("ram_min_mb < 512")
        if self.ram_max_mb < self.ram_min_mb: errors.append("ram_max > ram_min required")
        if self.ram_max_mb > 32768: errors.append("ram_max unrealistic")
        if self.install_dir == Path(""): errors.append("install_dir empty")
        return errors

    def clamp_ram(self) -> None: ...

    def to_dict(self) -> dict:
        """Serializa Paths a str."""
        d: dict = asdict(self)
        d["install_dir"] = str(self.install_dir)
        d["java_path"] = str(self.java_path) if self.java_path else None
        return d

    @staticmethod
    def from_dict(data: dict) -> "Settings": ...

    @staticmethod
    def defaults(data_dir: Path | None = None) -> "Settings": ...
```

**Constantes:**
- `DEFAULT_RAM_MIN: int = 1024`
- `DEFAULT_RAM_MAX: int = 4096`
- `MIN_RAM_MB: int = 512`
- `MAX_RAM_MB: int = 32768`
- `DEFAULT_THEME: str = "dark"`
- `SUPPORTED_THEMES: set[str] = {"dark", "light"}`

---

## 3. `store.py` — Clase principal

```python
from pathlib import Path
import json, os, platform
from .models import Settings

APP_NAME: str = "BML"
SETTINGS_FILE: str = "settings.json"
DATA_DIR_ENV: str = "BML_DATA_DIR"  # override para tests/dev

class SettingsStore:
    def __init__(self, data_dir: Path | None = None):
        # Si data_dir None -> resuelve automáticamente
        self.data_dir: Path = data_dir or self.resolve_data_dir()
        self.settings_path: Path = self.data_dir / SETTINGS_FILE
        self._cached_settings: Settings | None = None

    # ---------- Resolución de rutas ----------
    @staticmethod
    def resolve_data_dir() -> Path:
        """%APPDATA%/BML en Windows, ~/.config/BML en Linux, ./data si BML_DATA_DIR=./data.
           Prioridad: env BML_DATA_DIR > APPDATA > HOME/.config > ./data"""
        env_override: str | None = os.getenv(DATA_DIR_ENV)
        if env_override: return Path(env_override)
        system: str = platform.system()
        if system == "Windows":
            base: Path = Path(os.getenv("APPDATA", Path.home()))
            return base / APP_NAME
        elif system == "Darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        else:
            return Path.home() / ".config" / APP_NAME

    def ensure_data_dir(self) -> None:
        """mkdir(parents=True, exist_ok=True)"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_minecraft_dir(self) -> Path:
        """Retorna settings.install_dir (resuelve ~ y variables)."""
        ...

    # ---------- Load / Save ----------
    def load(self) -> Settings:
        """Lee JSON. Si no existe -> defaults(). Si corrupto -> backup + defaults.
           Cachea en _cached_settings."""
        ...

    def save(self, settings: Settings) -> None:
        """Valida -> to_dict() -> json.dump(indent=2). Actualiza caché.
           Lanza SettingsValidationError si validate() falla."""
        ...

    def update(self, patch: dict) -> Settings:
        """Merge parcial: load() -> aplica patch -> save() -> retorna nuevo."""
        ...

    def reset_to_defaults(self) -> Settings: ...

    # ---------- Migración ----------
    def _migrate(self, raw: dict) -> dict:
        """Maneja cambios de schema. Ej: v1 sin 'theme' -> añade default.
           Usa raw.get('__version__', 1)."""
        ...

    def _backup_corrupt_file(self) -> None:
        """Renombra settings.json -> settings.json.bak.<timestamp>"""
        ...

    # Helpers privados
    def _read_json(self) -> dict: ...
    def _write_json(self, data: dict) -> None: ...
```

**Flujo `load()`:**
```
load():
  if _cached_settings and file mtime no cambió: return _cached_settings
  if not settings_path.exists(): 
      s = Settings.defaults(data_dir)
      save(s)  # crea archivo
      return s
  try: raw = json.loads(settings_path.read_text(encoding="utf-8"))
  except JSONDecodeError: _backup_corrupt_file(); return defaults()
  raw = _migrate(raw)
  settings = Settings.from_dict(raw)
  errors = settings.validate()
  if errors: # log warning, clamp
      settings.clamp_ram()
  _cached_settings = settings
  return settings
```

**Flujo `save()`:**
```
save(settings):
  errors = settings.validate()
  if errors: raise SettingsValidationError(errors)
  ensure_data_dir()
  data: dict = settings.to_dict()
  data["__version__"] = 1
  tmp_path = settings_path.with_suffix(".tmp")
  tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
  tmp_path.replace(settings_path)  # atómico
  _cached_settings = settings
```

---

## 4. Errores

```python
class SettingsError(Exception): ...
class SettingsValidationError(SettingsError): ...
class SettingsCorruptError(SettingsError): ...
```

---

## 5. Conexión con `bridge/settings_bridge.py`

- Expone `Q_PROPERTY` para cada campo: `ramMax`, `showSnapshots`, `installDir`, etc.
- `SettingsBridge.load()` → `store.load().to_dict()` → QML
- `SettingsBridge.save(dict)` → `Settings.from_dict(dict)` → `store.save()`
- Señal `settingsChanged(dict)` al guardar.
- En QML: `Slider` bindeado a `settingsBridge.ramMax`, `Switch` a `showSnapshots`.

---

## 6. Tests sugeridos

- `test_resolve_data_dir_uses_env_override` (monkeypatch `BML_DATA_DIR`)
- `test_load_creates_defaults_if_missing` (tmp_path)
- `test_save_and_load_roundtrip_preserves_paths`
- `test_load_handles_corrupt_json_with_backup`
- `test_validate_rejects_ram_min_gt_max`
- `test_update_merges_partial_dict`

---

## 7. Variables resumen

| Variable | Tipo | Propósito |
|---|---|---|
| `data_dir` | `Path` | `%APPDATA%/BML` o `./data` |
| `settings_path` | `Path` | `data_dir/settings.json` |
| `raw_data` | `dict` | JSON crudo |
| `_cached_settings` | `Settings\|None` | Caché en memoria |
| `patch` | `dict` | Update parcial |
| `ram_min_mb` / `ram_max_mb` | `int` | Memoria JVM |
| `java_path` | `Path\|None` | Override de Java |
| `selected_account_uuid` | `str\|None` | Cuenta activa |
