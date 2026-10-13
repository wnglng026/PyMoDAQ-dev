# PyMoDAQ-dev 代码库分析

> 分析对象：`D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev`
> 远端：`https://github.com/wnglng026/PyMoDAQ-dev`（fork of `PyMoDAQ/PyMoDAQ`）
> 分析时间：2026-10-11 · 检出 `5.3.x` @ `629f3b71` = 上游 tag `5.3.2`，工作区干净
> 标注约定：**实测** = 本次在本机实际执行命令/扫描得到的数字；**推断** = 经验判断，需验证。

> **⚠️ 勘误（2026-10-13 实测更新，写方案前必读）**
>
> 本文 10-11 写作时看到的状态**已经过期**，以下以最新实测为准：
>
> - `git stash list` 现在是**空的**（两个 worktree 都是 0 条）——原文"汉化 WIP 在 `stash@{0}`"作废；
>   `wngln/i18n` 上的汉化工作**早已全部提交并推送**（当前 `9e295aa3f`），P1 骨架 + P2 代码改造 + P3 译稿
>   （可译 983 条 100%）都已完成。凡以"从 stash 恢复"为前提的步骤一律作废。
> - 三个 `wngln/*` 分支**不再同 SHA**：`wngln/i18n` 已推进到 `9e295aa3f`；`wngln/usb2830` / `wngln/dll-encoding`
>   各自独立。
> - 本地现在是**两个 worktree**（同一仓库）：`PyMoDAQ-dev`（分支 `5.3.x`，基线）与
>   `PyMoDAQ-dev-i18n`（分支 `wngln/i18n`，汉化工作区），各带独立 `.venv`。汉化/调试都在后者做。
> - 进度与后续计划见 `PyMoDAQ汉化-进展与交接.md`（§9.1–9.3 记录了 10-13 的补漏与剩余 50 处待译）。

---

## 0. 结论速览

| 判断 | 依据 |
|---|---|
| 本库是官方仓库的 **1:1 镜像**，零自研提交 | 18 个远端分支与上游逐一 SHA 相同；fork 的 `pushed_at` = 上游 `pushed_at` = 2026-10-09T20:01:28Z |
| 结构是 **5 包 monorepo**，约 **13.7 万行 Python** | 实测 AST 无关的逐文件统计：522 个 `.py` / 137,194 行（packages 内 516 个 / 136,519 行） |
| 依赖是**严格单向四层**，无环 | 从 5 个 `pyproject.toml` 的依赖声明读出：utils → data → gui → pymodaq |
| **库内目前没有任何 i18n 基础设施** | 实测：全库 `self.tr(` = **0** 处、`QTranslator` = **0** 处、`QCoreApplication.translate` = **1** 处、含中文的 `.py` = **0** 个 |
| 界面字符串约 **1.1k 条 / 80 个文件** | 本次正则粗扫 1,109 条；与你 AST 精扫的 1,177 条 / 119 文件量级一致（互为交叉验证） |
| ⚠️ **当前检出的 `5.3.x` 不含那处中文路径修复** | `environment.py` 编码修复（`9c8105cb`）只存在于 `wngln/dll-encoding` / `wngln/i18n` / `wngln/usb2830` 三个分支 |
| ✅ i18n **已落地**（10-13 更新） | 原判断"汉化 WIP 在 stash 里"已过期：`stash list` 为空，i18n 全部提交在 `wngln/i18n`（`9e295aa3f`），语言包 983 条 / 未译 0 |

---

## 1. 仓库身份（实测）

| 项 | 实测值 |
|---|---|
| `origin` | `https://github.com/wnglng026/PyMoDAQ-dev.git` |
| `upstream` | `https://github.com/PyMoDAQ/PyMoDAQ.git` |
| 默认分支 / 当前分支 | `5.3.x`（= `629f3b71` = tag `5.3.2`） |
| 远端分支数 | 36 个引用 = origin 18 + upstream 18，两侧 SHA 逐一对齐 |
| 本地分支 | 4 个：`5.3.x` + `wngln/i18n`、`wngln/usb2830`、`wngln/dll-encoding` |
| 本地独有提交 | 仅 `9c8105cb` 一个（在三个 `wngln/*` 上，**未推送**） |
| 克隆来源 | 本地的旧目录 `D:\...\PyMoDAQ`（reflog：`clone: from D:\...\PyMoDAQ`），该目录已删 |
| 体积 | 单个 pack 257 MB（完整上游历史，属正常） |

