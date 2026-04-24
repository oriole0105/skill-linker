from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import ClassVar

# PyInstaller frozen builds extract files to sys._MEIPASS
_CSS_PATH = (
    Path(sys._MEIPASS) / "skill_linker" / "tui" / "style.tcss"
    if hasattr(sys, "_MEIPASS")
    else Path(__file__).parent / "style.tcss"
)

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

from .. import config as config_mod
from .. import linker as linker_mod
from .. import scanner as scanner_mod
from ..config import Config, SourceConfig, TargetConfig
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
    target = skill_md if skill_md.exists() else next(entry.source_path.glob("*.md"), None)
    if target is None:
        return "_（此 skill 沒有描述文件）_"
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Unknown encoding — latin-1 maps every byte 0x00–0xff, never raises
        return target.read_text(encoding="latin-1")


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


class DeleteConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    DeleteConfirmScreen { align: center middle; }
    #del-dialog { width: 50; height: auto; background: $surface; border: solid $error; padding: 1 2; }
    #del-title { text-style: bold; color: $error; margin-bottom: 1; }
    #del-hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("y", "confirm", "確認 (Y)"),
        Binding("escape,n", "cancel", "取消 (Esc/N)"),
    ]

    def __init__(self, item_name: str) -> None:
        super().__init__()
        self.item_name = item_name

    def compose(self) -> ComposeResult:
        with Vertical(id="del-dialog"):
            yield Label("確認刪除", id="del-title")
            yield Label(f"將刪除：{self.item_name}")
            yield Label("按 Y 確認，Esc / N 取消", id="del-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class SourceFormScreen(ModalScreen["SourceConfig | None"]):
    DEFAULT_CSS = """
    SourceFormScreen { align: center middle; }
    #src-form { width: 60; height: auto; background: $surface; border: solid $primary; padding: 1 2; }
    #src-form-title { text-style: bold; color: $primary; margin-bottom: 1; }
    .form-field-label { color: $text-muted; margin-top: 1; }
    #src-form-hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "取消")]

    def __init__(self, source: SourceConfig | None = None) -> None:
        super().__init__()
        self._source = source

    def compose(self) -> ComposeResult:
        label_val = self._source.label if self._source else ""
        path_val = config_mod.unexpand(self._source.path) if self._source else ""
        title = "編輯 Source" if self._source else "新增 Source"
        with Vertical(id="src-form"):
            yield Label(title, id="src-form-title")
            yield Label("Label：", classes="form-field-label")
            yield Input(value=label_val, placeholder="Personal Skills", id="src-input-label")
            yield Label("Path：", classes="form-field-label")
            yield Input(value=path_val, placeholder="~/.agents/skills", id="src-input-path")
            yield Label("Enter 確認  Esc 取消", id="src-form-hint")

    def on_mount(self) -> None:
        self.query_one("#src-input-label", Input).focus()

    @on(Input.Submitted, "#src-input-label")
    def _label_submitted(self, _: Input.Submitted) -> None:
        self.query_one("#src-input-path", Input).focus()

    @on(Input.Submitted, "#src-input-path")
    def _path_submitted(self, _: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        label = self.query_one("#src-input-label", Input).value.strip()
        path_str = self.query_one("#src-input-path", Input).value.strip()
        if not label or not path_str:
            self.notify("Label 與 Path 不能為空", severity="error")
            return
        path = Path(os.path.expandvars(os.path.expanduser(path_str)))
        self.dismiss(SourceConfig(label=label, path=path))

    def action_cancel(self) -> None:
        self.dismiss(None)


class TargetFormScreen(ModalScreen["TargetConfig | None"]):
    DEFAULT_CSS = """
    TargetFormScreen { align: center middle; }
    #tgt-form { width: 60; height: auto; background: $surface; border: solid $primary; padding: 1 2; }
    #tgt-form-title { text-style: bold; color: $primary; margin-bottom: 1; }
    .form-field-label { color: $text-muted; margin-top: 1; }
    #tgt-form-hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "取消")]

    def __init__(self, target: TargetConfig | None = None) -> None:
        super().__init__()
        self._target = target

    def compose(self) -> ComposeResult:
        name_val = self._target.name if self._target else ""
        path_val = config_mod.unexpand(self._target.path) if self._target else ""
        title = "編輯 Target" if self._target else "新增 Target"
        with Vertical(id="tgt-form"):
            yield Label(title, id="tgt-form-title")
            yield Label("Name：", classes="form-field-label")
            yield Input(value=name_val, placeholder="Claude Code (global)", id="tgt-input-name")
            yield Label("Path：", classes="form-field-label")
            yield Input(value=path_val, placeholder="~/.claude/skills", id="tgt-input-path")
            yield Label("Enter 確認  Esc 取消", id="tgt-form-hint")

    def on_mount(self) -> None:
        self.query_one("#tgt-input-name", Input).focus()

    @on(Input.Submitted, "#tgt-input-name")
    def _name_submitted(self, _: Input.Submitted) -> None:
        self.query_one("#tgt-input-path", Input).focus()

    @on(Input.Submitted, "#tgt-input-path")
    def _path_submitted(self, _: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        name = self.query_one("#tgt-input-name", Input).value.strip()
        path_str = self.query_one("#tgt-input-path", Input).value.strip()
        if not name or not path_str:
            self.notify("Name 與 Path 不能為空", severity="error")
            return
        path = Path(os.path.expandvars(os.path.expanduser(path_str)))
        self.dismiss(TargetConfig(name=name, path=path))

    def action_cancel(self) -> None:
        self.dismiss(None)


class SettingsScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    SettingsScreen { align: center middle; }
    #settings-dialog {
        width: 84;
        height: auto;
        min-height: 18;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #settings-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #settings-panels { layout: horizontal; height: 12; }
    #settings-src-col { width: 1fr; padding-right: 1; border-right: ascii $primary-darken-2; }
    #settings-tgt-col { width: 1fr; padding-left: 1; }
    .settings-col-title { text-style: bold; color: $text-muted; }
    .settings-col-list { height: 8; }
    .settings-col-hint { color: $text-muted; height: 1; }
    #settings-footer { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("escape", "save_and_close", "儲存並離開"),
        Binding("a", "add_entry", "新增"),
        Binding("e", "edit_entry", "編輯"),
        Binding("delete", "delete_entry", "刪除"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = Config(sources=list(config.sources), targets=list(config.targets))
        self._modified = False

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Label("設定", id="settings-title")
            with Horizontal(id="settings-panels"):
                with Vertical(id="settings-src-col"):
                    yield Label("Sources", classes="settings-col-title")
                    yield ListView(id="src-list", classes="settings-col-list")
                    yield Label("[A] 新增  [E/Enter] 編輯  [Del] 刪除", classes="settings-col-hint")
                with Vertical(id="settings-tgt-col"):
                    yield Label("Targets", classes="settings-col-title")
                    yield ListView(id="tgt-list", classes="settings-col-list")
                    yield Label("[A] 新增  [E/Enter] 編輯  [Del] 刪除", classes="settings-col-hint")
            yield Label("Tab 切換區塊  Esc 儲存並離開", id="settings-footer")

    def on_mount(self) -> None:
        self._reload_sources()
        self._reload_targets()
        self.query_one("#src-list", ListView).focus()

    # ── list rebuild ─────────────────────────────────────────────

    def _reload_sources(self) -> None:
        lv = self.query_one("#src-list", ListView)
        lv.clear()
        for s in self._config.sources:
            lv.append(ListItem(Label(f"{s.label}  ({config_mod.unexpand(s.path)})")))

    def _reload_targets(self) -> None:
        lv = self.query_one("#tgt-list", ListView)
        lv.clear()
        for t in self._config.targets:
            lv.append(ListItem(Label(f"{t.name}  ({config_mod.unexpand(t.path)})")))

    # ── focus tracking ────────────────────────────────────────────

    def _active_panel(self) -> str:
        """Return 'sources' or 'targets' based on which list contains the focused widget."""
        src = self.query_one("#src-list", ListView)
        node = self.focused
        while node is not None:
            if node is src:
                return "sources"
            node = node.parent
        return "targets"

    def _active_list_idx(self) -> tuple[str, ListView, int] | None:
        panel = self._active_panel()
        lv = self.query_one("#src-list" if panel == "sources" else "#tgt-list", ListView)
        idx = lv.index
        if idx is None:
            return None
        return panel, lv, idx

    # ── Enter on list item = edit ─────────────────────────────────

    @on(ListView.Selected, "#src-list")
    def _src_enter(self, _: ListView.Selected) -> None:
        self.action_edit_entry()

    @on(ListView.Selected, "#tgt-list")
    def _tgt_enter(self, _: ListView.Selected) -> None:
        self.action_edit_entry()

    # ── actions ───────────────────────────────────────────────────

    def action_add_entry(self) -> None:
        if self._active_panel() == "sources":
            def handle(result: SourceConfig | None) -> None:
                if result:
                    self._config.sources.append(result)
                    self._modified = True
                    self._reload_sources()
            self.app.push_screen(SourceFormScreen(), handle)
        else:
            def handle(result: TargetConfig | None) -> None:
                if result:
                    self._config.targets.append(result)
                    self._modified = True
                    self._reload_targets()
            self.app.push_screen(TargetFormScreen(), handle)

    def action_edit_entry(self) -> None:
        info = self._active_list_idx()
        if not info:
            return
        panel, _, idx = info
        if panel == "sources":
            if idx >= len(self._config.sources):
                return
            current = self._config.sources[idx]
            captured = idx
            def handle(result: SourceConfig | None) -> None:
                if result:
                    self._config.sources[captured] = result
                    self._modified = True
                    self._reload_sources()
            self.app.push_screen(SourceFormScreen(current), handle)
        else:
            if idx >= len(self._config.targets):
                return
            current = self._config.targets[idx]
            captured = idx
            def handle(result: TargetConfig | None) -> None:
                if result:
                    self._config.targets[captured] = result
                    self._modified = True
                    self._reload_targets()
            self.app.push_screen(TargetFormScreen(current), handle)

    def action_delete_entry(self) -> None:
        info = self._active_list_idx()
        if not info:
            return
        panel, _, idx = info
        if panel == "sources":
            if idx >= len(self._config.sources):
                return
            item_name = self._config.sources[idx].label
            captured = idx
            def handle(confirmed: bool) -> None:
                if confirmed:
                    self._config.sources.pop(captured)
                    self._modified = True
                    self._reload_sources()
            self.app.push_screen(DeleteConfirmScreen(item_name), handle)
        else:
            if idx >= len(self._config.targets):
                return
            item_name = self._config.targets[idx].name
            captured = idx
            def handle(confirmed: bool) -> None:
                if confirmed:
                    self._config.targets.pop(captured)
                    self._modified = True
                    self._reload_targets()
            self.app.push_screen(DeleteConfirmScreen(item_name), handle)

    def action_save_and_close(self) -> None:
        if self._modified:
            config_mod.save(self._config)
        self.dismiss(self._modified)


class SkillLinkerApp(App):
    TITLE = "Skill Linker"
    CSS_PATH = _CSS_PATH

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "離開"),
        Binding("s", "open_settings", "設定"),
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
        # Sync selected to match current reality: linked skills are pre-selected
        self.selected = {e.name for e in self.entries if e.status == LinkStatus.LINKED}
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

    def action_open_settings(self) -> None:
        def handle(modified: bool) -> None:
            if modified:
                self.config = config_mod.load()
                self._rebuild_source_panel()
                self._refresh_data()
        self.push_screen(SettingsScreen(self.config), handle)

    def _rebuild_source_panel(self) -> None:
        panel = self.query_one("#source-panel", Vertical)
        for item in panel.query(".source-item"):
            item.remove()
        for src in self.config.sources:
            panel.mount(Label(f"  {src.label}", classes="source-item"))

    def action_switch_target(self) -> None:
        def handle(result: TargetConfig | None) -> None:
            if result:
                self.current_target = result
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
