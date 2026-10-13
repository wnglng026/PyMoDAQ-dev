# AGENTS.md — 本 fork 给 AI 助手的约定

上游 PyMoDAQ 的说明见 [`CLAUDE.md`](CLAUDE.md)（仓库结构、安装、测试命令，仍然有效）。
本文只写**本 fork 追加的约定**。工作语言：**简体中文**（文档、提交信息、注释）；代码标识符保持英文。

## 1. 仓库与分支

| 项 | 值 |
|---|---|
| `origin` | `https://github.com/wnglng026/PyMoDAQ-dev`（我们的 fork，**默认分支 `5.3.x`**） |
| `upstream` | `https://github.com/PyMoDAQ/PyMoDAQ`（**只读**，push 已禁用；官方引用走 `refs/remotes/official/*`） |
| 自研分支 | `wngln/i18n`（汉化）、`wngln/usb2830`（采集插件）、`wngln/dll-encoding`（编码修复） |

**分支纪律**

- AI 助手（ChatGPT 网页版 / Codex 等）只在 `wngln/chatgpt-<主题>` 上提交并提 **Draft PR**；
  **不要**直接推 `5.3.x`、`dev`、`wngln/i18n`、`wngln/usb2830` —— 这些由本地验证后合并。
- 一次任务 = 一个分支 = 一个主题；不要顺手重构无关代码。

## 2. 先读这些（上下文，省得你猜）

- [`docs/zh/README.md`](docs/zh/README.md) —— 中文文档索引与关键事实速查
- [`docs/zh/PyMoDAQ汉化-进展与交接.md`](docs/zh/PyMoDAQ汉化-进展与交接.md) —— 当前进度 + **五条硬约束** + 剩余待办
- [`docs/zh/PyMoDAQ-ChatGPT网页版协作方案.md`](docs/zh/PyMoDAQ-ChatGPT网页版协作方案.md) —— 协作流程、任务卡与回传模板、验收清单、踩坑清单
- [`docs/zh/PyMoDAQ-dev-代码库分析.md`](docs/zh/PyMoDAQ-dev-代码库分析.md) —— 结构分层与 i18n 落点（**顶部有勘误，以勘误为准**）

## 3. i18n 改动的五条硬约束（踩过坑，务必遵守）

1. **不翻译参数的 `name`**（它是设置持久化的键）；
2. **不翻译 `limits`**（取值会写进配置文件）；
3. 改写源码字符串时**按字节做偏移运算**（`ast.col_offset` 是 UTF-8 字节偏移，与字符混用会写坏含非 ASCII 的行）；
4. **统一用 `QCoreApplication.translate(上下文, 文案)`**，不要用 `self.tr`（PyMoDAQ 里有非 QObject 类）；
5. 注入 `QtCore` import 前按"名字是否已绑定"判断（`from qtpy.QtCore import X` 不会绑定 `QtCore` 这个名字）。

翻译流水线（**顺序不能换**）：

```bash
python -m pymodaq_utils.i18n extract      # 提取（内部走临时目录镜像，绕过 pylupdate6 在本仓库路径下的崩溃）
python tools/i18n/i18n_seed.py --map tools/i18n/zh_map.toml
python -m pymodaq_utils.i18n pack         # .ts -> TOML 语言包
python tools/i18n/i18n_audit.py           # 台账：未译必须为 0、占位符必须一致
```

- **不要手工编辑 `resources/translations/*.toml`**（`pack` 会覆盖）；改 `.ts` 或 `tools/i18n/zh_map.toml`。
- 有意保留英文的条目登记在 `tools/i18n/allow_english.txt`（标识符、数据值、`examples/` 示例、部分演示文案）。

## 4. 自检（提 PR 前至少跑一遍）

```bash
python tools/i18n/i18n_audit.py                                  # i18n 台账
python -m pytest packages/pymodaq_gui/tests/managers -q           # 轻量回归
python -m pytest packages/pymodaq/tests packages/pymodaq_gui/tests -q -m "not leco"   # 较全（约 4 分钟）
```

已知环境限制：本机缺 `PyQt6-WebEngine`，`packages/pymodaq_gui/tests/editor_test.py` 无法收集，请 `--ignore` 跳过，不要试图修它。

## 5. 环境注意事项

- 仓库**以 CRLF 检出**（`.gitattributes` = `* text=auto`）。批量改写时保持原换行符，避免产出"整文件重写"的 diff。
- `subprocess` 读取工具输出要显式 `encoding='utf-8'`（本机是 GBK 控制台环境）。
- 可编辑安装是**路径绑定**的：新建 worktree 后要单独 `python install-packages.py -d`（或用 `dev/setup-dev.ps1 -RepoRoot <worktree>`）。
- 中文路径下必须带 `pymodaq_utils/environment.py` 的编码修复（`9c8105cb`，只在 `wngln/*` 分支）；从 `5.3.x` 切分支做中文路径实验时先 cherry-pick。

## 6. 提 PR 的自述要求

PR 描述里必须写清：**改了哪些文件 / 你的判断依据 / 你无法验证的部分**。
本仓库的产出默认是"未验证"——能否运行由本地（或 CI）判定，不要把推断写成结论。
