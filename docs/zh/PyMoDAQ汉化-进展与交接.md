# PyMoDAQ 汉化（i18n）· 进展与交接文档

> 生成日期：2026-10-13 ｜ 分支 `wngln/i18n` @ `88255135`
> 标注约定：**实测** = 本次在本机实际执行命令/扫描得到的数字；**推断** = 经验判断，需验证。

## 本文件定位（与另外两份文档的分工）

| 文档 | 定位 | 何时看 |
|---|---|---|
| **本文件** | **进展与交接**：做到哪一步、证据是什么、接下来做什么 | 接手继续干活时 |
| `PyMoDAQ-dev-方案.md` | 三份方案（汉化 / USB2830 插件 / 本地调试脚本）的完整设计 | 需要设计依据与阶段计划时 |
| `PyMoDAQ-dev-代码库分析.md` | 仓库本身的度量与架构分析 | 需要代码规模/分层/插件体系数据时 |
| `PyMoDAQ-多语言化方案.md` | 早期方案，**已被取代**（其"副本 PyMoDAQ-i18n"思路已废弃） | 仅作历史参考 |

---

## 0. 结论速览

| 问题 | 答案 |
|---|---|
| 汉化做到哪一步了？ | **P1 + P2 + P3 全部完成**：代码侧改造收口（871 条文案进入可翻译机制），**译文也已完成——890 条可译条目 100%**，另有 392 条按设计保留英文（标识符/示例代码/演示文案，见 `tools/i18n/allow_english.txt`） |
| 需要 `lrelease` 吗？ | **不需要**。改用「`.ts` 作者格式 → TOML 语言包 → Python 版 `QTranslator`」，`lrelease` 缺失不再是阻塞项 |
| 能证明链路真的生效吗？ | **能**：在关闭兜底词典层（`PYMODAQ_ZH=0`）的前提下，实测 `get_action('launch_dashboard')` = 「启动空仪表板」、DAQ_Viewer 设置树 `main_settings` = 「主设置：」 |
| 会不会破坏既有配置/插件？ | 有意设了边界：**不翻 `name`**（设置持久化的键）、**不翻 `limits`**（取值会写进配置文件） |
| 有回归吗？ | 无。回归 **323 passed**（唯一失败 `test_icon_qt` 是**既有** Windows 环境问题，已用未改写版本对照确认） |
| 下一步做什么？ | ① P3 译稿（1276 条，用 `pymodaq_zh` 的 650 条词典做种子）；② USB2830 插件骨架；③ CI 覆盖率门禁 |

---

## 1. 环境与仓库现状（实测）

| 项 | 值 |
|---|---|
| 主工作区 | `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev` @ `5.3.x`（`629f3b71` = 上游 tag 5.3.2），工作区干净 |
| i18n 工作区 | `PyMoDAQ-dev-i18n`（git worktree）@ `wngln/i18n` = `88255135`，工作区干净 |
| 分支 | `wngln/i18n`（13 个 i18n 提交）、`wngln/dll-encoding`、`wngln/usb2830`（后两者均为 `9c8105cb`） |
| remotes | `origin` = `https://github.com/wnglng026/PyMoDAQ-dev.git`（`remote.pushDefault = origin`）；`upstream` = 官方 PyMoDAQ（**推送已禁用 `no_push`**） |
| 官方对比引用 | `official/5.3.x`、`official/dev`（用 `dev\fetch-official.ps1` 抓取，**不占 remote 列表**） |
| 虚拟环境 | 两个 worktree 各一个：Python **3.12.13** + PyMoDAQ 5.3.2 + PyQt6 6.11.0 + pyqtgraph 0.14.0 + `pymodaq_zh` |
| 已知环境约束 | 官方支持 3.10–3.13；`pyside6` 必须 `<6.12`；本仓库以 CRLF 检出（`.gitattributes` = `* text=auto`） |

---

## 2. i18n 架构（三层，实测可用）

