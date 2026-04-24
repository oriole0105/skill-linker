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


def unexpand(path: Path) -> str:
    """Convert absolute path back to ~ notation where possible."""
    home = str(Path.home())
    s = str(path)
    if s.startswith(home + "/") or s == home:
        return "~" + s[len(home):]
    return s


def save(config: Config) -> None:
    data = {
        "sources": [{"label": s.label, "path": unexpand(s.path)} for s in config.sources],
        "targets": [{"name": t.name, "path": unexpand(t.path)} for t in config.targets],
    }
    CONFIG_PATH.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))


def load() -> Config:
    if not CONFIG_PATH.exists():
        _write_default()
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8", errors="replace"))
    return Config(
        sources=[SourceConfig(label=s["label"], path=_expand(s["path"])) for s in raw.get("sources", [])],
        targets=[TargetConfig(name=t["name"], path=_expand(t["path"])) for t in raw.get("targets", [])],
    )


def _write_default() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(DEFAULT_CONFIG, allow_unicode=True, default_flow_style=False))
