from __future__ import annotations

from typing import final

from PySide6.QtCore import Property, QObject, Signal, Slot

from core.settings.models import Settings
from core.settings.store import SettingsError, SettingsStore, SettingsValidationError


@final
class SettingsBridge(QObject):
    changed = Signal()
    settingsChanged = Signal(dict)
    settingsError = Signal(str)

    def __init__(self, store: SettingsStore) -> None:
        super().__init__()
        self.store: SettingsStore = store
        self._settings: Settings = self.store.load()

    @Property(dict, notify=changed)
    def settings(self) -> dict[str, object]:
        return self._settings.to_dict()

    def _get_install_dir(self) -> str:
        return str(self._settings.install_dir)

    def _set_install_dir(self, value: str) -> None:
        self._update_field("install_dir", value)

    installDir = Property(str, _get_install_dir, _set_install_dir, notify=changed)

    def _get_ram_min(self) -> int:
        return self._settings.ram_min_mb

    def _set_ram_min(self, value: int) -> None:
        self._update_field("ram_min_mb", value)

    ramMin = Property(int, _get_ram_min, _set_ram_min, notify=changed)

    def _get_ram_max(self) -> int:
        return self._settings.ram_max_mb

    def _set_ram_max(self, value: int) -> None:
        self._update_field("ram_max_mb", value)

    ramMax = Property(int, _get_ram_max, _set_ram_max, notify=changed)

    def _get_java_path(self) -> str:
        return str(self._settings.java_path) if self._settings.java_path else ""

    def _set_java_path(self, value: str) -> None:
        self._update_field("java_path", value or None)

    javaPath = Property(str, _get_java_path, _set_java_path, notify=changed)

    def _get_show_snapshots(self) -> bool:
        return self._settings.show_snapshots

    def _set_show_snapshots(self, value: bool) -> None:
        self._update_field("show_snapshots", value)

    showSnapshots = Property(bool, _get_show_snapshots, _set_show_snapshots, notify=changed)

    def _get_keep_launcher_open(self) -> bool:
        return self._settings.keep_launcher_open

    def _set_keep_launcher_open(self, value: bool) -> None:
        self._update_field("keep_launcher_open", value)

    keepLauncherOpen = Property(bool, _get_keep_launcher_open, _set_keep_launcher_open, notify=changed)

    def _get_window_width(self) -> int:
        return self._settings.window_width

    def _set_window_width(self, value: int) -> None:
        self._update_field("window_width", value)

    windowWidth = Property(int, _get_window_width, _set_window_width, notify=changed)

    def _get_window_height(self) -> int:
        return self._settings.window_height

    def _set_window_height(self, value: int) -> None:
        self._update_field("window_height", value)

    windowHeight = Property(int, _get_window_height, _set_window_height, notify=changed)

    def _get_selected_account_uuid(self) -> str:
        return self._settings.selected_account_uuid or ""

    def _set_selected_account_uuid(self, value: str) -> None:
        self._update_field("selected_account_uuid", value or None)

    selectedAccountUuid = Property(
        str,
        _get_selected_account_uuid,
        _set_selected_account_uuid,
        notify=changed,
    )

    def _get_theme(self) -> str:
        return self._settings.theme

    def _set_theme(self, value: str) -> None:
        self._update_field("theme", value)

    theme = Property(str, _get_theme, _set_theme, notify=changed)

    def _get_language(self) -> str:
        return self._settings.language

    def _set_language(self, value: str) -> None:
        self._update_field("language", value)

    language = Property(str, _get_language, _set_language, notify=changed)

    def _get_concurrent_downloads(self) -> int:
        return self._settings.concurrent_downloads

    def _set_concurrent_downloads(self, value: int) -> None:
        self._update_field("concurrent_downloads", value)

    concurrentDownloads = Property(
        int,
        _get_concurrent_downloads,
        _set_concurrent_downloads,
        notify=changed,
    )

    @Slot(result=dict)
    def load(self) -> dict[str, object]:
        try:
            self._settings = self.store.load()
        except SettingsError as error:
            self.settingsError.emit(str(error))
            return {}
        data = self._settings.to_dict()
        self.changed.emit()
        self.settingsChanged.emit(data)
        return data

    @Slot(dict, result=bool)
    def save(self, data: dict[str, object]) -> bool:
        try:
            settings = Settings.from_dict(data)
            self.store.save(settings)
        except (SettingsError, SettingsValidationError, ValueError, TypeError) as error:
            self.settingsError.emit(str(error))
            return False
        self._set_settings(settings)
        return True

    @Slot(dict, result=bool)
    def update(self, patch: dict[str, object]) -> bool:
        try:
            settings = self.store.update(patch)
        except (SettingsError, SettingsValidationError, TypeError, ValueError) as error:
            self.settingsError.emit(str(error))
            return False
        self._set_settings(settings)
        return True

    @Slot(result=dict)
    def resetToDefaults(self) -> dict[str, object]:
        try:
            settings = self.store.reset_to_defaults()
        except SettingsError as error:
            self.settingsError.emit(str(error))
            return {}
        self._set_settings(settings)
        return self._settings.to_dict()

    def get_settings(self) -> Settings:
        return self._settings

    def _update_field(self, field_name: str, value: object) -> None:
        _ = self.update({field_name: value})

    def _set_settings(self, settings: Settings) -> None:
        self._settings = settings
        data = self._settings.to_dict()
        self.changed.emit()
        self.settingsChanged.emit(data)
