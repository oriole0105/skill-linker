from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, TargetConfig, load


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skill-linker",
        description="Manage AI tool skills via symlinks",
    )
    parser.add_argument(
        "--target", "-t",
        help="Target name (from config) or direct path. Default: first target in config.",
        default=None,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "tui"],
        default="tui",
        help="Command to run (default: tui)",
    )
    args = parser.parse_args()

    config = load()

    if not config.sources:
        print("No sources configured. Edit ~/.config/skill-linker/config.yaml", file=sys.stderr)
        sys.exit(1)

    target = _resolve_target(args.target, config)

    if args.command == "list":
        _cmd_list(config, target)
    else:
        _cmd_tui(config, target)


def _resolve_target(spec: str | None, config: Config) -> TargetConfig:
    if spec is None:
        return config.targets[0] if config.targets else TargetConfig(name="Current Directory", path=Path("./.claude/skills"))
    # try name match
    for t in config.targets:
        if t.name.lower() == spec.lower():
            return t
    # treat as path
    p = Path(spec).expanduser()
    return TargetConfig(name=str(p), path=p)


def _cmd_list(config: Config, target: TargetConfig) -> None:
    from . import scanner as scanner_mod
    from .scanner import LinkStatus

    STATUS_ICON = {
        LinkStatus.LINKED: "✓",
        LinkStatus.UNLINKED: "–",
        LinkStatus.BROKEN: "✗",
        LinkStatus.DIRECT: "⊘",
    }

    entries = scanner_mod.scan(config, target)
    print(f"Target: {target.path}\n")
    for e in entries:
        icon = STATUS_ICON[e.status]
        print(f"  {icon}  {e.name:<30}  [{e.source.label}]  {e.status.value}")


def _cmd_tui(config: Config, target: TargetConfig) -> None:
    from .tui.app import SkillLinkerApp
    app = SkillLinkerApp(config=config, initial_target=target)
    app.run()
