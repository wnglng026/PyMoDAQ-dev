# -*- coding: utf-8 -*-
"""i18n 改写工具（AST 外科式改写，保留原格式与注释）。

把"界面文案"包进 Qt 的翻译调用，供 ``pylupdate6`` 提取：

统一使用 ``QtCore.QCoreApplication.translate('<context>', '文案')``
（context 取所属类名，模块级取模块名）。

**为什么不统一用 `self.tr`**：PyMoDAQ 里有大量**不继承 QObject** 的类
（例如 ``ParameterTreeWidget``），在这些类的方法里调用 ``self.tr`` 会
``AttributeError``（实测踩到过）。``QCoreApplication.translate`` 没有这个限制，
而且 context 语义与 ``QObject.tr`` 相同（类名），翻译条目不变。

设计原则
--------
* **只改字符串节点**：AST 定位 + 按字节区间替换，其余源码（缩进/注释/空行）一字不动；
* **只改已知的界面汇聚点**（见 ``SINK_RULES``），不碰字典键、图标名、短名等；
* **幂等**：已在 ``tr()``/``translate()`` 里的字符串不再包装；
* **不做模棱两可的改写**：f-string、看起来像标识符/路径/URL 的串跳过并记入报告。

用法::

    python tools/i18n/i18n_codemod.py --dry-run --files packages/pymodaq/src/pymodaq/launcher/launcher.py
    python tools/i18n/i18n_codemod.py --dry-run --limit 1 --packages pymodaq_gui
    python tools/i18n/i18n_codemod.py --packages pymodaq pymodaq_gui
    python tools/i18n/i18n_codemod.py --report-only
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

# 界面文案的"汇聚点"：调用名（尾部）-> (位置参数索引, 关键字名)
SINK_RULES: Dict[str, Tuple[Sequence[int], Sequence[str]]] = {
    # add_action(short_name, name, icon_name, tip, ...) -> 位置 1=显示名，位置 3=提示
    "add_action": ((1, 3), ("name", "tip")),
    "add_menu": ((1,), ("title",)),
    "add_widget": ((), ("tip",)),
    "setWindowTitle": ((0,), ()),
    "setToolTip": ((0,), ()),
    "setStatusTip": ((0,), ()),
    "setTitle": ((0,), ()),
    "setText": ((0,), ()),
    "setTabText": ((1,), ()),
    "addTab": ((1,), ()),
    "QLabel": ((0,), ("text",)),
    "QPushButton": ((0,), ("text",)),
    "QCheckBox": ((0,), ("text",)),
    "QRadioButton": ((0,), ("text",)),
    "QToolButton": ((0,), ("text",)),
    "QGroupBox": ((0,), ("title",)),
    "QMenu": ((0,), ("title",)),
    "QDockWidget": ((0,), ("title",)),
    "QAction": ((0, 1), ("text",)),
}

# 明确不该翻译的整串（插件/模块标识、库名、数据值）
SKIP_VALUES = {
    "True", "False", "None", "nan", "inf",
    "h5py", "h5pyd", "zlib", "pymodaq", "scan", "hdf5", "txt", "csv",
    "Mock", "Remote", "LECODirector", "DataMixer", "ROI", "H5",
    "DAQ0D", "DAQ1D", "DAQ2D", "DAQND",
}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NAME_WITH_DIGITS_RE = re.compile(r"^[A-Za-z_]+[0-9]+$")
_TECHNICAL_RE = re.compile(r"(://|\\\\|/|\\)")
_PLACEHOLDER_RE = re.compile(r"%[sdf]|\{[^{}]*\}")


@dataclass
class FileReport:
    path: Path
    wrapped: int = 0
    skipped: List[Tuple[int, str, str]] = field(default_factory=list)
    manual: List[Tuple[int, str, str]] = field(default_factory=list)
    needs_import: bool = False


def should_skip(text: str) -> Optional[str]:
    """返回跳过原因；``None`` 表示可以包装。"""
    stripped = text.strip()
    if not stripped:
        return "空串"
    if stripped in SKIP_VALUES or text in SKIP_VALUES:
        return "标识符/数据值（白名单）"
    if _NAME_WITH_DIGITS_RE.match(stripped):
        return "形如 Scan000 的自动名称"
    if _TECHNICAL_RE.search(stripped):
        return "路径/URL"
    if _IDENTIFIER_RE.match(stripped) and (stripped.islower() or stripped.isupper()):
        return "单个标识符（全大写或全小写）"
    return None


class Collector(ast.NodeVisitor):
    """收集需要包装的字符串节点与其上下文。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.report = FileReport(path=path)
        # (节点, 上下文)：上下文必须在**收集时**确定（遍历结束后类栈已清空）
        self.targets: List[Tuple[ast.Constant, str]] = []
        self.marked: Set[int] = set()
        self._classes: List[str] = []

    @property
    def context(self) -> str:
        return self._classes[-1] if self._classes else self.path.stem

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._classes.append(node.name)
        self.generic_visit(node)
        self._classes.pop()

    def visit_Call(self, node: ast.Call) -> None:
        try:
            short = ast.unparse(node.func).split(".")[-1]
        except Exception:
            short = ""
        rule = SINK_RULES.get(short)
        if rule is not None:
            positional, keywords = rule
            for index in positional:
                if index < len(node.args):
                    self._consider(node.args[index], f"{short} 位置参数 {index}")
            for keyword in keywords:
                for kw in node.keywords:
                    if kw.arg == keyword:
                        self._consider(kw.value, f"{short}.{keyword}")
        self.generic_visit(node)

    def _consider(self, node: ast.AST, where: str) -> None:
        if isinstance(node, ast.JoinedStr):
            self.report.manual.append((getattr(node, "lineno", 0), "<f-string>", where))
            return
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            self.report.manual.append((getattr(node, "lineno", 0), "<% 格式化>", where))
            return
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return
        if id(node) in self.marked:
            return
        reason = should_skip(node.value)
        if reason:
            self.report.skipped.append((node.lineno, node.value[:40], f"{reason} @ {where}"))
            return
        if _PLACEHOLDER_RE.search(node.value):
            self.report.manual.append((node.lineno, node.value[:40], f"含占位符 @ {where}"))
        self.targets.append((node, self.context))