### 需要更正文档的一处

你的方案文档开头写「基线：`https://github.com/wnglng026/PyMoDAQ`」，但**实测**：

- 本库 `origin` 指向的是 **`wnglng026/PyMoDAQ-dev`**；
- `https://api.github.com/repos/wnglng026/PyMoDAQ` 现在**返回 404** —— 说明这个 fork **被改名为 `PyMoDAQ-dev`** 了（GitHub Desktop 日志里仍以旧名 `wnglng026/PyMoDAQ` 称呼它，正是改写名之前的残留）。

---

## 2. 规模与结构（实测）

### 2.1 各包体量

| 包 | 文件 | 代码行 | 占比 | 其中 src | 其中 tests |
|---|---|---|---|---|---|
| `pymodaq_gui` | 180 | 75,092 | 55% | 67,215 | 7,877 |
| `pymodaq`（应用层） | 250 | 38,594 | 28% | 33,981 | 4,613 |
| `pymodaq_data` | 37 | 14,686 | 10% | 8,977 | 5,709 |
| `pymodaq_utils` | 42 | 7,554 | 5% | 5,880 | 1,674 |
| `pymodaq_scripting` | 7 | 593 | 0% | 585 | 8 |
| **合计** | **516** | **136,519** | 100% | 116,638 | 19,881 |

> 测试占比约 **15%**（19,881 / 136,519），上游自带 pytest 基线 512 passed / 3 skipped。

### 2.2 子模块分布（代码行）

| 包 | 主要子模块 |
|---|---|
| `pymodaq` | `extensions` 13,756 · `utils` 11,351 · `control_modules` 6,350 · 顶层文件 1,294 · `launcher` 559 |
| `pymodaq_gui` | `resources` **33,479**（见下）· `plotting` 8,543 · `utils` 8,088 · `examples` 6,696 · `managers` 4,727 · `parameter` 3,487 · `h5modules` 1,291 · `editor` 478 |
| `pymodaq_data` | 顶层（`data.py` 为主）4,383 · `h5modules` 4,044 · `plotting` 294 |
| `pymodaq_utils` | 顶层 5,226 · `serialize` 609 |

**注意一个"虚胖"处（实测）**：`pymodaq_gui/resources` 的 33,479 行里，绝大部分是**生成的图标资源**：

| 文件 | 行数 |
|---|---|
| `resources/material_icons/resources/icons_rounded_40.py` | 17,687 |
| `resources/material_icons/resources/icons_rounded_20.py` | 15,582 |

→ 统计"要做汉化的代码量"或"复杂度"时**必须排除**这两个（合计 33,269 行，占全库 24%），否则所有比例都会被带偏。真正的 GUI 逻辑约 3.4 万行。

### 2.3 最大的业务文件（已排除生成资源）

| 行数 | 文件 |
|---|---|
| 4,019 | `pymodaq_data/src/pymodaq_data/data.py` |
| 2,032 | `pymodaq_gui/src/pymodaq_gui/utils/widget_sync/core.py` |
| 1,757 | `pymodaq/src/pymodaq/extensions/scan/daq_scan.py` |
| 1,334 | `pymodaq_data/src/pymodaq_data/h5modules/data_saving.py` |
| 1,288 | `pymodaq_gui/src/pymodaq_gui/plotting/data_viewers/viewer2D.py` |
| 1,274 | `pymodaq_data/src/pymodaq_data/h5modules/backends.py` |
| 1,266 | `pymodaq/src/pymodaq/control_modules/daq_viewer.py` |

---

## 3. 架构分层（实测：依赖单向，无环）

