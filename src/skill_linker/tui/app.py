from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual import events
from textual.app import App, ComposeResult, on
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
)

from .. import linker as linker_mod
from .. import scanner as scanner_mod
from ..config import Config, TargetConfig
from ..scanner import LinkStatus, SkillEntry

class SkillTable(DataTable):
    """DataTable that intercepts Enter/Space so the app handles them."""

    def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", "space"):
            event.prevent_default()
            event.stop()
            app: SkillLinkerApp = self.app  # type: ignore[assignment]
            if event.key == "enter":
                app.action_apply()
            else:
                app.action_toggle_skill()


class FilterInput(Input):
    """Filter input that passes up/down/escape to the DataTable."""

    def on_key(self, event: events.Key) -> None:
        table = self.app.query_one("#skill-table", DataTable)
        if event.key in ("up", "down"):
            event.prevent_default()
            table.focus()
            if event.key == "up":
                table.action_cursor_up()
            else:
                table.action_cursor_down()
        elif event.key == "escape":
            event.prevent_default()
            self.clear()
            table.focus()


STATUS_ICON = {
    LinkStatus.LINKED: "✓",
    LinkStatus.UNLINKED: "–",
    LinkStatus.BROKEN: "✗",
    LinkStatus.DIRECT: "⊘",
}

STATUS_LABEL = {
    LinkStatus.LINKED: "linked",
    LinkStatus.UNLINKED: "unlinked",
    LinkStatus.BROKEN: "broken",
    LinkStatus.DIRECT: "direct (unmanaged)",
}


def _read_skill_md(entry: SkillEntry) -> str:
    skill_md = entry.source_path / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text()
    # fallback: find any .md file
    for f in entry.source_path.glob("*.md"):
        return f.read_text()
    return "_（此 skill 沒有描述文件）_"


class SkillDetailScreen(ModalScreen[None]):
    DEFAULT_CSS = """
    SkillDetailScreen { align: center middle; }
    #detail-dialog {
        width: 80;
        height: 80%;
        max-height: 40;
        background: $surface;
        border: solid $primary;
        padding: 0 2;
    }
    #detail-title {
        text-style: bold;
        color: $primary;
        padding: 1 0 0 0;
    }
    #detail-source {
        color: $text-muted;
        margin-bottom: 1;
    }
    #detail-content {
        height: 1fr;
        overflow-y: auto;
        border-top: solid $primary-darken-2;
        padding: 1 0;
    }
    #detail-close {
        margin-top: 1;
        margin-bottom: 1;
    }
    """
    BINDINGS = [Binding("escape,q", "dismiss", "關閉")]

    def __init__(self, entry: SkillEntry) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        content = _read_skill_md(self.entry)
        with Vertical(id="detail-dialog"):
            yield Label(self.entry.name, id="detail-title")
            yield Label(f"Source: {self.entry.source.label}  ({self.entry.source_path})", id="detail-source")
            with Vertical(id="detail-content"):
                yield Markdown(content)
            yield Button("關閉  [Esc]", id="detail-close")

    @on(Button.Pressed, "#detail-close")
    def close(self) -> None:
        self.dismiss()


