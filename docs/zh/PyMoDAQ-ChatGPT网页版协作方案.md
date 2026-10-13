# PyMoDAQ-dev · ChatGPT 网页版协作 + 本地调试 方案

> 目标：用 **ChatGPT 网页版**在 GitHub 上开发，**本机**负责拉取、运行、验收与反馈。
> 基线（2026-10-13 实测）：本地两个 worktree —— `PyMoDAQ-dev`（分支 `5.3.x` @ `629f3b71`，干净）
> 与 `PyMoDAQ-dev-i18n`（分支 `wngln/i18n` @ `9e295aa3f`，干净）；远端 `origin` = `wnglng026/PyMoDAQ-dev`，
> **fork 的默认分支 = `5.3.x`**（`git ls-remote --symref origin HEAD` 实测）；`stash` 两个 worktree 均为空。
> 标注约定：**实测** = 本机执行过的命令结果；**推断** = 经验判断，需验证。

---

## 0. 结论速览

| 事项 | 结论 |
|---|---|
| 分工 | ChatGPT 网页版**只写文件/开分支/开 PR**（它不能运行、不能装依赖）；**本机是唯一的"能跑"环节**，负责运行、验收、复现、回传报错 |
| 上下文怎么给 ChatGPT | 三份文档 + 本方案已写入仓库 `docs/zh/`（默认分支 `5.3.x` 上就有），ChatGPT 开仓即可读，不用每次粘贴长文 |
| 分支纪律 | ChatGPT 只在 `wngln/chatgpt-<主题>` 上干活；`5.3.x`（基线）、`dev`、`wngln/i18n`（汉化）**只由本地合并** |
| 本地入口 | 复用现有 `dev\*.ps1`；新增一个"拉取 ChatGPT 分支并验收"的脚本（§4.3 给了现成实现） |
| 一次一步 | 任务卡写死"允许改哪些文件"；一次只推进一小步，避免网页版顺手大重构 |
| 让网页版也能看到"红/绿" | 把 i18n 台账门禁 + pytest 接进 GitHub Actions（§6），PR 自动跑，ChatGPT 能直接读结果 |
| 已知坑 | 换行符（LF/CRLF）、`pylupdate6` 在本仓库路径下崩溃、`install-packages.py` 顺序、worktree 与分支一一对应（§5） |

---

## 1. 先划清能力边界（这决定流程怎么设计）

| 能力 | ChatGPT 网页版 | 本机（Codex / 你的终端） |
|---|---|---|
| 读仓库文件 | ✅（GitHub 连接器 / 直接浏览） | ✅ |
| 改文件、建分支、开 PR | ✅ | ✅ |
| 运行 `pytest` / 起 GUI / 连硬件 | ❌ | ✅ |
| 装依赖、建 venv | ❌ | ✅ |
| 判断"改完还能不能跑" | ❌（只能靠 CI 或你回传） | ✅ |
| 保存/读取 `~/.pymodaq` 配置、看真实报错栈 | ❌ | ✅ |

**结论**：网页版产出的东西**默认是"未验证"**。凡是"能不能跑"的结论，必须由本机给出；这也是为什么 §6 的 CI 门禁值得做——它给网页版唯一一条"自动红/绿"反馈路径。

---

## 2. 三种接入方式（选一种或组合）

| 方式 | 做法 | 优点 | 代价 | 建议 |
|---|---|---|---|---|
| **A. GitHub 网页编辑** | ChatGPT 给"改哪个文件、改成什么"，你在 GitHub 网页编辑 → 提交到 `wngln/chatgpt-xxx` 分支 | 零配置、最稳 | 手工搬运；网页编辑器容易整文件重写 | 小改动/文档首选 |
| **B. ChatGPT 的 GitHub 连接器（或 Codex 云端）** | 授权后 ChatGPT 直接读写仓库、建分支、开 PR | 自动化程度高 | 需要授权；仍不能跑测试 | 批量改写首选，配合 §6 CI |
| **C. 纯对话 + 补丁文本** | 把相关文件贴给 ChatGPT，让它**只输出 unified diff**，本机 `git apply` 后跑验收 | diff 最小、最容易审 | 需要本地一次 apply | 高风险改动首选（例如 i18n 硬约束相关的） |

**推断（需你验证）**：你打算走的多半是 B；B 的前提是仓库**默认分支上就有上下文文档**，否则 ChatGPT 一开仓看到的是上游 PyMoDAQ 的英文文档，会按上游约定行事（它一定会忽略你本地的 `wngln/*` 分支语义）。

