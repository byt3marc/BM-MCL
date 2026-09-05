from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from bridge.auth_bridge import AuthBridge
from bridge.launcher_bridge import LauncherBridge
from bridge.settings_bridge import SettingsBridge
from bridge.skin_bridge import SkinBridge
from bridge.version_bridge import VersionBridge
from core.auth.store import AuthStore
from core.launcher.service import LauncherService
from core.settings.store import SettingsStore
from core.skins.cache import SkinCache
from core.skins.manager import SkinManager
from core.versions.service import VersionService


def create_bridges() -> dict[str, QObject]:
    settings_store = SettingsStore()
    settings_bridge = SettingsBridge(settings_store)
    settings = settings_store.load()
    auth_bridge = AuthBridge(AuthStore(settings_store.data_dir))
    version_bridge = VersionBridge(VersionService(settings.install_dir))
    skin_bridge = SkinBridge(SkinManager(SkinCache(settings_store.data_dir)))
    launcher_bridge = LauncherBridge(
        LauncherService(settings.install_dir),
        auth_bridge,
        settings_bridge,
    )
    return {
        "authBridge": auth_bridge,
        "settingsBridge": settings_bridge,
        "versionBridge": version_bridge,
        "skinBridge": skin_bridge,
        "launcherBridge": launcher_bridge,
    }


def run() -> int:
    application = QGuiApplication(sys.argv)
    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(Path(__file__).resolve().parent / "ui" / "qml"))
    bridges = create_bridges()
    context = engine.rootContext()
    for name, bridge in bridges.items():
        bridge.setParent(engine)
        context.setContextProperty(name, bridge)
    qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return application.exec()


if __name__ == "__main__":
    sys.exit(run())
