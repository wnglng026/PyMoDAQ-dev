# PyMoDAQ-dev 基线 · 汉化 / USB2830 振动采集插件 / 本地调试脚本 方案

> 基线：`https://github.com/wnglng026/PyMoDAQ-dev` → 本地 `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev`
> （旧地址 `wnglng026/PyMoDAQ` 已 404：fork 改名过一次，以 `-dev` 为准）
> 本地检出：`5.3.x` @ `629f3b71`（tag 5.3.2）；汉化工作区 `PyMoDAQ-dev-i18n` @ `wngln/i18n` `9e295aa3f`
> **进度提示（2026-10-13）**：§2 汉化已全部落地（P1/P2/P3 完成，语言包 983 条、未译 0）；§3 USB2830 只有方案、代码未开工。
> remote：`origin` = 你的 fork，`upstream` = `PyMoDAQ/PyMoDAQ`（官方）
> 本文数字均为**实测**；标注「推断」的为经验估算。

---

## 0. 结论速览

| 事项 | 结论 |
|---|---|
| 该库现状 | **官方仓库的 1:1 镜像**：18 个分支与上游逐一 SHA 相同，**零自研提交**；`5.3.x` = `629f3b71` = 上游 tag `5.3.2` |
| 因此 | 之前全部实测结论继续成立（1177 条界面字符串 / 119 文件 / 60 处 f-string / `lrelease` 缺失 / 现有 650 条词典 7 界面 100%） |
| 开发基线选择 | **以 `5.3.x` 为产品基线**（与我们已验证的行为一致）；新功能实验走 `dev`；自研工作都放自己的分支 `wngln/*`，不要直接改上游分支名 |
| 汉化路线 | 分层混合：源码 `tr()`（主体）+ 运行时语言包（兜底）+ Qt 自带语言包（标准控件）→ 支持多语言 |
| USB2830 插件 | 独立包 `pymodaq_plugins_usb2830`，**同一套插件代码 + 可切换的"实机/模拟"后端**；模拟后端做到无需硬件即可跑通全链路与自动化测试 |
| 本地调试脚本 | `dev\` 目录下 4 个 PowerShell 脚本（环境搭建 / 启动 / 调试 / 体检），已验证可用 |
| 迁移提醒 | ~~旧库那处未提交修复（`environment.py` 编码）必须迁移~~ → **已完成**：`9c8105cb`，在 `wngln/*` 各分支上 |

---

## 1. fork 与分支分析（实测）

### 1.1 分支全景

对比方式：`git rev-parse` 逐分支比较 `origin/<b>` 与 `upstream/<b>`。

| 分支 | fork SHA | 上游 SHA | 对比 | 末次提交 |
|---|---|---|---|---|
| `5.3.x`（默认） | `629f3b71` | `629f3b71` | 一致 | 2026-10-09 |
| `5.2.x` | `a607f9ab` | 同 | 一致 | 2026-10-09 |
| `badges` | `ab28e348` | 同 | 一致 | 2026-10-09 |
| `dev` | `4685a8a4` | 同 | 一致 | 2026-10-09 |
| `feature/plugin_smoke_test` | `8dd948fd` | 同 | 一致 | 2026-10-09 |
| `fix/plugin_tests_color_env` | `0346db2c` | 同 | 一致 | 2026-10-07 |
| `fix/plugin_checks_stop_motion(_5.3.x)` | `fe025822` / `bcadc75c` | 同 | 一致 | 2026-10-07 |
| `fix/daq_viewer_cleanup` | `df950497` | 同 | 一致 | 2026-10-05 |
| `fix/quit_during_loading` | `2e3b48da` | 同 | 一致 | 2026-10-04 |
| `fix/viewer2D_zorder` | `071943cb` | 同 | 一致 | 2026-10-04 |
| `feature/optimizer_refactoring` | `c3ed652f` | 同 | 一致 | 2026-09-14 |
| `feature/highlight_manager_entry` | `dc7a3629` | 同 | 一致 | 2026-06-28 |
| `5.1.x` / `5.0.x` / `4.4.x` | — | 同 | 一致 | 历史发布分支 |
| `test/scanners_evaluate_steps` | `74b14439` | 同 | 一致 | 2026-10-09 |

> 分支集合：fork 18 个 = 上游 18 个，**无多、无少**（另有 `origin/HEAD` 符号引用，非真实分支）。

### 1.2 各分支的角色（上游约定）

| 分支类型 | 作用 | 我们的使用方式 |
|---|---|---|
| `5.3.x` | 当前发布分支，只收 bugfix | **产品基线**：汉化分支、插件分支都从这里切 |
| `dev` | 开发主干，新功能先合这里 | 只作参考：想跟进将来 5.4 特性时查看 |
| `5.2.x` / `5.1.x` / `5.0.x` / `4.4.x` | 历史发布分支（仅 hotfix） | 不用 |
| `badges` | CI 徽章数据（机器写入） | 不用 |
| `feature/*` / `fix/*` / `test/*` | 上游在研/修复/测试分支 | 只读参考（`feature/plugin_smoke_test` 对我们写插件测试有参考价值） |

**建议的自研分支命名（不污染上游分支）**
```
wngln/i18n            ← 汉化 + 多语言（从 5.3.x 切出）
wngln/usb2830         ← 采集插件与振动分析扩展（从 5.3.x 切出）
wngln/dll-encoding    ← 那处 environment.py 修复（已建立，可独立成一个可提 upstream 的小 PR）
```

> **建议的切出关系**：`wngln/i18n` 与 `wngln/usb2830` **从 `wngln/dll-encoding` 切出**（或从 `5.3.x` 切出后 `cherry-pick 9c8105cb`）。
> 原因：该修复是"中文路径下能用"的前提，若产品分支不含它，初始化会被吞掉（见 §4.1 实测）。

### 1.3 与"放弃旧开发库"的关系

| 旧资产 | 处置 |
|---|---|
| `D:\...\PyMoDAQ`（旧克隆，含未提交修复） | **先迁移再删**：`environment.py` 编码修复（见 §4.1） |
| `D:\...\PyMoDAQ-i18n`（上一版副本） | 可删（其内容 = 上游 5.3.x，无独有资产） |
| `D:\...\pymodaq_zh`（运行时中文层，650 条词典） | **保留**：它是汉化的译稿种子与兜底层（§2.4） |
| `D:\...\VibrationAnalyzer\hardware\usb2830` | **保留**：USB2830 的 ctypes 驱动与结构体定义直接迁移到插件包（§3.3） |

---

## 2. 汉化方案（含多语言）

### 2.1 目标与验收（可量化）

| 编号 | 目标 | 验收 |
|---|---|---|
| G1 | 完全汉化 | `pylupdate6` 台账中白名单外未译条目 = 0；`selfcheck --all-extensions` 全部界面 100% |
| G2 | 多语言 | 新增语言只加语言包、不改代码；`--lang` / 配置 `gui.style.language` 生效；缺失回退英文 |
| G3 | 可跟随上游 | 分支只做字符串包装，rebase 冲突局限于 `tr()` 行 |
| G4 | 零行为回归 | 占位符数量/顺序一致；上游 pytest 全绿（当前基线 512 passed / 3 skipped） |

**白名单（不翻译）**：插件与模块标识（`Mock`/`DAQ0D`/`Det1D`）、库名与型号（`h5py`/`zlib`）、单位与数据轴标签（`Samples (S)`）、日志与异常文本、配置文件键、命令行帮助。

### 2.2 架构：三层

```
界面文本
  ├─ L2 应用语言包 pymodaq_zh_CN.qm / pymodaq_en.qm ← 源码 tr() 提取（474 标题 + 396 动作 + …）
  ├─ L3 运行时语言包 zh_CN.toml / en.toml           ← 插件文本、f-string 拼接、pyqtgraph 文本
  └─ L1 Qt 语言包 qtbase_zh_CN.qm                   ← 标准对话框与按钮（PyQt6 自带，已验证存在）
```

命中顺序：L2 → L3 → 原文。（L3 沿用现 `pymodaq_zh.translate()` 的精确匹配 + 冒号/省略号归一化）

### 2.3 工作量（基于实测字符串规模）

| 阶段 | 内容 | 工作量 |
|---|---|---|
| P0 ✅ | 新基线就位（fork + 本地检出 + 双 remote） | 已完成 |
| P1 | ✅ **已完成**：i18n 核心 + Qt 接入 + tr() 示范与语言包（见 2.6） | 0.5–1 人日 |
| P2 | `codemod`（AST 包装 119 个文件）+ `audit`（台账/占位符校验）脚本；分批提交 | 1 人日 |
| P3 | 译稿：650 条词典转种子 → 补齐 1177 条；人工处理 60 处 f-string | 3–5 人日 |
| P4 | L3 语言包化（TOML）+ 插件文本兜底 + 插件汉化模板 | 1–2 人日 |
| P5 | 语言切换（先重启切换）、打包、CI 门禁（未译条目不得增加） | 1–2 人日 |

### 2.4 复用已有资产

| 资产 | 用途 |
|---|---|
| `pymodaq_zh` 650 条词典 | `.ts` 译稿种子（省掉重复翻译） |
| `pymodaq_zh.selfcheck` | 验收工具：逐界面/逐扩展收割漏译 + 截图（可加 `--lang`） |
| `pymodaq_zh.debug` | 调试启动器（异常钩子、环境诊断、解释器自愈），可用 `PYMODAQ_PYTHON` 指向新基线 venv |

### 2.5 `lrelease` 缺口

实测：PyQt6 只有 `pylupdate6`，**没有 `lrelease`**（`.ts` 需编译成 `.qm`）。三条路径：

| 路径 | 说明 |
|---|---|
| ① 装 `pyside6-essentials` 取 `pyside6-lrelease`（推荐） | 与 Qt6 版本匹配；只调用命令行工具，不导入其模块，不影响 PyQt6 运行。体积约 70 MB（**推断**，未下载核实） |
| ② 安装 Qt6 官方工具 | 体积大、需官方安装器 |
| ③ 自研纯 Python `ts→qm` 转换（100–150 行） | 离线可用；QM 格式细节有风险（**推断**）；作为备选 |

**P1 实际采用的方案**：走"**语言包 + Python `QTranslator`**"——`.ts` 仍是作者格式
（`pylupdate6` 提取、Qt Linguist 可编辑），编译目标是 **TOML 语言包**，
运行时由 `pymodaq_gui.i18n.PackTranslator`（覆盖 `QTranslator.translate`）查表。
因此**完全不依赖 lrelease**，也就不必再解决它的获取问题。

### 2.6 P1 已完成的实测记录（分支 `wngln/i18n`，已推送）

| 提交 | 内容 |
|---|---|
| `8a82bf06` | `pymodaq_utils/i18n.py`：语言解析（env `PYMODAQ_LANG` > 配置 `[i18n] language` > 系统区域 > `en`）、TOML 语言包加载/查找（contexts → general → 回退语言）、命令行 `extract/pack/status`；配置模板加 `[i18n]`；入口脚本 `pymodaq-i18n` |
| `f77d47dc` | `pymodaq_gui/i18n.py`：`PackTranslator` + `install_translators()`（同时装 Qt 自带 `.qm`）；在 `mkQApp()` 里安装，**所有 GUI 入口自动生效** |
| `8960d062` | 示范 `tr()` 包装（启动器 3 条）+ 生成 `pymodaq_zh_CN.ts` + 编译 `pymodaq_zh_CN.toml` |
| `6b796eec` | `pack` 支持从文件名推断语言（`pylupdate6` 生成的 `.ts` **不带** `language` 属性） |

**端到端验证（关键：同时设 `PYMODAQ_ZH=0` 关掉运行时词典层 L3，中文只可能来自 L2）**

| 检查 | 结果 |
|---|---|
| `core.lookup('Launcher','launcher')` | `启动器` ✅ |
| `QCoreApplication.translate('launcher','Launcher')`（经 `mkQApp` 装表后） | `启动器` ✅ |
| `get_action('launch_dashboard').text()` | `启动空仪表板` ✅ |
| `get_action('launch_h5browser').text()` | `启动 H5 浏览器` ✅ |
| `get_action('launch_viewer').text()`（未包装） | 仍为英文 ✅（反证：翻译来自 `tr()` + 语言包） |

**P1 期间发现的两个待处理点（供 P2/P3 使用）**

1. `CustomApp` 用 `self.title` 设置窗口标题（`pymodaq_gui/utils/custom_app.py:175`、`:178`），
   未经 `tr()` → 标题不会被翻译。P2 的 codemod 需要覆盖这类"**标题来自变量**"的写法
   （不只是字符串字面量）。
2. `pylupdate6` 生成的 `.ts` 不带 `language` 属性 → `pack` 已能从文件名推断，但**若用
   Qt Linguist 翻译并保存**，属性会被写入，两种来源都要兼容（已实现）。

---

### 2.7 P2 已完成的实测记录（分支 `wngln/i18n`，已推送）

| 提交 | 内容 |
|---|---|
| `de6d0b42` / `155ecb8e` | `tools/i18n/i18n_codemod.py`（AST 外科式改写）+ `tools/i18n/i18n_audit.py`（台账/占位符/门禁） |
| `8b8a379f` / `25f584ba` | 包装 `pymodaq_gui`（585 条） |
| `5ea7439f` / `7bffc489` | 包装 `pymodaq`（216 条） |
| `6418e859` | 提取改为"镜像到临时目录"（绕过 pylupdate6 崩溃） |
| `f87b3191` | 生成 zh_CN 词条台账（`pymodaq_zh_CN.ts` 214 条、`pymodaq_gui_zh_CN.ts` 574 条） |
| `b448fe48` | 改写工具支持 `--max-targets`（二分定位/分批试点） |

**实测结果**：包装 801 条 / 77 个文件 / 822 行改动；**改写前后同一套测试结果完全一致**
（`204 passed, 1 xpassed`）；`compileall` 通过；`git diff` 无换行符 churn。
当前台账：**788 条待译（pymodaq 214 + pymodaq_gui 574），已译 3 条（0.4%）**；
另有 70 处 f-string + 6 处含占位符需人工处理。

**P2 期间踩到的四个坑（都已修，值得记录）**

1. **字符/字节偏移混用**：`ast` 的 `col_offset` 是 UTF-8 **字节**偏移，而按字符长度累加行首偏移 →
   凡是"字符串前面有非 ASCII 字符"的行都会被写坏（实测把文件写成了 Git 认定的`非文本`，整文件伪变更）。→ 全程按字节切片。
2. **`self.tr` 有前提**：PyMoDAQ 里不少类**不继承 QObject**（如 `ParameterTreeWidget`）→ `AttributeError`。
   → 统一改用 `QtCore.QCoreApplication.translate(上下文, 文案)`（context 语义与 `QObject.tr` 相同）。
3. **`from qtpy.QtCore import X` 不绑定名字 `QtCore`** → 生成的调用会 `NameError`。
   → 必须按"名字 `QtCore` 是否在模块顶层被绑定"来判断是否注入 import（已实现 `has_qtcore_name`）。
4. **`pylupdate6` 6.11.0 崩溃**：在本仓库路径下处理"已改写"的文件会抛内部错误
   （同一字节放到临时目录就正常，ASCII 与中文路径均已验证）→ 提取改为**先把包源码镜像到临时目录**、
   在那里跑 pylupdate6，再把 `.ts` 合并回仓库，并还原 `location` 路径。**这是 PyQt 工具的 bug，值得上报**。

**P2 的两个剩余项已清（本轮完成）**

| 项 | 做法 | 实测 |
|---|---|---|
| ✅ 474 条**参数标题** | 不逐条改字典，改为在**构建参数树时集中翻译**：`pymodaq_gui.i18n.translate_params/translate_param/translate_title`（只翻 `title`/`tip`，不动 `name`/`limits`），接线 4 处（`ParameterManager` 建树、`create_parameter`、`parameter.utils` 反序列化、`settings_manager.populate_from_file`）；提取端新增 `collect_static_messages`/`merge_static_messages` 把这类静态文案并入 `.ts`（`general` 上下文） | 关闭兜底词典层（`PYMODAQ_ZH=0`）后，真实 DAQ_Viewer 设置树：`main_settings` 标题 = **主设置：**、`wait_time` = **等待时间(ms)：** |
| ✅ 70 处 f-string | 改写工具新增 f-string 通道：`f"...{expr}..."` → `translate(上下文, 模板).format(expr...)`（花括号自动转义、格式说明符保留为占位符；`!r`/嵌套格式/调试语法留给人工） | **70/70 全部自动转换**，0 处需人工；19 个文件、118 行；`compileall` 通过 |

**当前台账：1282 条**（pymodaq 484 + pymodaq_gui 798，已含参数标题与 f-string 模板），已译 6 条；
回归：**323 passed**（唯一失败 `test_icon_qt` 为既有 Windows 环境问题，已用未改写版本对照确认）。

**仍待处理**：插件包（`pymodaq_plugins_*`）自带文案 —— 属 L3 运行时语言包与插件自带语言包的范畴。

---

## 3. USB2830 振动采集插件方案（实机 + 模拟）

### 3.1 目标

1. 一套插件代码同时支持 **实机** 与 **模拟**：无硬件时也能开发/联调/跑自动化测试；
2. 采集数据进入 PyMoDAQ 标准数据模型（`DataToExport`/`DataRaw`/`Axis`，带单位），可直接用 Dashboard、H5 保存、扫描、记录等既有能力；
3. 为后续振动分析（波形/频谱/1X/阶次/趋势）留出标准扩展点，而不是另起一套应用框架。

### 3.2 交付物结构（新仓库）

```
pymodaq_plugins_usb2830/                 # 独立插件包（PyMoDAQ 架构要求硬件支持在外部包）
├── pyproject.toml                       # 见下方"注册方式"
├── hatch_build.py                       # 可选：官方模板的构建钩子，按 [features] 自动生成 entry points
├── src/pymodaq_plugins_usb2830/
│   ├── hardware/usb2830/
│   │   ├── dll.py                       # ctypes 绑定（迁移自 VibrationAnalyzer：driver.py + structures.py）
│   │   ├── backend_base.py              # 统一后端协议：open/configure/start/read/stop/close
│   │   ├── backend_real.py              # 实机：DLL + PARA_AD
│   │   └── backend_sim.py               # 模拟：可配置多通道合成信号（1X/谐波/噪声/冲击）
│   ├── daq_viewer_plugins/plugins_1D/usb2830.py   # DAQ_Viewer_base 插件（波形）
│   ├── daq_viewer_plugins/plugins_0D/usb2830_rms.py  # 可选：RMS/1X 标量通道
│   ├── extensions/vibration_analysis.py # 振动分析扩展（CustomExt，见 3.6）
│   └── resources/config_template.toml   # 灵敏度、量程、DLL 路径等默认配置
└── tests/                               # 无硬件测试（用 PyMoDAQ 5.3 的 plugin_testing harness）
```

**插件注册方式（已实测两种，任选）**

| 方式 | 做法 | 说明 |
|---|---|---|
| A. 显式声明（最简单） | `[project.entry-points."pymodaq.instruments"]` + `[project.entry-points."pymodaq.plugins"]` | 实测 `pymodaq_plugins_mock` 的 `entry_points.txt` 就是这两个组；`daq_utils.get_instrument_plugins()` 同时查询二者（`pymodaq.plugins` 为旧命名，`pymodaq.instruments` 为新命名） |
| B. 官方模板方式 | 用 hatchling 构建钩子调用 `pymodaq_utils.resources.hatch_build_plugins.update_metadata_from_toml()`，在 pyproject 里用 `[features]` 开关：`instruments / extensions / pid_models / models / h5exporters / scanners` | 勾选 `instruments = true` 与 `extensions = true` 即自动生成 `pymodaq.instruments` / `pymodaq.extensions` / `pymodaq.plugins`；需在 pyproject 的 `[urls]` 里提供 `package-url` |

> 建议先用方式 A 跑通，再按官方模板切到 B（与生态一致，便于日后发布）。

### 3.3 实机后端（迁移现成代码，接口已实测）

现有 `VibrationAnalyzer\hardware\usb2830` 已把厂商 DLL 封装好，直接迁移：

| 层 | 现状（实测） |
|---|---|
| DLL 函数 | `USB2830_CreateDevice` / `USB2830_CreateDeviceEx` / `USB2830_ReleaseDevice` / `USB2830_InitDeviceAD` / `USB2830_ReadDeviceAD` / `USB2830_ReleaseDeviceAD` |
| 参数结构 `USB2830_PARA_AD` | `CheckStsMode, ADMode, FirstChannel, LastChannel, Frequency, InputRange, GroupInterval, LoopsOfGroup, Gains, TriggerMode, TriggerType, TriggerDir, TrigWindow, GroundingMode, ClockSource, bClockOutput` |
| 量程表 | `0: ±10 V，1: ±5 V，2: ±2.5 V，3: 0…10 V` |
| 读取约束 | 读取字数须为 `通道数 × 256` 的整数倍（现适配层按此取整） |
| 码值换算 | 现实现为 `mv = (hi-lo)/8192 × (raw & 0x1fff) + lo`（**13 位掩码**） |

> ⚠️ **待核实（推断）**：`& 0x1fff` 的位宽与刻度需按厂商手册核对（USB2830 系列不同型号位宽不同）。插件里把"位宽/满量程码值"做成参数，先用现实现对齐，再用手册/实测确定。

**插件参数（`comon_parameters` 之上追加）**：源（模拟/实机）、DLL 路径、设备号、物理通道开关、首/末通道、采样率、输入范围、触发模式、块长、灵敏度（mV/(m/s²)）、单位目标（mV/g/m·s⁻²）、是否交流耦合。

### 3.4 模拟后端（无硬件开发的关键）

| 能力 | 设计 |
|---|---|
| 信号合成 | 每通道独立配置：基频 1X（与虚拟转速联动）、谐波 2X/3X、噪声、冲击脉冲、可选 50 Hz 工频干扰 |
| 转速联动 | 提供"虚拟转速 RPM"参数与 `tacho` 通道（键相脉冲），为 1X/阶次分析提供相位基准 |
| 行为拟真 | 块长/采样率与实机一致；不做前卷积缓，便于验证实时性与丢块统计 |
| 确定性 | 固定随机种子 → 自动化测试可断言（谱峰位置、幅值） |

### 3.5 数据与线程模型（对齐 PyMoDAQ）

| 项 | 做法 |
|---|---|
| 数据载体 | 每通道一个 `DataRaw(name='AI0', data=[block], axes=[Axis('time','s',data=t)])`，装入 `DataToExport('USB2830')`；单位经灵敏度换到 `m/s**2`（或 mV/g） |
| 线程 | 插件跑在 `DetectorWorker` 的 `QThread` 内；`live_mode_available = True` 由插件连续推流，`hardware_averaging = False`（软件平均交给框架） |
| 多通道 | 用 `DataWithAxes` 的 channels 维度表达 4 通道；viewer 侧用 `Viewer1D` 的叠加/ROI/十字光标看谱峰 |
| 元数据 | 采样率、量程、灵敏度、转速写入 `DataRaw` 的 extra attributes，随 H5 一起落盘 |
| 停止 | `stop()` 立即停读并释放 AD；`close()` 释放设备句柄 |

### 3.6 振动分析扩展（同包的 Dashboard 扩展）

| 功能 | 实现要点 |
|---|---|
| 波形 / 频谱 | `DataWithAxes.ft()`（5.3 已有，轴单位自动变 `rad/s`）+ 窗函数/重叠/谱平均（自研） |
| 1X / 相位 | 与键相通道做互相关或在 1X 处取矢量（幅值+相位），输出到 0D 通道供趋势 |
| 阶次 / 瀑布 | 转速扫描（配合 `DAQ_Move` 执行器做升降速）→ 等角度重采样 → 瀑布图 |
| 趋势 / Run 管理 | 复用 `H5Saver` + `LoggerSaver`；Run 语义与基线比较自研 |
| 报告 | 先导出 H5/CSV，报告模板后续按需加 |

> 与既有 `VibrationAnalyzer` 的关系：其 `SampleFrame/ChannelMeta/MockAdapter` 思路可继续沿用，但在 PyMoDAQ 侧统一改写成 `DataToExport` 表达，避免两套数据模型。

### 3.7 验收与测试（无硬件可跑）

| 测试 | 内容 |
|---|---|
| 后端级 | 模拟后端：块长/通道数/采样率/确定性断言（`.venv` 内 pytest，无需 Qt） |
| 插件级 | 用 PyMoDAQ 5.3 的 `plugin_testing` harness + 验收 mixin：初始化→抓数→停止→关闭，不依赖真实硬件 |
| 实机级 | 手工验收清单：单通道/多通道、各量程、不同采样率、连续 10 分钟不丢块、停止/重启、异常拔插 |
| 数据级 | H5 落盘后回读校验形状/单位/属性 |

---

## 4. 本地开发调试脚本

位置：`D:\工作目录\振动诊断系统扩展方案\dev\`（**不放进 git 仓库**，保持仓库干净）。

| 脚本 | 作用 | 状态（实测） |
|---|---|---|
| `setup-dev.ps1` | 为 `PyMoDAQ-dev` 建 `.venv`（Python 3.12）+ 可编辑安装 5 个子包 + `pyqt6/debugpy/pytest/pytest-qt`，并安装中文层；幂等 | ✅ 已执行：3.12.13 + pymodaq 5.3.2 + PyQt6 6.11.0 + pyqtgraph 0.14.0 + pymodaq-zh 0.1.0 |
| `run.ps1` | 启动界面（`launcher`/`dashboard`/`viewer`/`move`/`scan`/`logger`/`sequencer`/`h5browser`） | ✅ 已就位（与已验证的 `pymodaq_zh` 启动方式一致） |
| `debug.ps1` | 调试启动：复用 `pymodaq_zh.debug`（faulthandler + 异常钩子 + 环境诊断 + 解释器自愈），并设 `PYMODAQ_PYTHON` 指向新 venv；支持 `-DebugPort/-IsolatedConfig/-NoEnvBackup/-LogTail` | ✅ 已执行 `-PrintEnv`：报告新 venv、PyMoDAQ 5.3.2（新路径）、11 个插件 |
| `status.ps1` | 体检：分支、与基线对比、venv/解释器、已装版本与路径、插件数、日志路径（可 `-LogTail N`） | ✅ 已执行：正确报出 `wngln/dll-encoding` 领先 `upstream/5.3.x` 1 个提交 |
| `patches\0001-*.patch` | 编码修复的可复用补丁 | ✅ 已生成 |
| `vscode-launch-snippet.json` | 3 条 VS Code 调试配置（启动器/仪表板/附加），追加到 `.vscode/launch.json` | 待你决定是否写入（不改动你原有 3 条配置） |

### 4.1 必须迁移的一处修复（✅ 已完成，`9c8105cb`）

旧库工作区里有一处**未提交**修复：`packages/pymodaq_utils/src/pymodaq_utils/environment.py`

| 改动 | 内容 |
|---|---|
| `PythonEnvironment.save()` | `open(self._path, 'w')` → `open(self._path, 'w', encoding='utf-8')` |
| `_from_stream()` | 解码加容错：`l.decode('utf-8', errors='replace')` |
| 为什么必须修 | 备份文件写入用系统默认编码（中文 Windows = cp936），读取按 UTF-8；安装路径含中文时第二次导入 `pymodaq` 必然 `UnicodeDecodeError`，且被 `pymodaq/__init__.py` 的 try 吞掉 → `CONTROL_MODULES` 未定义 → Dashboard 无法导入（已实测复现） |

计划：在新基线里作为 `wngln/dll-encoding` 分支的**一次独立提交**，同时准备一个可提 upstream 的最小 PR。

**已完成（实测）**

| 项 | 值 |
|---|---|
| 分支 | `wngln/dll-encoding`（从 `5.3.x` 切出） |
| 提交 | `9c8105cb` fix(utils): write environment backup as UTF-8 and tolerate bad bytes when reading |
| 补丁文件 | `dev\patches\0001-fix-utils-write-environment-backup-as-UTF-8-and-tole.patch`（可 `git am` 复用） |
| 验证 | 修复前：读旧备份文件抛 `UnicodeDecodeError`（新基线实测复现）；修复后：`OK 20261011061440_environment.txt 包数: 0` |

**附带发现（实测，影响配置）**：调试启动器的 `--no-env-backup` 只改内存配置，但 PyMoDAQ 初始化末尾会调用 `config.save()`，因此该项已被**持久化**到

```toml
# C:\Users\wngln\.pymodaq\config\utils.toml
[backup]
keep_backup = false
```

这解释了为什么新基线在不加该开关时也没报错（备份步骤被跳过了）；**手动验证已确认 bug 仍然存在**（直接用未打补丁的代码读旧文件 → `UnicodeDecodeError`）。
建议：保持 `false`（多分支并存时更稳），如果固定使用 `wngln/dll-encoding` 分支，可改回 `true` 让备份功能恢复。

---

## 5. 迁移与清理清单（需你确认后执行）

| # | 动作 | 说明 |
|---|---|---|
| 1 | 迁移 `environment.py` 修复到 `PyMoDAQ-dev` | ✅ 已完成（`wngln/dll-encoding` / `9c8105cb` / 补丁已导出） |
| 2 | 复制 `pymodaq_zh` 词典为汉化译稿种子 | 650 条 |
| 3 | 删除旧库 `D:\...\PyMoDAQ` | 确认后执行；届时其 venv 也会一并删除 |
| 4 | 删除 `D:\...\PyMoDAQ-i18n` | 内容与上游一致，无独有资产 |
| 5 | 保留 `D:\...\VibrationAnalyzer`（USB2830 驱动与算法参考） | 采集插件方案依赖其 ctypes 封装 |
| 6 | 可选：删除 `D:\...\PyMoDAQ\.venv` 之外的历史备份目录 | 由你决定 |

---

## 6. 需要你确认的 5 个决策点

1. 分支命名：`wngln/i18n`、`wngln/usb2830`、`wngln/dll-encoding` 是否 OK？
2. 工具链：是否允许联网安装 `pyside6-essentials` 以取得 `lrelease`？
3. 语言范围：先 `en` + `zh_CN`，还是同时纳入 `ja`/`de`？
4. 是否向上游提 PR（`environment.py` 修复、i18n 骨架）？
5. 清理：是否现在删除旧库 `PyMoDAQ` 与 `PyMoDAQ-i18n`（§5 第 3、4 项）？