---

## 3. 标准工作流（7 步）

```text
①本地写任务卡  →  ②ChatGPT 在 wngln/chatgpt-<主题> 上改 →  ③开 PR（草稿）
        ↑                                                        ↓
⑦通过→本地合并到 wngln/i18n 或 5.3.x 并推送      ④本地 fetch + 切到该分支
        ↑                                                        ↓
        ⑥把"命令 + 原文报错"回传 ChatGPT  ←  ⑤跑验收清单（§5）
```

| 步 | 谁做 | 具体动作 | 命令/产物 |
|---|---|---|---|
| ① | 你/ChatGPT | 写任务卡（模板见 §7.1），明确目标、允许改的文件、不许动的东西 | 一张卡 = 一个分支 |
| ② | ChatGPT | 只改任务卡范围内的文件，提交到 `wngln/chatgpt-<主题>`（**不推 5.3.x / dev / wngln/i18n**） | 分支 |
| ③ | ChatGPT | 开 **Draft PR**，PR 里贴任务卡 + 自述"我改了哪些文件、我没验证什么" | PR |
| ④ | 本机 | `git fetch` + 在"CC worktree"里切到该分支（§4.3 脚本） | 一个专用于 CC 的 worktree |
| ⑤ | 本机 | 跑 §5 验收清单（按改动类型选行） | 日志 |
| ⑥ | 本机 | 回传：**命令 + 完整原文报错 + 环境版本**，一次一小步 | 聊天消息 |
| ⑦ | 本机 | 验收通过 → 合并到 `wngln/i18n`（汉化类）或 `5.3.x`（基线类）→ 推送 | 提交 |

> 铁律两条：**(1) 同一分支不要两边同时改**（网页版改一半、本地也改一半，冲突极难收）；
> **(2) 一个分支只能被一个 worktree 检出**（Git 硬限制，重复 `worktree add` 会直接报错）。

---

## 4. 本地目录与脚本落点

### 4.1 建议的目录规划（实测当前状态）

| 目录 | 分支 | 用途 | 现状 |
|---|---|---|---|
| `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev` | `5.3.x` | 基线（与上游对齐，只做合并） | ✅ 已有 |
| `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-i18n` | `wngln/i18n` | 汉化/译稿工作区（**固定不切分支**） | ✅ 已有 |
| `D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-cc` | 随 ChatGPT 分支切换 | **给 ChatGPT 的分支做验收** | ⬜ 建议新建 |

为什么 CC 用一个独立 worktree、而不是每个分支建一个：editable 安装是**路径绑定**的（`.venv\Lib\site-packages\_editable_impl_*.pth` 指向具体 worktree），每个 worktree 都得建自己的 venv；用一个 CC worktree 来回 `git switch`，只需一份 venv。

### 4.2 建 CC worktree（一次性）

```powershell
$root = 'D:\工作目录\振动诊断系统扩展方案'
cd (Join-Path $root 'PyMoDAQ-dev')
git worktree add (Join-Path $root 'PyMoDAQ-dev-cc') -b wngln/cc-sandbox   # 首个 CC 分支

# 给它一份自己的 venv（复用本机 uv 的 Python 3.12；脚本已支持 -RepoRoot）
cd (Join-Path $root 'dev')
.\setup-dev.ps1 -RepoRoot (Join-Path $root 'PyMoDAQ-dev-cc')
```

> 装了 `pymodaq_zh` 中文层的那份 venv 在 `PyMoDAQ-dev-i18n`；CC 的 venv 默认不装（需要时 `setup-dev.ps1` 不带 `-NoZh` 即可，脚本默认是装）。

### 4.3 新增脚本：`dev\pull-chatgpt.ps1`（建议落地，内容可直接用）

