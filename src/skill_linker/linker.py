from __future__ import annotations

from pathlib import Path

from .scanner import LinkStatus, SkillEntry


def link(entry: SkillEntry) -> None:
    entry.target_path.parent.mkdir(parents=True, exist_ok=True)
    if entry.target_path.is_symlink():
        entry.target_path.unlink()
    entry.target_path.symlink_to(entry.source_path)


def unlink(entry: SkillEntry) -> None:
    if entry.status == LinkStatus.DIRECT:
        raise ValueError(f"{entry.name} is a real directory, not managed by skill-linker")
    if entry.target_path.is_symlink():
        entry.target_path.unlink()


def apply(to_link: list[SkillEntry], to_unlink: list[SkillEntry]) -> list[str]:
    errors: list[str] = []
    for entry in to_unlink:
        try:
            unlink(entry)
        except Exception as e:
            errors.append(f"unlink {entry.name}: {e}")
    for entry in to_link:
        try:
            link(entry)
        except Exception as e:
            errors.append(f"link {entry.name}: {e}")
    return errors