```
        ┌─────────────────────────────────────────────┐
        │  pymodaq       应用层 / 扩展 / 控制模块       │  38,594 行
        │  launcher · dashboard · control_modules      │
        │  extensions(scan/seq/logger/ramping)         │
        └───────────────┬─────────────────────────────┘
                        │ 依赖
        ┌───────────────▼─────────────────────────────┐
        │  pymodaq_gui   界面与绘图                     │  75,092 行
        │  parameter(参数树) · plotting · utils         │
        │  managers · widget_sync · editor             │
        └───────────────┬─────────────────────────────┘
                        │ 依赖
        ┌───────────────▼─────────────────────────────┐
        │  pymodaq_data  数据模型与 HDF5 落盘           │  14,686 行
        │  data.py(DataWithAxes) · h5modules(SWMR)     │
        └───────────────┬─────────────────────────────┘
                        │ 依赖
        ┌───────────────▼─────────────────────────────┐
        │  pymodaq_utils  基座：配置/日志/环境/串行化    │   7,554 行
        └─────────────────────────────────────────────┘
        （pymodaq_scripting 旁挂：只依赖 utils + data）
```

各包的关键第三方依赖（摘自 `pyproject.toml`，实测）：

| 包 | 关键依赖 |
|---|---|
| `pymodaq_utils` | `serializall` |
| `pymodaq_data` | `pymodaq_utils` · `h5py>=2.5` · `tables>=3.10` |
| `pymodaq_gui` | `pymodaq_data` · `pyqtgraph>=0.12` · `qt_material_icons` · `pyside6<6.12` |
| `pymodaq` | 上面 4 个包 + `pymodaq_plugin_manager` · `pymodaq_plugins_mock` · `pyleco>0.3` · `bayesian-optimization>=2.0` |
| 全部 | `requires-python >= 3.10` |

> `pyside6<6.12` 是上游最近的封顶（提交 `3684438e`：6.12.0 的 `Signal(bool)` 实现有 bug 会让解释器直接退出）。

---

## 4. 运行入口（实测：11 个 console_scripts）

| 命令 | 入口 |
|---|---|
| `pymodaq` | `pymodaq.launcher.launcher:main`（启动器，其余功能的"总控"） |
| `dashboard` | `pymodaq.dashboard:main` |
| `daq_viewer` | `pymodaq.control_modules.daq_viewer:main` |
| `daq_move` | `pymodaq.control_modules.daq_move:main` |
| `daq_scan` | `pymodaq.extensions.scan.daq_scan:main` |
| `daq_logger` | `pymodaq.extensions.daq_logger:main` |
| `sequencer` | `pymodaq.extensions.sequencer.sequencer:main` |
| `ramping` | `pymodaq.extensions.ramping.ramping:main` |
| `check_plugin` | `pymodaq_utils.plugin_checks:main`（插件校验，写插件时会用到） |
| `h5browser` | `pymodaq_gui.h5modules.h5browser:main` |
| `parameter_example` | `pymodaq_gui.examples.parameter_ex:main` |

**进程模型（实测，对汉化方案有直接影响）**：启动器不是把界面都装在一个进程里，而是用
`subprocess` 逐个拉起独立进程：

```python
popen_with_splash([sys.executable, '-m', 'pymodaq.dashboard'], ...)
popen_with_splash([sys.executable, '-m', 'pymodaq.control_modules.daq_viewer'], ...)
popen_with_splash([sys.executable, '-m', 'pymodaq.control_modules.daq_move'], ...)
popen_with_splash([sys.executable, '-m', 'pymodaq.extensions.h5browser'], ...)
args_lst = [sys.executable, '-m', 'pymodaq.dashboard', ...]   # 打开扩展时
```

---

## 5. 插件体系（实测）

- 入口点是标准 entry points，取用函数：`pymodaq_utils/utils.py:496` → `get_entrypoints(group='pymodaq.plugins')`
- 相关组：`pymodaq.plugins`（旧命名）与 `pymodaq.instruments`（新命名），`daq_utils` 会同时查询两者
- 硬件支持**不放在本仓库**，而是外部包（`pymodaq_plugins_mock` 就是随 `pymodaq` 一起装的依赖）→ 你的 USB2830 插件做成独立包 `pymodaq_plugins_usb2830` 与上游架构一致 ✅
- 5.3 新增了**无硬件插件测试 harness**（提交 `6c99c31d`/`ea3f0e28`：`plugin_testing` 模块 + 验收 mixin）→ 正好用于你方案 3.7 的"无硬件验收"

---

## 6. i18n 落点分析（与你的方案对接）

### 6.1 关键实测：库内零 i18n 基础设施