```
界面文本
  ├─ L1 Qt 自带语言包   qtbase_zh_CN.qm                    ← PyQt6 自带（标准对话框/按钮）
  ├─ L2 应用语言包      源码 tr()/.translate() → .ts → TOML ← 本方案主体，覆盖界面文案与参数标题
  └─ L3 运行时兜底词典  pymodaq_zh（650 条）                ← 插件文案、动态拼接、pyqtgraph 文本
```

* **L2 的加载器**：`pymodaq_gui.i18n.PackTranslator`（覆盖 `QTranslator.translate`，查 TOML 语言包），
  在 `mkQApp()` 里安装 → 所有 GUI 入口（`pymodaq`/`dashboard`/`daq_viewer`/…）自动生效 ✅
* **为什么不走 Qt 官方 `.qm`**：PyQt6 只自带 `pylupdate6`，**没有 `lrelease`**（实测），
  且 `pyside6-essentials` 下载在本机长期停滞。TOML + Python `QTranslator` 免依赖、可 diff、可评审。
* **语言解析优先级**：`PYMODAQ_LANG` 环境变量 > 配置 `[i18n] language` > 系统区域 > `en`；
  缺失条目回退 `[i18n] fallback`（默认 `en`）。

---

## 3. P1 交付与验证（i18n 骨架）

| 提交 | 内容 |
|---|---|
| `8a82bf06` | `pymodaq_utils/i18n.py`：语言解析、TOML 语言包加载/查找、命令行 `extract/pack/status`；配置模板加 `[i18n]`；入口脚本 `pymodaq-i18n` |
| `f77d47dc` | `pymodaq_gui/i18n.py`：`PackTranslator` + `install_translators()`；挂在 `mkQApp()` |
| `8960d062` | 示范 `tr()` 包装 + 生成 `pymodaq_zh_CN.ts` + 编译 `pymodaq_zh_CN.toml` |
| `6b796eec` | `pack` 支持从文件名推断语言（`pylupdate6` 生成的 `.ts` **不带** `language` 属性） |

**验证（关键：`PYMODAQ_ZH=0` 关掉兜底词典层，中文只可能来自 L2）**

| 检查 | 结果 |
|---|---|
| `core.lookup('Launcher','launcher')` | `启动器` ✅ |
| `QCoreApplication.translate('launcher','Launcher')`（经 `mkQApp` 装表后） | `启动器` ✅ |
| `get_action('launch_dashboard').text()` | **启动空仪表板** ✅ |
| `get_action('launch_h5browser').text()` | **启动 H5 浏览器** ✅ |
| 未包装的 `launch_viewer` | 仍为英文 ✅（反证：中文来自 `tr()` + 语言包，而非兜底词典） |

---

## 4. P2 交付与验证（代码侧改造收口）

### 4.1 覆盖面（实测）

| 类别 | 数量 | 做法 |
|---|---|---|
| 调用点字符串 | **801 条 / 77 文件** | AST 外科式改写：把文案包成 `QtCore.QCoreApplication.translate(上下文, 文案)`（只替换字符串节点，其余字节不动，幂等） |
| 参数树标题 | **474 条** | **不逐条改字典**（见 4.2），改在"构建参数树时集中翻译"，并把它们作为静态文案并入 `.ts` |
| f-string 动态文本 | **70 条** | 自动转成 `translate(模板).format(表达式…)`（花括号自动转义、格式说明符保留为占位符）；**0 条需人工** |
| 源码净改动 | **89 个文件，+8212 / −936 行** | 相对 `6b796eec`（含工具与语言包文件） |

### 4.2 参数标题为什么不能包 `tr()`

参数定义是**类属性里的字典字面量**（`params = [{'title': …}]`），在**模块导入时**就求值——那时翻译器还没安装，
包 `tr()` 也不会生效。因此：

* **运行时**：`pymodaq_gui.i18n.translate_params/translate_param/translate_title` 在**构建参数树时**翻译
  （接线 4 处：`ParameterManager` 建树、`create_parameter`、`parameter.utils` 反序列化、`settings_manager.populate_from_file`）；
