from __future__ import annotations

from typing import final

from PySide6.QtCore import Property, QObject, QThread, Signal, Slot

from core.versions.models import VersionInfoData
from core.versions.service import InstallCallbacks, VersionError, VersionService


@final
class _VersionInstallWorker(QObject):
    progress = Signal(int, int)
    statusChanged = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, service: VersionService, version_id: str) -> None:
        super().__init__()
        self._service = service
        self._version_id = version_id
        self._maximum = 0

    @Slot()
    def run(self) -> None:
        callbacks: InstallCallbacks = {
            "setStatus": self.statusChanged.emit,
            "setProgress": self._set_progress,
            "setMax": self._set_maximum,
        }
        try:
            self._service.install_version(self._version_id, callbacks=callbacks)
            self.succeeded.emit(self._version_id)
        except VersionError as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    def _set_progress(self, current: int) -> None:
        self.progress.emit(current, self._maximum)

    def _set_maximum(self, maximum: int) -> None:
        self._maximum = maximum
        self.progress.emit(0, maximum)


@final
class VersionBridge(QObject):
    versionsChanged = Signal(list)
    progress = Signal(int, int)
    statusChanged = Signal(str)
    installFinished = Signal(str)
    installError = Signal(str)
    installingChanged = Signal()

    def __init__(self, service: VersionService) -> None:
        super().__init__()
        self.service: VersionService = service
        self._threads: set[QThread] = set()
        self._installing: bool = False

    @Property(bool, notify=installingChanged)
    def isInstalling(self) -> bool:
        return self._installing

    @Slot(bool, result=list)
    def getVersions(self, include_snapshots: bool) -> list[VersionInfoData]:
        try:
            versions = self.service.get_available_versions(include_snapshots=include_snapshots)
        except VersionError as error:
            self.installError.emit(str(error))
            return []
        serialized = [version.to_dict() for version in versions]
        self.versionsChanged.emit(serialized)
        return serialized

    @Slot(result=list)
    def getInstalledVersions(self) -> list[str]:
        try:
            return self.service.get_installed_versions()
        except VersionError as error:
            self.installError.emit(str(error))
            return []

    @Slot(str, result=bool)
    def isInstalled(self, version_id: str) -> bool:
        try:
            return self.service.is_installed(version_id)
        except VersionError as error:
            self.installError.emit(str(error))
            return False

    @Slot(str)
    def installVersion(self, version_id: str) -> None:
        if self._installing:
            self.installError.emit("Ya hay una instalación de versión en curso.")
            return
        self._installing = True
        self.installingChanged.emit()
        worker = _VersionInstallWorker(self.service, version_id)
        thread = QThread(self)
        _ = worker.moveToThread(thread)
        _ = thread.started.connect(worker.run)
        _ = worker.progress.connect(self.progress.emit)
        _ = worker.statusChanged.connect(self.statusChanged.emit)
        _ = worker.succeeded.connect(self._on_install_finished)
        _ = worker.failed.connect(self.installError.emit)
        _ = worker.finished.connect(thread.quit)
        _ = worker.finished.connect(worker.deleteLater)
        _ = thread.finished.connect(thread.deleteLater)
        _ = thread.finished.connect(lambda: self._finish_install(thread))
        self._threads.add(thread)
        thread.start()

    @Slot()
    def clearCache(self) -> None:
        self.service.clear_cache()

    @Slot(str)
    def _on_install_finished(self, version_id: str) -> None:
        self.installFinished.emit(version_id)
        _ = self.getVersions(False)

    def _finish_install(self, thread: QThread) -> None:
        self._threads.discard(thread)
        self._installing = False
        self.installingChanged.emit()
