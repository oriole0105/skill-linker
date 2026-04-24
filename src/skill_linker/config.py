from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_PATH = Path.home() / ".config" / "skill-linker" / "config.yaml"

DEFAULT_CONFIG = {
    "sources": [
        {"label": "Personal Skills", "path": "~/.agents/skills"},
    ],
    "targets": [
        {"name": "Claude Code (global)", "path": "~/.claude/skills"},
        {"name": "Current Directory", "path": "./.claude/skills"},
    ],
}


@dataclass
class SourceConfig:
    label: str
    path: Path


@dataclass
class TargetConfig:
    name: str
    path: Path


@dataclass
class Config:
    sources: list[SourceConfig] = field(default_factory=list)
    targets: list[TargetConfig] = field(default_factory=list)


def _expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def load() -> Config:
    if not CONFIG_PATH.exists():
        _write_default()
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    return Config(
        sources=[SourceConfig(label=s["label"], path=_expand(s["path"])) for s in raw.get("sources", [])],
        targets=[TargetConfig(name=t["name"], path=_expand(t["path"])) for t in raw.get("targets", [])],
    )


def _write_default() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(DEFAULT_CONFIG, allow_unicode=True, default_flow_style=False))
