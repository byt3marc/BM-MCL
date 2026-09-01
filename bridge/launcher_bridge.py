from __future__ import annotations

from typing import final

from PySide6.QtCore import Property, QObject, QThread, Signal, Slot

from bridge.auth_bridge import AuthBridge
from bridge.settings_bridge import SettingsBridge
from core.launcher.java_manager import JavaManager, LauncherError
from core.launcher.service import LauncherService, LaunchOptions
from core.settings.models import Settings


@final
class _LaunchWorker(QObject):
    logLine = Signal(str)
    javaProgress = Signal(str)
    launched = Signal()
    exited = Signal(int)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, service: LauncherService, options: LaunchOptions) -> None:
        super().__init__()
        self._service = service
        self._options = options

    @Slot()
    def run(self) -> None:
        try:
            _ = self._service.launch(
                self._options,
                on_log=self.logLine.emit,
                on_exit=self.exited.emit,
                on_java_status=self.javaProgress.emit,
                on_started=self.launched.emit,
            )
        except LauncherError as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


@final
class LauncherBridge(QObject):
    logLine = Signal(str)
    launched = Signal()
    exited = Signal(int)
    launchError = Signal(str)
    javaProgress = Signal(str)
    runningChanged = Signal()

    def __init__(
        self,
        service: LauncherService,
        auth_bridge: AuthBridge,
        settings_bridge: SettingsBridge,
    ) -> None:
        super().__init__()
        self.service: LauncherService = service
        self.auth_bridge: AuthBridge = auth_bridge
        self.settings_bridge: SettingsBridge = settings_bridge
        self._thread: QThread | None = None
        self._running: bool = False

    @Property(bool, notify=runningChanged)
    def isRunning(self) -> bool:
        return self._running

    @Slot(str)
    def launch(self, version_id: str) -> None:
        if self._running:
            self.launchError.emit("Minecraft ya se está ejecutando o iniciando.")
            return
        options = self._build_options(version_id)
        if options is None:
            return
        self._running = True
        self.runningChanged.emit()
        worker = _LaunchWorker(self.service, options)
        thread = QThread(self)
        self._thread = thread
        _ = worker.moveToThread(thread)
        _ = thread.started.connect(worker.run)
        _ = worker.logLine.connect(self.logLine.emit)
        _ = worker.javaProgress.connect(self.javaProgress.emit)
        _ = worker.launched.connect(self.launched.emit)
        _ = worker.exited.connect(self.exited.emit)
        _ = worker.failed.connect(self.launchError.emit)
        _ = worker.finished.connect(thread.quit)
        _ = worker.finished.connect(worker.deleteLater)
        _ = thread.finished.connect(thread.deleteLater)
        _ = thread.finished.connect(self._finish_launch)
        thread.start()

    @Slot()
    def terminate(self) -> None:
        self.service.terminate()

    @Slot(result=list)
    def getLogs(self) -> list[str]:
        return self.service.get_logs()

    def _build_options(self, version_id: str) -> LaunchOptions | None:
        account = self.auth_bridge.get_selected_account()
        if account is None:
            self.launchError.emit("Debe seleccionarse una cuenta antes de iniciar Minecraft.")
            return None
        settings = self.settings_bridge.get_settings()
        self._sync_service_directory(settings)
        java_path = str(settings.java_path) if settings.java_path is not None else None
        return LaunchOptions(
            version_id=version_id,
            account=account,
            settings=settings,
            minecraft_dir=settings.install_dir,
            java_path=java_path,
        )

    def _sync_service_directory(self, settings: Settings) -> None:
        if self.service.minecraft_dir != settings.install_dir:
            self.service.minecraft_dir = settings.install_dir
            self.service.java_manager = JavaManager(settings.install_dir, settings.java_path)
            return
        self.service.java_manager.java_path = settings.java_path

    def _finish_launch(self) -> None:
        self._thread = None
        self._running = False
        self.runningChanged.emit()