```powershell
<#
.SYNOPSIS  把 ChatGPT（或任何人）推送的分支拉到本地 CC worktree，并做基础体检
.EXAMPLE   .\pull-chatgpt.ps1 -Branch wngln/chatgpt-usb2830
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Branch,
    [string]$Root = 'D:\工作目录\振动诊断系统扩展方案',
    [string]$Worktree = 'PyMoDAQ-dev-cc',
    [switch]$SkipFetch
)
$ErrorActionPreference = 'Stop'
$repo = Join-Path $Root 'PyMoDAQ-dev'
$wt   = Join-Path $Root $Worktree

if (-not $SkipFetch) { git -C $repo fetch --prune origin }

if (-not (Test-Path -LiteralPath $wt)) {
    git -C $repo worktree add $wt -b $Branch "origin/$Branch"
} else {
    Push-Location $wt
    try {
        git switch --discard-changes $Branch 2>$null
        if ($LASTEXITCODE -ne 0) { git switch -c $Branch "origin/$Branch" }
        else { git pull --ff-only origin $Branch }
    } finally { Pop-Location }
}

Push-Location $wt
try {
    Write-Host "`n== 分支 ==" -ForegroundColor Cyan; git branch --show-current
    Write-Host "`n== 与基线的差异 ==" -ForegroundColor Cyan
    git diff --stat "origin/5.3.x...HEAD"
    Write-Host "`n== 换行符体检（正常应为 0 条“整文件重写”）==" -ForegroundColor Cyan
    $files = git diff --name-only "origin/5.3.x...HEAD"
    foreach ($f in $files) {
        $stat = git diff --numstat "origin/5.3.x...HEAD" -- $f
        $n = ($stat -split "`t")[0..1] -join '+'
        $lines = (Get-Content -LiteralPath $f -ErrorAction SilentlyContinue).Count
        if ($lines -gt 0 -and ($n -notmatch '^-')) {
            $add = [int](($stat -split "`t")[0]); $del = [int](($stat -split "`t")[1])
            if ($add -gt $lines * 0.8 -and $del -gt $lines * 0.8) {
                Write-Host "  ⚠ 疑似整文件重写（可能是换行符）：$f  +$add/-$del（文件 $lines 行）" -ForegroundColor Yellow
            }
        }
    }
    Write-Host "`n下一步：按 §5 的验收清单跑对应命令（venv: $wt\.venv\Scripts\python.exe）" -ForegroundColor Green
} finally { Pop-Location }
```

### 4.4 已有脚本（都在 `dev\`，均支持 `-RepoRoot`）

| 脚本 | 用途 |
|---|---|
| `dev\setup-dev.ps1` | 建/重建 venv + 可编辑安装 5 个子包 + pytest（幂等） |
| `dev\run.ps1` | 启动器 / 仪表板 / 扩展 的常规启动 |
| `dev\debug.ps1` | 带异常钩子与环境诊断的调试启动 |
| `dev\status.ps1` | 分支、与 `official/*` 的差异、venv、日志体检 |
| `dev\fetch-official.ps1` | 抓官方引用到 `refs/remotes/official/*`（不占 remote 列表） |

---

## 5. 验收清单（复制即用，按改动类型选）

**通用（任何改动先跑这三条）**

```powershell
$wt = 'D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-cc'
cd $wt
git diff --stat origin/5.3.x...HEAD            # 改动范围是否与任务卡一致
.venv\Scripts\python.exe -c "import pymodaq, pymodaq_gui; print(pymodaq.__file__)"   # 能导入
.venv\Scripts\python.exe -m pytest packages/pymodaq_utils/tests packages/pymodaq_data/tests -q
```

**i18n 类改动（汉化）**

```powershell
cd 'D:\工作目录\振动诊断系统扩展方案\PyMoDAQ-dev-cc'
.venv\Scripts\python.exe tools\i18n\i18n_audit.py            # 台账：未译必须为 0、占位符一致
.venv\Scripts\python.exe -m pymodaq_utils.i18n extract       # 提取（走镜像，别绕过）
.venv\Scripts\python.exe tools\i18n\i18n_seed.py --map tools\i18n\zh_map.toml
.venv\Scripts\python.exe -m pymodaq_utils.i18n pack
$env:PYMODAQ_ZH='0'; $env:PYMODAQ_LANG='zh_CN'               # 只看 L2（源码 tr），排除兜底词典
..\dev\debug.ps1 launcher -RepoRoot .
```

**GUI 能启动 / 界面文案**

```powershell
..\dev\debug.ps1 dashboard -RepoRoot .      # 异常钩子会打印 traceback
..\dev\debug.ps1 scanner   -RepoRoot .
```

**插件类（USB2830 等）**

```powershell
.venv\Scripts\python.exe -m pytest <插件包>/tests -q          # 先用模拟后端
# 实机前先确认模拟后端能让"扫描"全链路跑通（方案见 PyMoDAQ-dev-方案.md §3）
```

**合并前（本地把关）**

```powershell
git -C $wt log --oneline origin/5.3.x..HEAD     # 提交是否干净、消息是否可读
git -C $wt diff origin/5.3.x...HEAD --stat | Select-Object -Last 5
```

---

## 6. 让网页版也能看到"红/绿"：CI 门禁（建议下一步就做）

网页版跑不了测试，但 GitHub Actions 能跑。建议加一个 `.github/workflows/i18n-audit.yml`：

```yaml
name: i18n audit
on:
  pull_request:
  workflow_dispatch:
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: install
        run: pip install -e packages/pymodaq_utils
      - name: audit（未译 0 / 占位符一致 / 覆盖率门禁）
        run: python tools/i18n/i18n_audit.py --fail-under 100
```

> 注意：`i18n_audit.py` 的 `--fail-under` 只是覆盖率门禁；它**不需要** GUI 依赖，所以 CI 里很轻。
> 真正的 `pytest`（GUI 相关）已在仓库既有的 `tests-*.yml` 里，PR 会跑——这也是网页版唯一能看到的自动反馈。

---

## 7. 模板（直接复制）

### 7.1 任务卡模板

```text
【任务卡】<一句话目标>
仓库：wnglng026/PyMoDAQ-dev      基线分支：5.3.x
工作分支：wngln/chatgpt-<主题>   （不要直接改 5.3.x / dev / wngln/i18n）

允许改动的文件（严格清单）：
  - packages/.../xxx.py
  - tools/i18n/zh_map.toml
不要改：其它任何文件；尤其不要动参数定义的 name / limits，不要重排/格式化无关代码

必须遵守：
  - 只做本任务卡描述的事，不要顺手重构
  - 保持文件换行符与现有一致（本仓库 CRLF 检出）
  - i18n 相关：统一用 QCoreApplication.translate(上下文, 文案)，不要用 self.tr

完成标准（我本地会用这些命令验收）：
  - python tools/i18n/i18n_audit.py   → 未译 0、占位符一致
  - pytest <路径> -q                  → 全绿

交付：PR（Draft）+ 说明"改了哪些文件 / 你验证了什么 / 你没法验证什么"
```

### 7.2 给 ChatGPT 的开场 prompt 模板

```text
你在 https://github.com/wnglng026/PyMoDAQ-dev 上工作，这是 PyMoDAQ 的二次开发 fork。
先读这几份文档再动手（默认分支 5.3.x 上就有）：
  docs/zh/PyMoDAQ-dev-代码库分析.md      —— 仓库结构、依赖分层、i18n 落点（顶部有勘误，以勘误为准）
  docs/zh/PyMoDAQ-dev-方案.md            —— 汉化 / USB2830 插件 / 本地调试脚本方案
  docs/zh/PyMoDAQ汉化-进展与交接.md      —— 当前进度、五条硬约束、剩余待办
  docs/zh/PyMoDAQ-ChatGPT网页版协作方案.md —— 我们的协作流程与验收清单

约束：
1) 只在分支 wngln/chatgpt-<主题> 上提交，不要直接改 5.3.x / dev / wngln/i18n；
2) 你的产出我无法运行，请**严格**按任务卡的文件清单改动，不要顺手重构；
3) 每次只推进一小步，改完告诉我：改了哪些文件、你的推断、你需要我跑哪条命令；
4) 遇到报错，先要我把 **完整原文报错** 贴给你，不要猜。
```

### 7.3 回传格式模板（本地 → ChatGPT）

```text
【验收结果】分支 wngln/chatgpt-xxx @ <sha>
环境：Windows / Python 3.12.13 / PyQt6 6.11.0 / PyMoDAQ 5.3.2（editable）
命令：<完整命令>
结果：<通过 / 失败>
报错原文：
<原样粘贴，不要改写>
我的判断：<是环境问题还是代码问题；不确定就说不确定>
```

---

## 8. 踩坑清单（多数是实测踩过的）

| # | 坑 | 现象 | 对策 |
|---|---|---|---|
| 1 | **换行符** | 仓库以 CRLF 检出（`.gitattributes` = `* text=auto`，`core.autocrlf=true`）；网页版编辑可能整文件变 LF → diff 显示"整文件重写" | 合并前看 `git diff --numstat`；异常就 `git config core.autocrlf true` 后重新检出该文件 |
| 2 | **同一分支双检出** | `worktree add` 报 "already checked out" | CC worktree 与 CC 分支一一对应；切换用 `git switch`（§4.3 脚本已处理） |
| 3 | **`pylupdate6` 崩溃** | 在仓库路径下处理已改写的文件会抛内部错误（同字节放临时目录正常） | 提取必须走"镜像到临时目录再合并 `.ts`"（`pymodaq_utils.i18n extract` 已内置，别绕过） |
| 4 | **`subprocess` 读输出** | 本机是 GBK 环境，读工具输出会 `UnicodeDecodeError` | 显式 `encoding='utf-8'` |
| 5 | **中文路径** | `pymodaq_utils/environment.py` 备份文件编码 bug → 中文路径下第二次导入 `pymodaq` 崩 | 该修复只在 `wngln/*` 分支（`9c8105cb`）；CC worktree 从 `5.3.x` 切出时**要么基于 `wngln/i18n` 切，要么先 cherry-pick** |
| 6 | **`~/.pymodaq` 权限** | 沙箱/受限环境里写不进去 → 一堆 `PermissionError` 噪音 | 跑 GUI 用 `dev\debug.ps1`（它会诊断）；必要时给该目录写权限 |
| 7 | **editable 安装路径绑定** | 新 worktree 里 `import pymodaq` 找不到新代码 | 每个 worktree 单独 `setup-dev.ps1 -RepoRoot`（§4.2） |
| 8 | **网页版"顺手重构"** | PR 里出现与任务无关的大面积改动 | 任务卡写死文件清单 + §6 CI + 本地 `git diff --stat` 把关 |
| 9 | **`.ts` ↔ `.toml`** | 手工改 `.toml` 会被下一次 `pack` 覆盖 | 改 `.ts` 或 `tools/i18n/zh_map.toml`，然后 extract/seed/pack |

---

## 9. 本轮已落地的准备（实测）

| 项 | 状态 |
|---|---|
| 三份文档写入仓库 `docs/zh/`（默认分支 `5.3.x` 与 `wngln/i18n` 都有） | ✅ `wngln/i18n` = `ee3554894`、`5.3.x` = `d5b6b3b44`（已推送） |
| 本方案 `docs/zh/PyMoDAQ-ChatGPT网页版协作方案.md` | ✅ 同上两个提交 |
| 仓库根 `AGENTS.md`（给 AI 助手的仓库约定入口） | ✅ 同上两个提交 |
| `docs/zh/README.md`（索引 + 与工作区母本的同步方法） | ✅ 同上两个提交 |
| 过期结论更正（"汉化 WIP 在 stash 里"、"旧库地址"、"必须迁移的修复"） | ✅ 已改，避免 ChatGPT 按错前提开工 |
| `dev\pull-chatgpt.ps1` 落地 | ✅ 已落地（与 §4.3 同款：语法检查通过；用不存在的分支实测了"早退不建目录"路径。**happy path 未实测**——需要真实 ChatGPT 分支才能验） |
| CC worktree `PyMoDAQ-dev-cc` + 独立 venv | ⬜ 待你确认（§4.2，一次 `worktree add` + 一次 `setup-dev.ps1`，约几分钟） |
| `.github/workflows/i18n-audit.yml` | ⬜ 待你确认（内容见 §6） |
| `dev\` 脚本是否搬进仓库（让 ChatGPT 能读/改） | ⬜ 待你决定（搬的话建议放 `tools/dev/`，脚本已支持 `-RepoRoot`） |

---

## 10. 需要你拍板的 3 件事

1. **ChatGPT 走哪种接法**：A 网页编辑 / B GitHub 连接器 / C 补丁文本？（我建议 **B + C**：批量改走 B，高风险改走 C）
2. **CC worktree 建在哪个盘/目录、是否要我顺手建好**（§4.2，一次 `worktree add` + 一次 `setup-dev.ps1`）
3. **要不要现在接 CI 门禁**（§6）+ 建 CC worktree（§4.2）——`dev\pull-chatgpt.ps1` 已落地，这两项做完网页版协作才算闭环

---

## 11. 在线写入被拒（HTTP 403）怎么处置

**现象**：ChatGPT 网页版在 `wngln/i18n` 上写文件返回
`403 Resource not accessible by integration`，没有产生提交。

**这是哪一类错误（判断，附依据）**：`Resource not accessible by integration` 是 **GitHub App
安装令牌（installation token）**的标准错误文案——App 装上了，但**没拿到 `Contents: write`**，
或者目标仓库**没被纳入该 App 的安装范围**（组织仓库还可能被组织策略限制）。
它**不等于**"你本人没有仓库权限"：本地 `git push origin wngln/i18n` 一直是通的（本文件所在的
`faf443948`/`cf60ba803` 等都是这么推上去的），说明服务端并没有拒绝写入。

**恢复权限（只能在浏览器里点，本机代不了）**

| 步 | 位置 | 要做什么 |
|---|---|---|
| 1 | ChatGPT → 设置 → 已连接的应用 / GitHub 连接 | 看连接状态与授权范围；能重连就重连一次 |
| 2 | GitHub → Settings → Applications → 对应 App → Configure | **Repository access** 勾上 `wnglng026/PyMoDAQ-dev`；**Permissions → Contents: Read and write**（有 Pull requests 权限一并给） |
| 3 | 回到 ChatGPT | 先**读一次**目标分支与文件，再改**一个小文件**提交，核对是否真的产生了提交（别一上来就批量改） |

**恢复之前不必停工**：走 §2 的 **C 模式**（ChatGPT 给补丁/完整文件内容 → 本机 `git apply`
或本地编辑 → 跑验收 → 本地推送）。本轮"审计空结果守卫"就是这么落地的：网页版只描述了改动意图，
本机实现 + 验证 + 推送（`cf60ba803`）。

---

## 12. ⚠️ 已经做完的部分（在线助手请勿重复实现）

在线助手在 403 报告里列了一份"恢复权限后的修改顺序"，其中第 2–5 项**大部分已经完成并验证过**，
照那份清单去"调试/修复"很可能把已验证的代码改坏。逐条核对如下：

| 在线助手的计划项 | 实际状态 | 证据（可自行核对） |
|---|---|---|
| 1. 修 `i18n_audit.py` 的"提取为空却报 100%" | ✅ **本机已修**（本项确实存在，已复现并修掉） | `cf60ba803`；`tools/i18n/i18n_audit.py` 顶部 docstring 有退出码语义 |
| 2. "检查并修复 `i18n_codemod.py` 的只读模式与写入边界" | ✅ 已有：`--dry-run` / `--report-only` / `--files` / `--max-targets`；10-13 还修了"含 `/` 就跳过"的路径误判、补齐对话框类汇聚点 | `tools/i18n/i18n_codemod.py`；提交 `9e295aa3f` |
| 3. "调试 `pymodaq_utils.i18n` 的语言解析、加载、回退、缓存" | ✅ 已实现并按此设计工作：`PYMODAQ_LANG` > 配置 `[i18n] language` > 系统区域 > `en`；语言包按文件名排序、后者覆盖前者；`load_pack(refresh=True)` 用于切换语言 | `packages/pymodaq_utils/src/pymodaq_utils/i18n.py`；交接文档 §4 |
| 4. "调试 Qt 翻译器的安装、上下文匹配与生命周期" | ✅ 已实现：`pymodaq_gui.i18n.PackTranslator` 在 `mkQApp()` 安装；查找顺序 `[contexts.<上下文>]` → `[general]` → 回退语言包 → 原文；查不到必须回退原文（返回空串会让界面变空白，实测踩过） | `packages/pymodaq_gui/src/pymodaq_gui/i18n.py`；提交 `2a657d5e7` |
| 5. "补测试、检查翻译资源打包与 Dashboard 集成" | ⚠️ **部分完成**：打包链路（extract → seed → pack）已完成并加了写前自检；**仍缺**：CI 门禁接线、`tools/` 的正式自动化测试（目前只有一次性自测脚本） | §6、交接文档 §9.3 |

**真正剩下的活**（按优先级）：

1. 50 处未包装界面文案（清单见交接文档 §9.3）——纯体力活，最适合在线助手做；
2. `.github/workflows/i18n-audit.yml` 门禁接线（§6）；
3. 给 `tools/i18n/` 加正式测试（把本轮的一次性自测固化成 `tools/i18n/tests/`）；
4. USB2830 采集插件（方案见 `PyMoDAQ-dev-方案.md` §3，代码未开工）。

---

*本文"实测"项均可复现：分支/worktree/默认分支来自 `git worktree list`、`git ls-remote --symref origin HEAD`、`git stash list`；能力边界来自产品行为（网页版无本地执行环境）。*
