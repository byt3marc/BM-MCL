from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


DATE_FMT = "%Y-%m-%dT%H:%M:%S+00:00"


class VersionType(StrEnum):
    RELEASE = "release"
    SNAPSHOT = "snapshot"
    OLD_BETA = "old_beta"
    OLD_ALPHA = "old_alpha"


@dataclass(frozen=True, slots=True)
class VersionInfo:
    id: str
    type: VersionType
    release_time: datetime
    time: datetime | None = None
    url: str | None = None
    installed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "release_time": self.release_time.isoformat(),
            "time": self.time.isoformat() if self.time else None,
            "url": self.url,
            "installed": self.installed,
        }

    @staticmethod
    def from_mojang_dict(data: dict[str, Any]) -> "VersionInfo":
        if not isinstance(data, dict):
            raise ValueError("Los datos de versión deben ser un objeto.")
        version_id = data.get("id")
        if not isinstance(version_id, str) or not version_id:
            raise ValueError("La versión no contiene un identificador válido.")
        raw_type = data.get("type", VersionType.RELEASE.value)
        try:
            version_type = VersionType(raw_type)
        except (TypeError, ValueError):
            version_type = VersionType.RELEASE
        release_time = _parse_datetime(data.get("releaseTime"))
        if release_time is None:
            release_time = datetime.min.replace(tzinfo=timezone.utc)
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


def _parse_datetime(value: Any, required: bool = True) -> datetime | None:
    if value is None:
        if required:
            return datetime.min.replace(tzinfo=timezone.utc)
        return None
    if not isinstance(value, str):
        if required:
            return datetime.min.replace(tzinfo=timezone.utc)
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        if required:
            return datetime.min.replace(tzinfo=timezone.utc)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