* **提取端**：`pymodaq_utils.i18n.collect_static_messages/merge_static_messages` 扫描源码里 `'title'/'tip'` 的字典值
  与 `Parameter(...)` 的 `title=/tip=` 参数，作为 `general` 上下文并入 `.ts`，**译者可见、流程统一**。

**实测**（`PYMODAQ_ZH=0`）：真实 DAQ_Viewer 设置树 → `settings.child('main_settings').title()` = **主设置：**、
`child('main_settings','wait_time').title()` = **等待时间(ms)：**

### 4.3 工具（`tools/i18n/`）

| 工具 | 用途 |
|---|---|
| `i18n_codemod.py` | AST 外科式改写；`--dry-run`（看 diff）、`--report-only`（只出统计）、`--max-targets N`（分批/二分）、内置 f-string 通道与跳过白名单 |
| `i18n_audit.py` | 台账（提取条目 vs 已译）、**占位符一致性**校验、`--fail-under` 覆盖率门禁（可接 CI） |

### 4.4 当前台账（`i18n_audit.py` 输出）

| 包 | 条目 | 已译 | 覆盖率 |
|---|---|---|---|
| `pymodaq` | 484 | 6 | 1.2% |
| `pymodaq_gui` | 798 | 0 | 0.0% |
| **合计** | **1282** | **6** | **0.5%** |

占位符一致性：全部通过 ✅

### 4.5 回归与质量

| 检查 | 结果 |
|---|---|
| `compileall`（两个包全量） | 通过 ✅ |
| 回归测试（控制模块 + 视图 + managers + parameter） | **323 passed**，1 failed（`test_icon_qt`，**既有** Windows 环境问题：测试自带 `skipif IS_WINDOWS_CI`，且把 `action_manager.py` 还原为未改写版本后同样失败） |
| `git diff` 形态 | 无换行符 churn（见 5.5 与 6.1 的成因） |

---

## 5. 五条硬约束（踩坑后固化，务必遵守）

| # | 约束 | 原因（实测） |
|---|---|---|
| 5.1 | **不得翻译 `name`** | 它是设置持久化的键，翻了会让既有配置文件与实验文件读不回来 |
| 5.2 | **不得翻译 `limits`** | 列表项取值会被写进配置文件（选中值即字符串本身），翻译破坏兼容性 |
| 5.3 | **按字节做偏移运算** | `ast` 的 `col_offset` 是 UTF-8 **字节**偏移；与字符长度混用会把"字符串前面有非 ASCII 字符"的行写坏（曾导致 Git 判定文件为**非文本**、整文件伪变更） |
| 5.4 | **不要用 `self.tr`，统一用 `QCoreApplication.translate(上下文, 文案)`** | PyMoDAQ 里不少类**不继承 QObject**（如 `ParameterTreeWidget`），`self.tr` 会 `AttributeError` |
| 5.5 | **注入 import 要按"名字是否绑定"判断** | `from qtpy.QtCore import Slot, …` **不绑定**名字 `QtCore`；必须先看模块顶层是否绑定了这个名字 |

---

## 6. 环境级坑与绕过（都已在工具里修好）

### 6.1 `pylupdate6` 6.11.0 在本仓库路径下崩溃 —— 已绕过

**现象**：在本仓库路径下对**已改写**的文件跑 `pylupdate6`，它抛"An unexpected error occurred"（退出码 2，无堆栈）。
**定位证据**：同一份字节放到临时目录（ASCII 或中文路径都试过）就正常；逐文件扫描显示崩溃文件数 = 被改写文件数。
**绕过**：提取时**先把包源码镜像到临时目录**（跳过 `__pycache__`），在那里跑 `pylupdate6`，再把 `.ts` 合并回仓库，
并把 `location` 路径还原为仓库内相对路径（`pymodaq_utils.i18n.extract_fresh/extract_package`）。
**建议**：这是 PyQt 工具的 bug，值得向 PyQt 邮件列表上报（可复现，见上式）。

### 6.2 其它已修的工具问题