def mark_wrapped(tree: ast.AST, collector: Collector) -> None:
    """标记已经在 tr()/translate() 调用里的字符串（保证幂等）。"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            short = ast.unparse(node.func).split(".")[-1]
        except Exception:
            short = ""
        if short in ("tr", "translate", "_translate"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    collector.marked.add(id(arg))


def line_start_bytes(text: str) -> List[int]:
    """每行起始处的**字节**偏移。

    必须用字节：``ast`` 的 ``col_offset``/``end_col_offset`` 是 UTF-8 **字节**偏移，
    而 Python 字符串的切片是按字符。混用会在"字符串前面有非 ASCII 字符"的行上错位
    （实测把它写坏成 Git 认定的二进制文件）。
    """
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    return offsets


def node_span_bytes(node: ast.Constant, offsets: Sequence[int]) -> Tuple[int, int]:
    return (offsets[node.lineno - 1] + node.col_offset,
            offsets[node.end_lineno - 1] + node.end_col_offset)


def dominant_eol(text: str) -> bytes:
    """判断文件的主换行风格（用于注入 import 时保持一致）。"""
    crlf = text.count("\r\n")
    lone_lf = text.count("\n") - crlf
    return b"\r\n" if crlf and crlf >= lone_lf else b"\n"


def has_qtcore_name(tree: ast.AST) -> bool:
    """模块顶层是否绑定了名字 ``QtCore``（我们生成的调用用的是裸名 ``QtCore``）。

    注意：``from qtpy.QtCore import Slot, QObject`` 只绑定成员、**不绑定** ``QtCore``；
    ``import qtpy.QtCore`` 只绑定 ``qtpy``；这两种都不算。
    """
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.asname == "QtCore" or alias.name == "QtCore":
                    return True
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.module == "qtpy" and any(
                    alias.name == "QtCore" and alias.asname in (None, "QtCore") for alias in stmt.names):
                return True
    return False


def transform_bytes(path: Path, data: bytes, max_targets: Optional[int] = None) -> Tuple[bytes, FileReport]:
    """返回（改写后的字节, 报告）；本函数不写文件。

    全程按字节切片，除了被包装的字符串字面量之外**不动任何一个字节**
    （换行、BOM、缩进、注释都原样保留）。
    """
    text = data.decode("utf-8")
    tree = ast.parse(text)
    collector = Collector(path)
    mark_wrapped(tree, collector)
    collector.visit(tree)
    report = collector.report

    offsets = line_start_bytes(text)
    edits: List[Tuple[int, int, bytes]] = []
    targets = collector.targets[:max_targets] if max_targets else collector.targets
    for node, context in targets:
        start, end = node_span_bytes(node, offsets)
        literal = data[start:end].decode("utf-8")      # 原字面量（含引号）
        replacement = f"QtCore.QCoreApplication.translate({context!r}, {literal})"
        edits.append((start, end, replacement.encode("utf-8")))
        report.wrapped += 1

    if not edits:
        return data, report

    if edits and not has_qtcore_name(tree):
        report.needs_import = True
        import_end = 0
        for stmt in tree.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                import_end = offsets[stmt.end_lineno - 1] + stmt.end_col_offset
        insertion = dominant_eol(text) + b"from qtpy import QtCore"
        edits.append((import_end, import_end, insertion if import_end else
                      b"from qtpy import QtCore" + dominant_eol(text)))

    new_data = data
    for start, end, replacement in sorted(edits, key=lambda item: item[0], reverse=True):
        new_data = new_data[:start] + replacement + new_data[end:]
    return new_data, report


def iter_target_files(packages: Sequence[str], repo_root: Path, limit: Optional[int]) -> List[Path]:
    files: List[Path] = []
    for package in packages:
        source_dir = repo_root / "packages" / package / "src" / package
        if not source_dir.is_dir():
            continue
        files.extend(sorted(p for p in source_dir.rglob("*.py")
                            if "__pycache__" not in p.parts and "tests" not in p.parts))
    return files[:limit] if limit else files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="i18n_codemod", description="PyMoDAQ i18n 改写工具")
    parser.add_argument("--packages", nargs="*", default=["pymodaq", "pymodaq_gui"])
    parser.add_argument("--files", nargs="*", help="只处理这些文件（覆盖 --packages）")
    parser.add_argument("--limit", type=int, help="最多处理多少个文件")
    parser.add_argument("--dry-run", action="store_true", help="只打印 diff，不写文件")
    parser.add_argument("--report-only", action="store_true", help="只出统计报告，不写文件")
    parser.add_argument("--repo", default=None, help="仓库根目录（默认按脚本位置推断）")
    parser.add_argument("--diff-lines", type=int, default=60, help="每个文件最多打印多少行 diff")
    parser.add_argument("--max-targets", type=int, default=None,
                        help="每个文件最多包装多少条（用于二分定位问题构造）")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    repo_root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    files = ([Path(f) for f in args.files] if args.files
             else iter_target_files(args.packages, repo_root, args.limit))

    total_wrapped = 0
    changed_files = 0
    reports: Dict[str, dict] = {}
    for path in files:
        data = path.read_bytes()
        try:
            new_data, report = transform_bytes(path, data, max_targets=args.max_targets)
        except SyntaxError as exc:
            print(f"!! 语法错误，跳过 {path}: {exc}")
            continue
        total_wrapped += report.wrapped
        reports[str(path)] = {
            "wrapped": report.wrapped,
            "skipped": report.skipped,
            "manual": report.manual,
            "needs_import": report.needs_import,
        }
        if not report.wrapped:
            continue
        changed_files += 1
        try:
            rel = path.relative_to(repo_root)
        except ValueError:
            rel = path
        if args.dry_run:
            source = data.decode("utf-8", errors="replace")
            new_source = new_data.decode("utf-8", errors="replace")
            diff = list(difflib.unified_diff(
                source.splitlines(keepends=True), new_source.splitlines(keepends=True),
                fromfile=f"a/{rel}", tofile=f"b/{rel}"))
            flag = "  (需注入 from qtpy import QtCore)" if report.needs_import else ""
            print(f"\n########## {rel}   包装 {report.wrapped} 条{flag}")
            print("".join(diff[: args.diff_lines]))
        if not (args.dry_run or args.report_only):
            path.write_bytes(new_data)

    print("\n" + "=" * 72)
    print(f"文件数 {len(files)}    有改动 {changed_files}    包装字符串 {total_wrapped}")
    print("需人工处理（f-string / 占位符）"
          f"{sum(len(item['manual']) for item in reports.values())} 处")
    if total_wrapped and not (args.dry_run or args.report_only):
        print("已写入。建议随后运行：python -m pytest packages/<改动包> -q 以及 i18n_audit.py")
    if not args.dry_run:
        report_file = repo_root / "tools" / "i18n" / "codemod_report.json"
        report_file.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告：{report_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