| 检查项 | 实测结果 | 含义 |
|---|---|---|
| `self.tr(` | **0** | 界面文案全是硬编码英文字面量，**没有一处走 Qt 翻译** |
| `QTranslator` | **0** | 从未加载过任何 `.qm`（连 Qt 自带 `qtbase_zh_CN.qm` 也没用过） |
| `QCoreApplication.translate` | 1 | 孤立一处 |
| 含中文的 `.py` | 0 | 干净基线，无历史污染 |
| `lrelease` | 缺失（仅 `pylupdate6`） | 与你的实测一致 |

**结论**：你的方案里"新建 `LanguageManager` + `.ts` 骨架"是**必需项**，不是优化项 —— 上游没有留任何可复用的接入点。你 stash 里的 `pymodaq_utils/i18n.py`（467 行）+ `pymodaq_gui/i18n.py`（110 行）正是补这个空。

### 6.2 界面字符串分布（本次粗扫，用于分批）

| 模块 | 约计条数 | 文件数 |
|---|---|---|
| `pymodaq/extensions` | 338 | 14 |
| `pymodaq_gui/utils` | 177 | 17 |
| `pymodaq/dashboard.py` | 153 | 1 |
| `pymodaq_gui/parameter` | 123 | 12 |
| `pymodaq_gui/managers` | 114 | 7 |
| `pymodaq/utils` | 87 | 11 |
| `pymodaq_gui/plotting` | 58 | 9 |
| `pymodaq/control_modules` | 30 | 4 |
| `pymodaq/launcher` | 15 | 1 |
| `pymodaq_gui/editor` / `h5modules` / `messenger` | 6 / 6 / 2 | 各 1 |
| **合计（粗扫）** | **1,109** | **80** |

> 你 AST 精扫是 1,177 条 / 119 文件。两者差异来自口径（我的正则只统计"界面调用附近的英文字面量"，会漏掉 `'title'` 关键字、`add_action` 等形态，也会漏掉 `pymodaq_data` 等非 GUI 包）。**互相印证：量级正确，可以放心按 1.1k 量级排工。**
> 建议 P2 分批就照这张表的顺序切：`extensions` → `gui/utils` → `dashboard` → `parameter` → `managers`（前 5 项就占 80%）。
> 排除项：`pymodaq_gui/resources/material_icons`（生成代码，33k 行）。

### 6.3 两个会影响 P1 设计的实测发现

**① `--lang` 传不到子进程。** 启动器用 `sys.executable -m ...` 起子进程，且**只转发 `-e <扩展>`**，不转发其它命令行参数。所以：

- 语言选择**必须以配置项为主**（你的 `gui.style.language` 是对的）；
- `--lang` 只在"直接跑 dashboard / daq_viewer / daq_scan"这类单进程入口时有效；
- 若确实要 `--lang` 全局生效，得在 launcher 里显式把参数拼进 `args_lst`。（推断，需实测确认）

**② L2 的 QTranslator 必须按进程各装一次。** 全库 `QApplication` 出现 **167** 处；至少 8 处显式 `QtWidgets.QApplication(sys.argv)` 构造（`post_treatment/load_and_plot`、`utils/chrono_timer`、`utils/managers/batchscan_manager`×2、`utils/managers/remote_manager`、`utils/scanner/scanner`、`utils/scanner/scan_selector`、`utils/svg/svg_renderer`），再加上各扩展/控制模块的 `main()`。

→ 建议做成一个 `install_translators(app)` 辅助函数，在**每个 `main()` 拿到 QApplication 之后立即调用**，而不是指望单一的启动点。这一步如果漏了，表现是"启动器是中文、点开 DAQ_Viewer 又变英文"（推断）。

---

## 7. 当前 git 状态与三个风险

### 7.1 状态

| 项 | 值 |
|---|---|
| `PyMoDAQ-dev` worktree | 分支 `5.3.x` @ `629f3b71`（tag 5.3.2），**工作区干净** |
| `PyMoDAQ-dev-i18n` worktree | 分支 `wngln/i18n` @ `9e295aa3f`，**工作区干净**（汉化全部已提交并推送） |
| `wngln/i18n` / `wngln/usb2830` / `wngln/dll-encoding` | `wngln/i18n` 已推进到 `9e295aa3f`；另两个分支各自独立推进，**不再同 SHA** |
| `stash` | **空**（两个 worktree 实测 `git stash list` 均为 0 条） |