* 读取工具输出必须显式 `encoding='utf-8'`（否则本机 GBK 环境下 `subprocess` 的 reader 线程会崩）；
* `pack` 需要从**文件名**推断语言（`pylupdate6` 不写 `language` 属性，Qt Linguist 才写）；
* 改写涉及"非 QObject / 字节偏移 / import 绑定"三类问题，均已在 `i18n_codemod.py` 内固化。

---

## 7. 待确认事项（需你决定）

| # | 事项 | 说明 |
|---|---|---|
| 7.1 | **`PyMoDAQ-WL` 的用途** | 本机存在一个空克隆（origin = `wnglng026/PyMoDAQ-WL`，分支 `main` **无任何提交**）。若它是"汉化发行版"的目标仓库，我可以在其上建立分支/合并 `wngln/i18n` |
| 7.2 | 分析文档有一处**过期结论** | `PyMoDAQ-dev-代码库分析.md` 写有"汉化 WIP 在 stash 里"——实测两个仓库的 **stash 均为 0**，改动已全部提交在 `wngln/i18n` ✅ 建议更正 |
| 7.3 | 顶层重复脚本 | 方案根目录还留着一份 `PyMoDAQ-dev-i18n运行调试脚本.py`（项目目录内已有正式副本），删或留 |
| 7.4 | 插件包文案 | `pymodaq_plugins_*` 自带文案不在本台账内，属 L3/插件自带语言包范畴；是否纳入本轮范围 |
| 7.5 | 是否向上游提 PR | `9c8105cb`（中文路径编码修复）与 i18n 骨架都可作为 PR；目前策略是"只本地保留，不推送公共仓库" |

---

## 8. 下一步计划

### 8.1 P3：译稿（主体，预计 2–4 人日）

> ✅ **已完成（2026-10-13）**：新增 `tools/i18n/i18n_seed.py`（用 L3 词典 635 条做种子 + 人工映射）、
> `tools/i18n/zh_map.toml`（339 条人工译文）、`tools/i18n/allow_english.txt`（392 条按设计保留英文）。
> 结果：`pymodaq` 467/484、`pymodaq_gui` 423/798，**可译条目 890 条全部译完，覆盖率 100%，占位符一致性通过**；
> 语言包已编译（423 + 467 条）。**验证**：`PYMODAQ_ZH=0`（关闭兜底词典层）跑 7 个界面，中文覆盖率均 100%
> （启动器 17/17、采集视图 15/15、仪表板 18/18、Scanner 27/27、Logger 19/19、PID 22/22、Sequencer 18/18）。

```powershell
cd D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-i18n

# 1) 用既有 650 条词典做种子，注入 .ts（脚本待写：读 dictionary.py → 填 general/contexts 条目）
# 2) 补差量到 1276 条（可用 Qt Linguist 打开 .ts，或文本编辑）
.venv\Scripts\python.exe -m pymodaq_utils.i18n pack          # .ts -> TOML 语言包
.venv\Scripts\python.exe tools\i18n\i18n_audit.py            # 台账核对（目标：未译 0）

# 3) 运行期核对（关掉兜底词典层，确保中文来自 L2）
$env:PYMODAQ_ZH='0'; $env:PYMODAQ_LANG='zh_CN'
python PyMoDAQ-dev-i18n运行调试脚本.py 界面自检
python PyMoDAQ-dev-i18n运行调试脚本.py 启动器                 # 目视核对
```

### 8.2 CI 门禁

```powershell
.venv\Scripts\python.exe tools\i18n\i18n_audit.py --fail-under 95   # 覆盖率低于阈值即失败
```

### 8.3 USB2830 采集插件（方案已定，代码未开工）

在 `wngln/usb2830` 上做：`hardware/usb2830`（迁移现有 ctypes 驱动）+ 可切换的**实机/模拟后端** +
`DAQ_Viewer` 插件类 + 振动分析扩展；无硬件可跑通（模拟后端）+ 用 PyMoDAQ 的 `plugin_testing` 做验收。
细节见 `PyMoDAQ-dev-方案.md` §3。

---

## 9. 常用命令速查

