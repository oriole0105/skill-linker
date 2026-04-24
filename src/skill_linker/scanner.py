from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .config import Config, SourceConfig, TargetConfig


class LinkStatus(Enum):
    LINKED = "linked"
    UNLINKED = "unlinked"
    BROKEN = "broken"
    DIRECT = "direct"  # exists but not a symlink — not managed


@dataclass
class SkillEntry:
    name: str
    source: SourceConfig
    source_path: Path
    status: LinkStatus
    target_path: Path  # where the symlink would/does live


def _is_skill_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(path.iterdir())


def scan(config: Config, target: TargetConfig) -> list[SkillEntry]:
    entries: list[SkillEntry] = []
    seen: set[str] = set()

    for source in config.sources:
        if not source.path.exists():
            continue
        for child in sorted(source.path.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            name = child.name
            if name in seen:
                continue
            seen.add(name)

            target_link = target.path / name
            status = _get_status(target_link, child)
            entries.append(SkillEntry(
                name=name,
                source=source,
                source_path=child,
                status=status,
                target_path=target_link,
            ))

    return entries


def _get_status(link: Path, source: Path) -> LinkStatus:
    if not link.exists() and not link.is_symlink():
        return LinkStatus.UNLINKED
    if link.is_symlink():
        resolved = link.resolve()
        if resolved == source.resolve():
            return LinkStatus.LINKED
        return LinkStatus.BROKEN
    # exists but not symlink
    return LinkStatus.DIRECT
