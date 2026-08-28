# BML - 1.0 Refactor

Hola, en este proyecto voy a hacer un refactor, de mi antiguo proyecto / launcher de minecraft donde mejorare...
- UI & UX, para que se vea mejor visualmente
- Merar orden de las funciones ademas para que sean mas faciles de entender y reutilizar
- Mejorar el poder utilizar cuentas no premiun, premium, skins, etc.

Lenguajes:
- Python (PySide6, QML, minecraft)


Estructura del proyecto:
BML/
├── main.py                     # QGuiApplication + QQmlApplicationEngine + expone bridge
├── pyproject.toml              # dependencies: PySide6, minecraft-launcher-lib>=8.0
├── .gitignore                  # /data/, /__pycache__/
│
├── core/                       # Puro Python, sin Qt. Testeable. ÚNICO lugar que importa minecraft_launcher_lib
│   ├── __init__.py
│   ├── settings/
│   │   ├── models.py           # @dataclass Settings: install_dir, ram, java_path, show_snapshots
│   │   └── store.py            # load/save JSON en %APPDATA%/BML o ./data/ (decisión tuya)
│   ├── auth/
│   │   ├── models.py           # @dataclass Account (uuid, name, type: offline/microsoft)
│   │   ├── offline.py          # genera uuid offline
│   │   └── microsoft.py        # wrapper de mll.microsoft_account (+ offline fallback)
│   ├── versions/
│   │   ├── models.py           # Tu VersionInfo (id, type, releaseTime) - desacoplado de la lib
│   │   └── service.py          # ADAPTER: utils.get_version_list() -> List[VersionInfo], install.install_minecraft_version() con callback
│   ├── skins/
│   │   ├── manager.py
│   │   └── cache.py            # cache en data/skins/
│   └── launcher/
│       ├── java_manager.py     # mll.java_utils + mll.runtime (autoinstala Java si falta)
│       └── service.py          # ADAPTER: mll.command.get_minecraft_command() + QProcess/subprocess
│
├── bridge/                     # Única capa Qt. QObject + Signals/Slots + QThread
│   ├── __init__.py
│   ├── app_bridge.py           # Root: expone auth/version/settings como Q_PROPERTY a QML
│   ├── auth_bridge.py          # login/offline, signal accountChanged
│   ├── version_bridge.py       # getVersions(), installVersion(id), signals: progress, status, max
│   └── settings_bridge.py
│
├── ui/
│   ├── qml/
│   │   ├── main.qml            # ApplicationWindow + StackView
│   │   ├── pages/              # Home.qml, Library.qml, Login.qml, Settings.qml
│   │   ├── components/         # BMButton.qml, BMCard.qml, ProgressBar.qml
│   │   └── theme/              # Theme.qml, Colors.qml
│   └── assets/                 # icons/fonts
│
└── tests/
    ├── test_versions_service.py # mockea minecraft_launcher_lib
    └── test_settings_store.py
