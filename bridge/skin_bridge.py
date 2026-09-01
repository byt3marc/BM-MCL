from __future__ import annotations

from pathlib import Path
from typing import final

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot

from core.skins.manager import (
    InvalidSkinError,
    SkinError,
    SkinManager,
    SkinNotFoundError,
)


@final
class _SkinFetchWorker(QObject):
    succeeded = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, manager: SkinManager, account_uuid: str, force_refresh: bool) -> None:
        super().__init__()
        self._manager = manager
        self._account_uuid = account_uuid
        self._force_refresh = force_refresh

    @Slot()
    def run(self) -> None:
        try:
            skin_path = self._manager.fetch_skin(self._account_uuid, self._force_refresh)
            if skin_path is None:
                raise SkinNotFoundError("No se encontró una skin para esta cuenta.")
            self.succeeded.emit(self._account_uuid, str(skin_path))
        except (SkinError, OSError, ValueError) as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


@final
class SkinBridge(QObject):
    skinReady = Signal(str, str)
    skinError = Signal(str)
    skinUpdated = Signal(str, str)

    def __init__(self, manager: SkinManager) -> None:
        super().__init__()
        self.manager: SkinManager = manager
        self._threads: set[QThread] = set()

    @Slot(str, result=str)
    def getSkinUrl(self, account_uuid: str) -> str:
        try:
            return self.manager.get_skin_url(account_uuid)
        except SkinError as error:
            self.skinError.emit(str(error))
            return ""

    @Slot(str, result=str)
    def getRenderUrl(self, account_uuid: str) -> str:
        try:
            return self.manager.get_render_url(account_uuid)
        except SkinError as error:
            self.skinError.emit(str(error))
            return ""

    @Slot(str, result=str)
    def getCachedPath(self, account_uuid: str) -> str:
        try:
            if self.manager.cache.is_cached(account_uuid):
                return str(self.manager.cache.get_skin_path(account_uuid))
            return str(self.manager.get_fallback_skin())
        except (SkinError, TypeError, ValueError) as error:
            self.skinError.emit(str(error))
            return ""

    @Slot(str)
    @Slot(str, bool)
    def fetchSkin(self, account_uuid: str, force_refresh: bool = False) -> None:
        worker = _SkinFetchWorker(self.manager, account_uuid, force_refresh)
        thread = QThread(self)
        _ = worker.moveToThread(thread)
        _ = thread.started.connect(worker.run)
        _ = worker.succeeded.connect(self._on_skin_ready)
        _ = worker.failed.connect(self.skinError.emit)
        _ = worker.finished.connect(thread.quit)
        _ = worker.finished.connect(worker.deleteLater)
        _ = thread.finished.connect(thread.deleteLater)
        _ = thread.finished.connect(lambda: self._threads.discard(thread))
        self._threads.add(thread)
        thread.start()

    @Slot(str, str, result=str)
    @Slot(str, str, str, result=str)
    def applyLocalSkin(
        self,
        account_uuid: str,
        skin_url: str,
        variant: str = "classic",
    ) -> str:
        try:
            skin_path = self.manager.apply_local_skin(
                account_uuid,
                self._local_path(skin_url),
                variant,
            )
        except (InvalidSkinError, SkinError, OSError, ValueError) as error:
            self.skinError.emit(str(error))
            return ""
        result = str(skin_path)
        self.skinUpdated.emit(account_uuid, result)
        self.skinReady.emit(account_uuid, result)
        return result

    @Slot(str, str, result=bool)
    def setVariant(self, account_uuid: str, variant: str) -> bool:
        try:
            self.manager.set_variant(account_uuid, variant)
        except (InvalidSkinError, SkinError) as error:
            self.skinError.emit(str(error))
            return False
        self.skinUpdated.emit(account_uuid, self.getCachedPath(account_uuid))
        return True

    @Slot(str, result=str)
    def getVariant(self, account_uuid: str) -> str:
        try:
            return self.manager.get_variant(account_uuid)
        except (SkinError, TypeError, ValueError) as error:
            self.skinError.emit(str(error))
            return "classic"

    @Slot(str, str)
    def _on_skin_ready(self, account_uuid: str, skin_path: str) -> None:
        self.skinReady.emit(account_uuid, skin_path)
        self.skinUpdated.emit(account_uuid, skin_path)

    @staticmethod
    def _local_path(value: str) -> Path:
        url = QUrl(value)
        if url.isLocalFile():
            return Path(url.toLocalFile())
        return Path(value)
