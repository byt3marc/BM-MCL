from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict, TypeGuard, cast

DATE_FMT = "%Y-%m-%dT%H:%M:%S+00:00"


class VersionType(StrEnum):
    RELEASE = "release"
    SNAPSHOT = "snapshot"
    OLD_BETA = "old_beta"
    OLD_ALPHA = "old_alpha"


class VersionInfoData(TypedDict):
    id: str
    type: str
    release_time: str
    time: str | None
    url: str | None
    installed: bool


@dataclass(frozen=True, slots=True)
class VersionInfo:
    id: str
    type: VersionType
    release_time: datetime
    time: datetime | None = None
    url: str | None = None
    installed: bool = False

    def to_dict(self) -> VersionInfoData:
        return {
            "id": self.id,
            "type": self.type.value,
            "release_time": self.release_time.isoformat(),
            "time": self.time.isoformat() if self.time else None,
            "url": self.url,
            "installed": self.installed,
        }

    @staticmethod
    def from_mojang_dict(data: object) -> VersionInfo:
        if not _is_string_keyed_dict(data):
            raise TypeError("Los datos de versión deben ser un objeto válido.")
        version_id = data.get("id")
        if not isinstance(version_id, str) or not version_id:
            raise ValueError("La versión no contiene un identificador válido.")
        raw_type = data.get("type", VersionType.RELEASE.value)
        try:
            version_type = VersionType(raw_type) if isinstance(raw_type, str) else VersionType.RELEASE
        except ValueError:
            version_type = VersionType.RELEASE
        release_time = _parse_datetime(data.get("releaseTime"))
        if release_time is None:
            release_time = datetime.min.replace(tzinfo=UTC)
        updated_time = _parse_datetime(data.get("time"), required=False)
        url = data.get("url")
        if url is not None and not isinstance(url, str):
            url = None
        return VersionInfo(
            id=version_id,
            type=version_type,
            release_time=release_time,
            time=updated_time,
            url=url,
        )


@dataclass(frozen=True, slots=True)
class InstallProgress:
    current: int
    total: int
    status: str

    def to_dict(self) -> dict[str, int | str]:
        return {"current": self.current, "total": self.total, "status": self.status}


@dataclass(frozen=True, slots=True)
class InstalledVersion:
    id: str
    path: str
    last_played: datetime | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "path": self.path,
            "last_played": self.last_played.isoformat() if self.last_played else None,
        }


def _parse_datetime(value: object, required: bool = True) -> datetime | None:
    if value is None or not isinstance(value, str):
        return datetime.min.replace(tzinfo=UTC) if required else None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC) if required else None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _is_string_keyed_dict(value: object) -> TypeGuard[dict[str, object]]:
    if not isinstance(value, dict):
        return False
    dictionary = cast(dict[object, object], value)
    return all(isinstance(key, str) for key in dictionary)
