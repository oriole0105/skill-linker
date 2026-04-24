# Skill Linker 使用指南

## 安裝與啟動

```bash
cd uv_prj/skill-linker
uv run skill-linker
```

首次執行會自動在 `~/.config/skill-linker/config.yaml` 建立預設設定檔。

---

## 設定 Source 與 Target

編輯 `~/.config/skill-linker/config.yaml`：

```yaml
sources:
  - label: Personal Skills      # 顯示名稱（隨意取）
    path: ~/.agents/skills      # 存放 skill 的目錄

targets:
  - name: Claude Code (global)  # 顯示名稱，也用於 --target 參數
    path: ~/.claude/skills
  - name: OpenCode
    path: ~/.opencode/skills
```

- **sources**：可加多個，Skill Linker 會合併顯示所有 source 下的 skill
- **targets**：各 AI 工具的 skill 安裝路徑，可隨時用 `T` 切換

---

## 主畫面操作

### 基本流程

1. 用 `↑` `↓` 移動游標瀏覽清單
2. 用 `Space` 勾選想安裝的 skill（`●` = 已選，`○` = 未選）
3. 按 `Enter` 預覽變更並確認

### 完整快捷鍵

| 鍵 | 功能 |
|----|------|
| `↑` `↓` | 移動游標 |
| `Space` | 選取 / 取消目前 skill |
| `A` | 全選（篩選後可見的所有 skill） |
| `N` | 清除所有選取 |
| `Enter` | 套用選取（link / unlink） |
| `D` | 查看目前 skill 的描述（SKILL.md） |
| `F` | 進入過濾輸入框 |
| `T` | 切換 target 目錄 |
| `R` | 重新整理（重新掃描狀態） |
| `Q` | 離開 |

### 狀態欄說明

| 圖示 | 意思 |
|------|------|
| `✓ linked` | 已安裝到目前 target |
| `– unlinked` | 尚未安裝 |
| `✗ broken` | symlink 存在但指向無效路徑（可重新 link 修復） |
| `⊘ direct (unmanaged)` | target 有同名目錄但不是 symlink，Skill Linker 不管理此項目 |

---

## 過濾功能

1. 按 `F` 進入過濾輸入框
2. 輸入關鍵字即時篩選（比對 skill 名稱與 source 名稱）
3. 在輸入框中按 `↑` `↓` 可直接移動清單游標
4. 按 `Enter` 確認並將焦點移到清單
5. 按 `Esc` 清空過濾並回到清單

---

## 套用確認

按 `Enter` 後會顯示確認對話框，列出：
- 將新增的 link
- 將移除的 link
- 套用的 target 路徑

```
確認操作
Link   (2):  sv-lint, sv-write
Unlink (1):  uvm-check

Target: /Users/you/.claude/skills

按 Y 確認，Esc / N 取消
```

按 `Y` 確認執行，按 `Esc` 或 `N` 取消。

---

## 查看 Skill 描述

游標移到任一 skill，按 `D` 開啟描述視窗，顯示該 skill 的 `SKILL.md` 內容。

按 `Esc` 或 `Q` 關閉。

---

## 切換 Target

按 `T` 開啟 target 選擇選單：

- `↑` `↓` 移動
- `Enter` 切換到選取的 target
- `Esc` 取消

切換後畫面自動重新整理，顯示新 target 的連結狀態。

---

## 命令列模式

不開 TUI，直接列出狀態：

```bash
uv run skill-linker list
```

指定特定 target：

```bash
# 用 config 中的 name
uv run skill-linker --target "Claude Code (global)"

# 直接指定路徑
uv run skill-linker --target ~/.opencode/skills
```

---

## 常見情境

### 將所有 skill 安裝到全域 Claude Code

```bash
uv run skill-linker
```

1. 確認 Header 顯示 `Target: ~/.claude/skills`
2. 按 `A` 全選
3. 按 `Enter` → `Y` 確認

### 只安裝特定幾個 skill

1. 按 `F` 輸入關鍵字縮小清單
2. 按 `Space` 勾選需要的 skill
3. 按 `Enter` → `Y` 確認

### 切換到專案目錄安裝

1. 按 `T` 選擇對應的 target
2. 重新勾選需要的 skill
3. 按 `Enter` → `Y` 確認

### 修復 broken symlink

broken 狀態的 skill 勾選後按 `Enter` 套用，Skill Linker 會先移除舊的 broken link 再重建正確的 symlink。

---

## 修改設定檔後

直接在 TUI 中按 `R` 重新整理即可，不需重新啟動。

（注意：新增的 source 或 target 在重啟後才會生效，`R` 只重新掃描目錄內容。）