**当前工作入口（10-13 实测，取代原"恢复 WIP"步骤）：**

```powershell
# 汉化 / 调试都在 i18n worktree 里做，它固定留在 wngln/i18n 分支
cd D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-i18n
git log --oneline -1          # 应为 9e295aa3f 或更新
.venv\Scripts\python.exe tools\i18n\i18n_audit.py    # 台账：未译应为 0
```

### 7.2 风险

| # | 风险 | 说明 | 建议 |
|---|---|---|---|
| 1 | **当前检出的 `5.3.x` 不含那处中文路径修复** | `9c8105cb` 只在三个 `wngln/*` 分支上。在中文路径下初始化 `pymodaq` 会被 `pymodaq/__init__.py` 的 try 吞掉 → `CONTROL_MODULES` 未定义 | 汉化/插件开发都在各自 `wngln/*` 分支上做；若必须用 `5.3.x`，先 `cherry-pick 9c8105cb` |
| 2 | 三个 `wngln/*` 分支同 SHA，容易混 | 名字长得很像，实际还没各自提交 | 开始干活前先确认 `git branch --show-current` |
| 3 | 分支都没有上游跟踪 | 推送时会出现 "no upstream branch" | 首次推送用 `git push -u origin wngln/i18n`（或在 GitHub Desktop 点「发布分支」） |

---

## 8. 与两份方案文档的出入（建议更正）

| # | 文档说法 | 实测 | 建议 |
|---|---|---|---|
| 1 | `PyMoDAQ-dev-方案.md` 开头：origin = `https://github.com/wnglng026/PyMoDAQ` | 实际 origin = **`.../PyMoDAQ-dev`**；`wnglng026/PyMoDAQ` 已 404（fork 改名） | 改文档，避免以后按旧地址找仓库 |
| 2 | 文档称 `wngln/i18n`、`wngln/usb2830` 是"从 `5.3.x` 切出"并已建立 | 三个分支都停在 `9c8105cb`，等于都从 `wngln/dll-encoding` 的血统上，尚未有各自提交 | 属正常，但**要在文档里记一句**"目前三者同 SHA"，免得误判进度 |
| 3 | 文档 §4.1 记该修复为"旧库里未提交的修复，需迁移" | 实测已迁移完成（`9c8105cb`，`5.3.x..wngln/i18n` 只有这一个提交） | 标为已完成 |
| 4 | 文档未提"库内 `tr()` 为 0" | 实测 0 处 | 补进方案，作为"必须新建 i18n 层"的硬依据 |
| 5 | 文档未提 `--lang` 无法传递到子进程 | 实测 launcher 只转发 `-e` | 补进 P1 设计（以配置项为主） |

---

## 9. 建议的下一步（对齐你的 P1）

1. ~~切到 `wngln/i18n` 并恢复 WIP~~ → **已完成（10-13）**：stash 为空，i18n 全部提交在 `wngln/i18n`（`9e295aa3f`）。
2. ~~P1 设计按 6.3 的两条修正~~ → **已实现**：语言以配置项/`PYMODAQ_LANG` 为准；`install_translators(app)` 在每个 `mkQApp()` 里调用。
3. ~~补 `lrelease`~~ → **已绕开**：PyQt6 无 `lrelease`，改用 TOML 语言包 + Python 版 `QTranslator`（见交接文档 §4）。
4. ~~P2 分批~~ → **已完成**：983 条语言包、未译 0；`material_icons` 生成代码未纳入统计。
5. ~~更正 §8 的 5 处文档出入~~ → **已更正**（本文顶部勘误 + 交接文档）。
6. **新增（10-13）**：剩余 50 处界面文案待包装（清单见交接文档 §9.3）；USB2830 插件代码尚未开工（方案见 `PyMoDAQ-dev-方案.md` §3）。

---

*本文所有"实测"项均可复现：统计脚本口径为逐文件行数累加（`.py`，排除 `__pycache__/build/dist/.pytest_cache`）；字符串量为正则匹配"界面调用附近的英文字面量"，与 AST 精扫口径不同、结果互为验证。*