```powershell
$wt = 'D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-i18n'
cd $wt

# 体检 / 运行 / 调试（dev 脚本都支持 -RepoRoot 指向任一工作区）
..\dev\status.ps1                       # 分支、与 official/* 的差异、venv、日志
..\dev\fetch-official.ps1               # 抓官方引用到 refs/remotes/official/*
..\dev\debug.ps1 dashboard              # 调试启动（异常钩子 + 环境诊断）
python PyMoDAQ-dev-i18n运行调试脚本.py 语言包进度

# i18n 流水线
.venv\Scripts\python.exe -m pymodaq_utils.i18n status     # 语言与进度
.venv\Scripts\python.exe -m pymodaq_utils.i18n extract    # 提取 tr() + 静态标题 -> .ts（走镜像）
.venv\Scripts\python.exe -m pymodaq_utils.i18n pack       # .ts -> TOML 语言包
.venv\Scripts\python.exe tools\i18n\i18n_audit.py         # 台账 / 占位符 / 门禁

# 回归测试（唯一既有失败 test_icon_qt 可忽略）
.venv\Scripts\python.exe -m pytest packages/pymodaq/tests/control_modules `
    packages/pymodaq_gui/tests/plotting_test/data_viewers_test `
    packages/pymodaq_gui/tests/managers packages/pymodaq_gui/tests/parameter_test `
    -q -m "not leco"
```

---

## 9.1 2026-10-13 补漏：启动器"点击快捷键区按钮 → 弹窗"未翻译（已修）

**你的反馈**：手动点击快捷键（启动器左侧"快捷键："标签下那 4 个按钮）后弹出的窗口未翻译。

**实测定位**（用探针脚本实机构建启动器 + 打桩 `subprocess.Popen` / `QSplashScreen.showMessage`，
在 `PYMODAQ_ZH=0`（只允许 L2 生效）下 dump 全部可见文案）——点按钮弹出的是 **QSplashScreen**，
文案来自 `launcher.popen_with_splash()` 的 Python 字符串，当初没被 `tr()` 包住，所以语言包里没有：

| 位置 | 原文（修复前） |
|---|---|
| 点 4 个启动按钮 | `Loading a DashBoard... Please wait...` 等 4 条 |
| 恢复历史实验启动 | `Loading a DashBoard with {} experiment and {} state...\nPlease wait...` |
| 启动扩展 | `Loading the {} extension... Please wait...` |
| 4 个按钮的 **tooltip**（悬停） | `Launch an empty Dashboard without configuration` 等 7 条（`EnumToolTip`） |

同一轮探针还扫出主窗口其它残留英文（顺带一起修了）：顶层菜单 `File/View/Tools/Help/Toolbars`、
`视图 > 工具栏` 里的工具栏名（`Runtime/Help/Header/experiment/State/Extensions`）、
`工具栏样式` 的 5 个选项、参数树搜索框占位符 `Search...`、重启确认框 `Do you want to restart?`、
更新对话框表头，以及日期下拉框里的 `at`（`%Y/%m/%d at %Hh%M` → `%Y/%m/%d %H:%M`）。

**做法**：`EnumToolTip` 与工具栏样式标签改成"调用时翻译"（新增 `get_tooltip()` /
`toolbar_button_style_label()`，字面量集中放在函数里，保证 pylupdate6 能提取），
其余直接就地包 `QCoreApplication.translate(context, ...)`；新增 32 条译文进 `tools/i18n/zh_map.toml`，
再跑 extract → seed → pack。

**复验（实测，`PYMODAQ_ZH=0`）**

| 项 | 结果 |
|---|---|
| 点按钮弹窗 | `正在加载仪表板……请稍候……` / `正在加载采集视图……` / `正在加载 DAQ_Move……` / `正在加载 H5 浏览器……` |
| 启动扩展 | `正在加载 Scanner 扩展……请稍候……` |
| 4 个按钮 tooltip | `启动一个无配置的空仪表板` 等，全中文 |
| 菜单栏 | 文件 / 视图 / 工具 / 帮助；工具栏、工具栏样式（仅图标…跟随系统样式） |
| 日期下拉框 | `2026/10/12 00:39`（`at` 已消失） |
| 台账 | 条目 923、未译 **0**、覆盖率 100%、占位符一致性通过 |
| 相关测试 | `pytest packages/pymodaq/tests/launcher packages/pymodaq_gui/tests/managers packages/pymodaq_gui/tests/utils` → **274 passed** |

**仍保留英文（有意）**：扩展下拉框里的 `Scanner/Logger/PID/Sequencer…`（`ExtensionEnum` 值，属标识符）、
实验/状态条目名 `default`、`empty`、右上角工具栏名 `Launcher`（类名）。
另有 1 个上游 UI 小瑕疵：`视图 > 工具栏` 里有两项空白（`add_toolbar('controls')` /
`add_toolbar('launcher')` 没给 title），与翻译无关，未动。

---

## 9.2 2026-10-13 第二批：对话框/消息框/状态灯文案（已修）

顺着"弹窗未翻译"这条线扫同类问题：`tools/i18n/i18n_codemod.py` 的汇聚点（`SINK_RULES`）
原本只覆盖 `setText/setWindowTitle/QLabel/add_action…`，**完全没覆盖对话框类调用**，
于是 `addButton("Save")`、`setInformativeText("What do you want to do?")` 这类文案一直是英文。

同时发现一个工具 bug：路径判定写成"含 `/` 就跳过"，导致
`'Scan state: idle / running / complete / error'`、`'Show/hide log window'`
这类正常文案被误判为路径而**静默漏译**（整批状态灯 tooltip 都在内）。已改成
只匹配真正的路径/URL（`://`、反斜杠、`D:\`、`/home`、带扩展名的文件名）。

