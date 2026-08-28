# BML — 1.0 Refactor

Hey! In this project I'm doing a full refactor of my old Minecraft launcher.
The goal is to rebuild it with a cleaner codebase and a much nicer UI, while keeping everything that made the old one work.

## What I'm improving

- **UI & UX** — a modern, clean look built with QML, instead of the old clunky interface.
- **Code organization** — the old launcher was one big mess of functions; now everything is split into small, well-named modules that are easier to understand, test and reuse.
- **Accounts** — better support for offline (non-premium) accounts, Microsoft (premium) accounts, and skin management.

## Tech stack

- **Python** as the main language
- **PySide6 + QML** for the desktop UI
- **minecraft-launcher-lib** (`>= 8.0`) for versions, Java handling and launching

## Project structure

```text
BML/
├── main.py                     # QGuiApplication + QQmlApplicationEngine, exposes the bridge
├── pyproject.toml              # dependencies: PySide6, minecraft-launcher-lib>=8.0
├── .gitignore                  # /data/, /__pycache__/
│
├── core/                       # Pure Python, no Qt. Testable. THE ONLY place that imports minecraft_launcher_lib
│   ├── __init__.py
│   ├── settings/
│   │   ├── models.py           # @dataclass Settings: install_dir, ram, java_path, show_snapshots
│   │   └── store.py            # load/save JSON in %APPDATA%/BML or ./data/ (your call)
│   ├── auth/
│   │   ├── models.py           # @dataclass Account (uuid, name, type: offline/microsoft)
│   │   ├── offline.py          # offline UUID generation
│   │   └── microsoft.py        # wrapper over mll.microsoft_account (+ offline fallback)
│   ├── versions/
│   │   ├── models.py           # My own VersionInfo (id, type, releaseTime) — decoupled from the lib
│   │   └── service.py          # ADAPTER: utils.get_version_list() -> List[VersionInfo], 
│   │                          # install.install_minecraft_version() with progress callback
│   ├── skins/
│   │   ├── manager.py
│   │   └── cache.py            # skin cache in data/skins/
│   └── launcher/
│       ├── java_manager.py     # mll.java_utils + mll.runtime (auto-installs Java if missing)
│       └── service.py          # ADAPTER: mll.command.get_minecraft_command() + QProcess/subprocess
│
├── bridge/                     # The only Qt layer. QObject + Signals/Slots + QThread
│   ├── __init__.py
│   ├── app_bridge.py           # Root: exposes auth/version/settings as Q_PROPERTY to QML
│   ├── auth_bridge.py          # login/offline, accountChanged signal
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
    ├── test_versions_service.py # mocks minecraft_launcher_lib
    └── test_settings_store.py
```

## Status

Work in progress — the structure is in place and the launcher core is being refactored module by module.
