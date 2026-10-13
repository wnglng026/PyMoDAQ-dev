# 中文文档索引（本 fork 自研内容）

> 这个目录是**我们 fork 的工作文档**，不属于上游 PyMoDAQ。上游文档在 `docs/src/`（sphinx）。
> 面向 AI 助手（ChatGPT 网页版 / Codex 等）的一页纸约定在仓库根 [`AGENTS.md`](../../AGENTS.md)。

## 阅读顺序

| # | 文档 | 解决什么问题 |
|---|---|---|
| 1 | [PyMoDAQ-dev-代码库分析.md](PyMoDAQ-dev-代码库分析.md) | 仓库是什么、5 包 monorepo 怎么分层、i18n 落点在哪、有哪些风险（**顶部有勘误，以勘误为准**） |
| 2 | [PyMoDAQ-dev-方案.md](PyMoDAQ-dev-方案.md) | 汉化整体方案（三层架构）、USB2830 振动采集插件方案（实机 + 模拟）、本地调试脚本、迁移清理清单 |
| 3 | [PyMoDAQ汉化-进展与交接.md](PyMoDAQ汉化-进展与交接.md) | **当前进度**（哪些做完了、怎么验的）、五条硬约束、剩余待办、常用命令速查 |
| 4 | [PyMoDAQ-ChatGPT网页版协作方案.md](PyMoDAQ-ChatGPT网页版协作方案.md) | 用 ChatGPT 网页版开发 + 本地拉取调试的流程、任务卡/回传模板、验收清单、踩坑清单 |

## 关键事实速查（2026-10-13 实测）

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/wnglng026/PyMoDAQ-dev`（fork of `PyMoDAQ/PyMoDAQ`；官方只读引用走 `official/*`，不占 remote 列表） |
| 默认分支 | `5.3.x`（= 上游 tag `5.3.2`） |
| 自研分支 | `wngln/i18n`（汉化，P1–P3 已完成）、`wngln/usb2830`（插件，方案已定、代码未开工）、`wngln/dll-encoding`（编码修复 `9c8105cb`） |
| 汉化现状 | 语言包 `pymodaq_gui` 465 + `pymodaq` 518 = **983 条**；可译条目**未译 0**、占位符一致性通过 |
| 剩余待译 | 50 处界面文案未包装（19 个非 examples 文件，清单见交接文档 §9.3） |
| 本地 worktree | `PyMoDAQ-dev`（`5.3.x`）、`PyMoDAQ-dev-i18n`（`wngln/i18n`），各带独立 `.venv` |

## 维护约定（重要）

这些文档的**母本在工作区**，本目录是发布到 GitHub 的镜像（目的是让 ChatGPT 网页版开仓即可读）：

| 本目录 | 母本 |
|---|---|
| `docs/zh/PyMoDAQ-dev-代码库分析.md` | `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-代码库分析.md` |
| `docs/zh/PyMoDAQ-dev-方案.md` | `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-方案.md` |
| `docs/zh/PyMoDAQ汉化-进展与交接.md` | `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ汉化-进展与交接.md` |
| `docs/zh/PyMoDAQ-ChatGPT网页版协作方案.md` | `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-ChatGPT网页版协作方案.md` |

同步（**先改母本，再镜像过来**）：

```powershell
$src = 'D:\工作目录\振动诊断系统扩展方案'
$dst = Join-Path $src 'PyMoDAQ-dev-i18n\docs\zh'
foreach ($n in 'PyMoDAQ-dev-代码库分析.md','PyMoDAQ-dev-方案.md','PyMoDAQ汉化-进展与交接.md','PyMoDAQ-ChatGPT网页版协作方案.md') {
    Copy-Item -LiteralPath (Join-Path $src $n) -Destination $dst -Force
}
git -C (Join-Path $src 'PyMoDAQ-dev-i18n') status --short docs/zh
```

> 内容有更新时，`wngln/i18n` 与 `5.3.x` 两个分支都更新一次（内容完全相同，后续合并不会冲突）。