**本批改动**：新增汇聚点 `addButton / setInformativeText / setPlaceholderText / setLabelText /
showMessage / setDetailedText / addMenu / addAction`；对 17 个文件自动改写 55 处，
另手工补 5 处（`.format()` 形式、`"OK"`、脚本开关文案、扫描批次菜单标题）；
`zh_map.toml` 新增 24 条译文。语言包 → **pymodaq_gui 465 + pymodaq 518 = 983 条**。

覆盖到的界面（举要）：Dashboard 重启确认、扫描/记录/优化状态灯 tooltip、批次管理器与
远程管理器的 New/Modify、H5 文件锁定对话框（Retry / New File (Auto) / Browse...）、
配置管理器、子条目对话框、ROI 复制/删除、ListPicker / TreeFromToml / SubEntryHandler 按钮、
"关于"弹窗文案。

**复验（实测）**

| 项 | 结果 |
|---|---|
| 台账 | 条目 983、未译 **0**、覆盖率 100%、占位符一致性通过 |
| 按上下文抽样查表 | `[BatchManager] What do you want to do?` → 你想做什么？；`[ConfigManager] Modify` → 修改；`[ScanStatusBarManager] Scan state: …` → 扫描状态：…；`[DAQ_PID] Synchro {}` → 同步 {}；`[SubEntryHandler] Ok` → 确定 |
| 启动器界面 | 仍是全中文（点按钮弹窗 `正在加载仪表板……请稍候……`） |
| 回归测试 | `pytest packages/pymodaq/tests packages/pymodaq_gui/tests -m "not leco"` → **881 passed / 19 skipped / 1 xpassed**（`editor_test.py` 因本机缺 `PyQt6-WebEngine` 无法收集，既有环境限制） |

提交：`9e295aa3f`（已推送 `origin` = `wnglng026/PyMoDAQ-dev`）。

## 9.3 剩余待译（已量化，下一轮直接做）

`python tools/i18n/i18n_codemod.py --report-only` 还剩 **50 处**未包装的界面文案，
分布在 19 个文件（非 examples），主要是绘图控件与自绘控件的按钮/提示：

