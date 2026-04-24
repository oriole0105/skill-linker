# skill-linker

A terminal TUI tool for managing AI tool skills via symbolic links.

Different AI tools (Claude Code, OpenCode, RooCode, etc.) store skills in different paths. **skill-linker** lets you keep all your skills in one place and install them to any target by creating symlinks — no file duplication.

## Screenshot

```
┌─ Skill Linker ─ Target: ~/.claude/skills ──────────────────────────────┐
│ Sources            │ Skills                                              │
│                    │ Filter...                                           │
│   Personal Skills  │ ●  remotion-best-practices  Personal  ✓ linked    │
│   Company Skills   │ ○  sv-lint                  Personal  – unlinked  │
│                    │ ○  sv-write                 Personal  – unlinked  │
│                    │ ○  uvm-check                Personal  ✓ linked    │
│                    │                                                     │
├────────────────────────────────────────────────────────────────────────  │
│ Q 離開  T Target  R 重新整理  A 全選  N 全取消  F 過濾  D 描述          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-source**: aggregate skills from multiple directories, shown in one unified list
- **Multi-target**: switch between targets (Claude Code global, project-level, OpenCode, etc.) with `T`
- **Symlink-based install**: `Enter` to preview changes, `Y` to apply — no file copying
- **Status indicators**: instantly see which skills are linked, unlinked, broken, or unmanaged
- **Filter**: press `F` to search by name or source label
- **Skill description**: press `D` to read the skill's `SKILL.md` in a Markdown viewer

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone https://github.com/oriole0105/skill-linker.git
cd skill-linker
uv sync
```

## Usage

```bash
# Launch TUI (default target = first entry in config)
uv run skill-linker

# List all skills and their link status (no TUI)
uv run skill-linker list

# Use a specific target
uv run skill-linker --target "Claude Code (global)"
uv run skill-linker --target ~/.opencode/skills
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` `↓` | Move cursor |
| `Space` | Toggle selection |
| `A` | Select all |
| `N` | Deselect all |
| `Enter` | Apply (link / unlink) |
| `D` | View skill description |
| `F` | Filter |
| `T` | Switch target |
| `R` | Refresh |
| `Q` | Quit |

## Configuration

On first run, `~/.config/skill-linker/config.yaml` is created automatically:

```yaml
sources:
  - label: Personal Skills
    path: ~/.agents/skills

targets:
  - name: Claude Code (global)
    path: ~/.claude/skills
  - name: Current Directory
    path: ./.claude/skills
```

Add more sources or targets as needed. Paths support `~` and environment variable expansion.

## How it works

Selecting a skill marks it as "desired installed". Pressing `Enter` computes the diff:

- **Selected + not linked** → create symlink
- **Deselected + currently linked** → remove symlink
- **Selected + already linked** → no-op
- **Deselected + not linked** → no-op

Symlinks pointing to a real directory (not managed by skill-linker) are shown as `⊘ direct` and are never touched.

## Documentation

- [SPEC.md](SPEC.md) — full functional specification
- [USER_GUIDE.md](USER_GUIDE.md) — usage guide with examples
