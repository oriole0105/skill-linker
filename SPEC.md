# Skill Linker — Functional Specification

## Overview

Skill Linker 是一個終端機 TUI 工具，用途是管理 AI 工具（Claude Code、OpenCode、RooCode 等）的 skill 安裝。

不同工具的 skill 安裝路徑各不相同，而 skill 的實體檔案統一放在一個或多個 source 目錄下。Skill Linker 以建立 symbolic link 的方式將 skill「安裝」到指定的 target 目錄，不複製任何檔案，保持單一來源。

---

## 核心概念

### Source 目錄
存放 skill 實體內容的倉庫目錄，可設定多個。每個 source 下的子目錄即為一個 skill（只要非隱藏目錄即視為 skill）。

### Target 目錄
AI 工具讀取 skill 的路徑。例如：
- Claude Code 全域：`~/.claude/skills/`
- Claude Code 專案：`./.claude/skills/`
- OpenCode：`~/.opencode/skills/`

### Skill
Source 下的一個子目錄。標準格式含 `SKILL.md`（描述文件）及 `rules/` 或 `templates/` 等子目錄，但 Skill Linker 對格式無強制要求。

### Link 狀態

| 狀態 | 符號 | 說明 |
|------|------|------|
| linked | `✓ linked` | target 有 symlink 正確指向此 skill |
| unlinked | `– unlinked` | target 沒有此 skill |
| broken | `✗ broken` | target 有 symlink 但指向無效路徑 |
| direct | `⊘ direct (unmanaged)` | target 有同名目錄但不是 symlink，不由本工具管理 |

---

## 設定檔

路徑：`~/.config/skill-linker/config.yaml`

首次執行自動建立，內含預設值。

```yaml
sources:
  - label: Personal Skills
    path: ~/.agents/skills
  - label: Company Skills
    path: ~/company/skills

targets:
  - name: Claude Code (global)
    path: ~/.claude/skills
  - name: Claude Code (project)
    path: ./.claude/skills
  - name: OpenCode
    path: ~/.opencode/skills
```

- `sources[].label`：顯示名稱（純粹標示用）
- `sources[].path`：支援 `~` 與環境變數展開
- `targets[].name`：顯示名稱，也用於 CLI `--target` 參數
- `targets[].path`：支援 `~` 與環境變數展開

---

## CLI 介面

```
skill-linker [--target <name|path>] [tui|list]
```

| 參數 / 子指令 | 說明 |
|---|---|
| `(無參數)` | 啟動 TUI，使用 config 第一個 target |
| `--target <name>` | 指定 target（對應 config 中的 name） |
| `--target <path>` | 直接指定路徑（不需在 config 中） |
| `list` | 純文字列出所有 skill 及其連結狀態後離開 |
| `tui` | 明確指定啟動 TUI（預設） |

---

## TUI 功能規格

### 主畫面佈局

```
┌─ Skill Linker ─ Target: ~/.claude/skills ─────────────────────────┐
│ Sources          │ Skills                                           │
│                  │ Filter...                                        │
│   Personal       │ ○  remotion-best-practices  Personal  ✓ linked  │
│   Skills         │ ●  sv-lint                  Personal  – unlinked│
│   Company        │ ○  sv-write                 Personal  – unlinked│
│   Skills         │ ○  uvm-check                Personal  ✓ linked  │
│                  │                                                  │
├──────────────────────────────────────────────────────────────────  │
│ Q 離開  T 切換Target  R 重新整理  A 全選  N 全取消  F 過濾  D 描述 │
└────────────────────────────────────────────────────────────────────┘
```

### 選取欄位
- `○` 未選取
- `●` 已選取

選取狀態代表「我希望此 skill 被安裝到 target」，按 `Enter` 後依選取狀態決定哪些需 link、哪些需 unlink。

### 功能列表

| 功能 | 鍵盤 | 說明 |
|------|------|------|
| 移動游標 | `↑` `↓` | 在清單中移動 |
| 選取/取消 | `Space` | 切換目前列的選取狀態 |
| 全選 | `A` | 選取所有（篩選後可見的）skill |
| 全取消 | `N` | 清除所有選取 |
| 套用 | `Enter` | 開啟確認對話框，預覽並執行 link/unlink |
| 過濾 | `F` | 進入過濾輸入框 |
| 描述 | `D` | 開啟目前 skill 的描述視窗（讀取 SKILL.md） |
| 切換 Target | `T` | 開啟 target 選擇選單 |
| 重新整理 | `R` | 重新掃描 source 與 target，更新狀態 |
| 離開 | `Q` | 結束程式 |

### 過濾輸入框

- `F` 進入輸入框
- 即時篩選（name 或 source label 包含輸入文字）
- `↑` `↓` 直接移動到清單（輸入框保持不動）
- `Enter` 關閉輸入框，焦點移到清單
- `Esc` 清空過濾文字並關閉輸入框

### 確認對話框（Enter 後）

列出將 link 與將 unlink 的 skill 名稱，以及 target 路徑。

| 鍵 | 動作 |
|----|------|
| `Y` | 確認執行 |
| `Esc` / `N` | 取消 |

### 描述視窗（D）

顯示目前 skill 的 `SKILL.md` 內容（Markdown 渲染）。若無 `SKILL.md` 則顯示目錄下第一個 `.md` 文件；若皆無則顯示提示訊息。

| 鍵 | 動作 |
|----|------|
| `Esc` / `Q` | 關閉 |

### Target 選擇選單（T）

以清單顯示 config 中所有 target，當前使用的以 `●` 標示。

| 鍵 | 動作 |
|----|------|
| `↑` `↓` | 移動 |
| `Enter` | 選擇並切換 target |
| `Esc` | 取消 |

切換 target 後自動清除選取狀態並重新掃描。

---

## Link 操作行為

### Link
```
ln -s <source_skill_path> <target_path/skill_name>
```
- 若 target 目錄不存在則自動建立（`mkdir -p`）
- 若已有 broken symlink 先移除再建立

### Unlink
- 只移除 symlink，不動 source 目錄
- 若狀態為 `direct`（真實目錄）則拒絕操作並顯示錯誤

### 套用邏輯
已選取 + 狀態非 linked → **link**
未選取 + 狀態為 linked → **unlink**
已選取 + 狀態為 linked → 不動作（已安裝）
未選取 + 狀態為 unlinked → 不動作（未安裝）

---

## 模組結構

```
src/skill_linker/
├── __init__.py
├── main.py        # CLI 入口，解析 args，啟動 TUI 或 list
├── config.py      # 讀寫 config.yaml，SourceConfig / TargetConfig dataclass
├── scanner.py     # 掃描 source/target，計算 LinkStatus，回傳 SkillEntry list
├── linker.py      # 執行 symlink 建立與移除
└── tui/
    ├── __init__.py
    ├── app.py     # Textual App，所有畫面與操作邏輯
    └── style.tcss # Textual CSS 樣式
```

---

## 相依套件

| 套件 | 用途 |
|------|------|
| `textual >= 8.2` | TUI 框架 |
| `pyyaml >= 6.0` | 讀寫 config.yaml |
| Python `>= 3.12` | |

執行方式：`uv run skill-linker`（不需全域安裝）