| 处数 | 文件 |
|---:|---|
| 11 | `pymodaq_gui/plotting/data_viewers/viewer2D.py` |
| 7 | `pymodaq_gui/utils/widgets/push.py` |
| 5 | `pymodaq_gui/managers/settings/utils.py` |
| 5 | `pymodaq_gui/parameter/pymodaq_ptypes/tableview.py` |
| 5 | `pymodaq_gui/utils/widgets/collapsible_widget.py` |
| 3 | `pymodaq/utils/compact_dock_manager.py` |
| 2 | `pymodaq_gui/plotting/data_viewers/viewer0D.py` |
| 1×12 | `daq_move_ui/ui_base.py`、`daq_viewer_ui/ui_base.py`、`daq_logger_legacy.py`、`sequencer/utilities/sequencer/sequence.py`、`utils/custom_ext.py`、`managers/state/state_manager.py`、`managers/manager_base.py`、`pymodaq_ptypes/pixmap.py`、`pymodaq_ptypes/text_pattern.py`、`viewer1D.py`、`viewerND.py`、`utils/custom_app.py` |

做法同前：`--dry-run` 看 diff → 应用 → `extract / seed / pack / audit` → 补 `zh_map.toml` → 跑测试。
另：`examples` 下 375 条例样文案仍按设计保留英文（`tools/i18n/allow_english.txt`）。

---

## 9.4 2026-10-13（三）审计/打包的"空结果"守卫（已修）

**来源**：ChatGPT 网页版指出"提取结果为空时，审计工具会误报 100% 覆盖率"。
**本地复现确认属实**：`i18n_audit.py` 里 `ratio = translated / (total - allowed) if total - allowed else 1.0`，
`total == 0` 时走 `else` 分支 → 打印 `✅ 全译 100.0%`。也就是说 pylupdate6 静默失败、
镜像复制不全、`.ts` 被截断这类事故，会被审计报成"通过"——正好掩盖最需要发现的问题。

| 改动 | 文件 | 效果 |
|---|---|---|
| 空提取守卫 | `tools/i18n/i18n_audit.py` | 条目为 0 且源码里有 `translate()/tr()` 调用 → **退出码 2** + 排查顺序；确实没有界面文案的包显示 `—`，不再按 100% 计 |
| 条目底线 | 同上 | 新增 `--min-entries PACKAGE=N`（可重复），供 CI 钉住底线 |
| fail-closed | 同上 | 没有可审计条目却设了 `--fail-under` → 退出码 2，不放行 |
| 打包写前自检 | `packages/pymodaq_utils/src/pymodaq_utils/i18n.py` | 生成的 TOML 解析失败或条目数不符 → **拒绝写出**并保留上一版（对应 `2a657d5e7` 那次"裸换行 → 语言包 0 条 → 界面空白"）；另有"条目从 N 条降到 0 条"的提醒 |
| Python 3.10 兼容 | 同上 + `pymodaq_utils/pyproject.toml` | `tomllib` → `tomli` 回退。原实现让 3.10 直接 `ImportError`，而 `mkQApp()` 会导入本模块 → 3.10 用户起不来 PyMoDAQ |

退出码语义（写进 docstring）：`0` 正常 / `1` 覆盖率低于 `--fail-under` / `2` **结果不可信**。

**验证（实测）**：13 项守卫自测全通过（空提取、门禁、`--min-entries`、写前自检、`tomli` 回退分支）；
真实 `pack` 与全量审计仍为 **983 条 / 未译 0 / 退出码 0**；
`pytest packages/pymodaq_utils/tests packages/pymodaq/tests/launcher` → **161 passed**。提交 `cf60ba803`。

---

## 附录 A：`wngln/i18n` 的 13 个提交（相对 `9c8105cb`）