class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    #confirm-dialog { width: 60; height: auto; background: $surface; border: solid $primary; padding: 1 2; }
    #confirm-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #confirm-hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("y", "confirm", "確認 (Y)"),
        Binding("escape,n", "cancel", "取消 (Esc/N)"),
    ]

    def __init__(self, to_link: list[SkillEntry], to_unlink: list[SkillEntry], target: TargetConfig):
        super().__init__()
        self.to_link = to_link
        self.to_unlink = to_unlink
        self.target = target

    def compose(self) -> ComposeResult:
        link_names = ", ".join(e.name for e in self.to_link) or "(無)"
        unlink_names = ", ".join(e.name for e in self.to_unlink) or "(無)"
        with Vertical(id="confirm-dialog"):
            yield Label("確認操作", id="confirm-title")
            yield Label(f"Link   ({len(self.to_link)}):  {link_names}")
            yield Label(f"Unlink ({len(self.to_unlink)}):  {unlink_names}")
            yield Label("")
            yield Label(f"Target: {self.target.path}")
            yield Label("按 Y 確認，Esc / N 取消", id="confirm-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class TargetScreen(ModalScreen[TargetConfig | None]):
    DEFAULT_CSS = """
    TargetScreen { align: center middle; }
    #target-dialog { width: 50; height: auto; background: $surface; border: solid $primary; padding: 1 2; }
    #target-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #target-hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "取消")]

    def __init__(self, config: Config, current: TargetConfig):
        super().__init__()
        self.config = config
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="target-dialog"):
            yield Label("選擇 Target", id="target-title")
            with ListView(id="target-list"):
                for i, t in enumerate(self.config.targets):
                    marker = "●" if t.name == self.current.name else "○"
                    yield ListItem(Label(f"{marker}  {t.name}  —  {t.path}"), id=f"target-{i}")
            yield Label("↑↓ 移動  Enter 確認  Esc 取消", id="target-hint")

    def on_mount(self) -> None:
        current_idx = next(
            (i for i, t in enumerate(self.config.targets) if t.name == self.current.name), 0
        )
        self.query_one("#target-list", ListView).index = current_idx

    @on(ListView.Selected, "#target-list")
    def on_selected(self, event: ListView.Selected) -> None:
        idx = int(event.item.id.removeprefix("target-"))
        self.dismiss(self.config.targets[idx])

    def action_cancel(self) -> None:
        self.dismiss(None)


class SkillLinkerApp(App):
    TITLE = "Skill Linker"
    CSS_PATH = Path(__file__).parent / "style.tcss"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "離開"),
        Binding("t", "switch_target", "切換 Target"),
        Binding("r", "refresh", "重新整理"),
        Binding("a", "select_all", "全選"),
        Binding("n", "deselect_all", "全取消"),
        Binding("f", "focus_filter", "過濾"),
        Binding("d", "show_detail", "描述"),
    ]

    def __init__(self, config: Config, initial_target: TargetConfig):
        super().__init__()
        self.config = config
        self.current_target = initial_target
        self.entries: list[SkillEntry] = []
        self.selected: set[str] = set()
        self.filter_text: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main-container"):
            with Vertical(id="source-panel"):
                yield Label("Sources", id="source-panel-title")
                for src in self.config.sources:
                    yield Label(f"  {src.label}", classes="source-item")
            with Vertical(id="skill-panel"):
                yield Label("Skills", id="skill-panel-title")
                yield FilterInput(placeholder="Filter... (F 進入，Esc 離開)", id="filter-input")
                yield SkillTable(id="skill-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._setup_table()
        self._refresh_data()

    def _setup_table(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        table.add_column("", key="check")
        table.add_column("Name", key="name")
        table.add_column("Source", key="source")
        table.add_column("Status", key="status")

    def _refresh_data(self) -> None:
        self.entries = scanner_mod.scan(self.config, self.current_target)
        self._rebuild_table()
        self.sub_title = f"Target: {self.current_target.path}"

    def _filtered(self) -> list[SkillEntry]:
        if not self.filter_text:
            return self.entries
        low = self.filter_text.lower()
        return [e for e in self.entries if low in e.name.lower() or low in e.source.label.lower()]

    def _rebuild_table(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        saved_row = table.cursor_row
        table.clear()
        for entry in self._filtered():
            check = "●" if entry.name in self.selected else "○"
            icon = STATUS_ICON[entry.status]
            label = STATUS_LABEL[entry.status]
            table.add_row(check, entry.name, entry.source.label, f"{icon} {label}", key=entry.name)
        count = table.row_count
        if count > 0:
            table.move_cursor(row=min(saved_row, count - 1))

    def _status_line(self) -> str:
        linked = sum(1 for e in self.entries if e.status == LinkStatus.LINKED)
        total = len(self.entries)
        sel = len(self.selected)
        to_link = sum(1 for e in self.entries if e.name in self.selected and e.status != LinkStatus.LINKED)
        to_unlink = sum(1 for e in self.entries if e.name not in self.selected and e.status == LinkStatus.LINKED)
        return f"已連結: {linked}/{total}  已選: {sel}  將 link: {to_link}  將 unlink: {to_unlink}"

    def _current_entry(self) -> SkillEntry | None:
        table = self.query_one("#skill-table", DataTable)
        row = table.cursor_row
        filtered = self._filtered()
        if 0 <= row < len(filtered):
            return filtered[row]
        return None

    def action_show_detail(self) -> None:
        entry = self._current_entry()
        if entry:
            self.push_screen(SkillDetailScreen(entry))

    def action_toggle_skill(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        row_idx = table.cursor_row
        filtered = self._filtered()
        if row_idx < 0 or row_idx >= len(filtered):
            return
        entry = filtered[row_idx]
        if entry.name in self.selected:
            self.selected.discard(entry.name)
            table.update_cell(entry.name, "check", "○")
        else:
            self.selected.add(entry.name)
            table.update_cell(entry.name, "check", "●")

    def action_select_all(self) -> None:
        self.selected = {e.name for e in self._filtered()}
        self._rebuild_table()

    def action_deselect_all(self) -> None:
        self.selected.clear()
        self._rebuild_table()

    def action_refresh(self) -> None:
        self._refresh_data()
        self.notify("已重新整理")

    def action_switch_target(self) -> None:
        def handle(result: TargetConfig | None) -> None:
            if result:
                self.current_target = result
                self.selected.clear()
                self._refresh_data()

        self.push_screen(TargetScreen(self.config, self.current_target), handle)

    def action_focus_filter(self) -> None:
        self.query_one("#filter-input", Input).focus()

    @on(Input.Changed, "#filter-input")
    def on_filter_change(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self._rebuild_table()

    @on(Input.Submitted, "#filter-input")
    def on_filter_submit(self, _: Input.Submitted) -> None:
        self.query_one("#skill-table", DataTable).focus()


    def action_apply(self) -> None:
        to_link = [e for e in self.entries if e.name in self.selected and e.status != LinkStatus.LINKED and e.status != LinkStatus.DIRECT]
        to_unlink = [e for e in self.entries if e.name not in self.selected and e.status == LinkStatus.LINKED]

        if not to_link and not to_unlink:
            self.notify("沒有變更", severity="information")
            return

        def handle(confirmed: bool) -> None:
            if not confirmed:
                return
            errors = linker_mod.apply(to_link, to_unlink)
            if errors:
                self.notify("\n".join(errors), severity="error", timeout=8)
            else:
                self.notify(f"完成：link {len(to_link)} 個，unlink {len(to_unlink)} 個", severity="information")
            self._refresh_data()

        self.push_screen(ConfirmScreen(to_link, to_unlink, self.current_target), handle)