| 提交 | 说明 |
|---|---|
| `88255135` | f-string 自动转换（70 处）+ 台账刷新（1282 条） |
| `9dbaab58` | 台账并入参数标题（1218 条）+ 3 条示范译文 |
| `36280bc8` | 参数标题集中翻译（474 条不再逐条改字典） |
| `b448fe48` | 改写工具支持 `--max-targets` |
| `f87b3191` | 生成 zh_CN 词条台账 |
| `6418e859` | 提取改为镜像到临时目录执行，绕过 `pylupdate6` 崩溃 |
| `7bffc489` | 包装 `pymodaq` 界面文案 |
| `25f584ba` | 包装 `pymodaq_gui` 界面文案 |
| `155ecb8e` | 新增改写与审计工具 |
| `6b796eec` | `pack` 支持从文件名推断语言 |
| `8960d062` | 示范 `tr()` 包装与 zh_CN 语言包（启动器 3 条） |
| `f77d47dc` | Qt 侧接入（Python `QTranslator` + `mkQApp` 安装点） |
| `8a82bf06` | 引入 i18n 核心与语言包机制（Qt 无关） |

另有 `9c8105cb`（所有自研分支的共同基础）：`environment.py` 备份文件编码修复——中文路径下的必需修复，
建议一并向上游提 PR。

## 附录 B：文件地图

| 路径 | 作用 |
|---|---|
| `PyMoDAQ-dev/`、`PyMoDAQ-dev-i18n/` | 主基线 / i18n 工作区（git worktree） |
| `PyMoDAQ-dev-i18n/packages/pymodaq_utils/src/pymodaq_utils/i18n.py` | i18n 核心（语言解析、语言包、`extract/pack/status`、静态文案提取） |
| `PyMoDAQ-dev-i18n/packages/pymodaq_gui/src/pymodaq_gui/i18n.py` | Qt 接入（`PackTranslator`、`install_translators`、`translate_params`） |
| `PyMoDAQ-dev-i18n/tools/i18n/i18n_codemod.py`、`i18n_audit.py` | 改写工具 / 审计与门禁 |
| `PyMoDAQ-dev-i18n/packages/*/src/*/resources/translations/*.ts|.toml` | 作者格式 / 运行时语言包 |
| `dev/*.ps1` | 环境搭建、运行、调试、体检、抓官方引用 |
| `调试启动核心.py` + 各项目 `*运行调试脚本.py` | 每项目一个运行调试入口（解释器守卫 + 依赖探测 + 异常钩子） |
| `pymodaq_zh/` | L3 运行时词典（650 条 + hooks + selfcheck + debug） |


## 9.6 2026-10-13：第三批绘图/表格控件补译（已提交，待本地流水线验证）

在独立分支 `wngln/chatgpt-i18n-ui-batch1` 上处理，不直接修改 `wngln/i18n`。

**本批改动**
- `viewer2D.py`：将 11 处图像工具提示（通道显隐、直方图缩放/显隐、ROI 管理器、等值线、十字光标、ROI 选择区、图像翻转）接入 `QCoreApplication.translate('View2D', ...)`。
- `managers/settings/utils.py`：翻译配置表格菜单，并把动态的 `Load/Save {entry_type}Manager file` 改为可提取的翻译模板格式。
- `parameter/pymodaq_ptypes/tableview.py`：翻译新增、删除行、清空、txt 加载/保存菜单。
- `compact_dock_manager.py`：翻译锁定提示、停靠位置，以及执行器/探测器图形显隐提示。
- `viewer0D.py`、`viewer1D.py`、`viewerND.py`：补齐最小值/最大值线、ROI 选择区和多维坐标轴切换提示。
- `tools/i18n/zh_map.toml`：新增对应人工译文（含动态占位模板）。

**验证状态（如实记录）**
- GitHub 文件更新成功，所有更改均位于独立分支。
- 尚未在本地运行 `extract → seed → pack → audit`、Python 编译检查或 PyQt GUI 回归测试；因此当前不能宣称语言包已更新或运行时汉化已验证。
- 下一步：在项目工作区运行完整流水线，检查提取条目数、占位符一致性和审计覆盖率；若通过，再执行相关 viewer / settings / parameter 测试，并继续处理剩余未包装文案。


### 9.7 同日追加：Pixmap 参数控件

- `pymodaq_gui/parameter/pymodaq_ptypes/pixmap.py`：将 `Show/Hide` 复选框接入 Qt 翻译系统。
- `zh_map.toml`：补充“显示/隐藏”。
- 本追加仍待完整提取、打包、审计与运行测试验证。
