# -*- coding: utf-8 -*-
"""i18n 审计：台账（提取条目 vs 已译）、占位符一致性、覆盖率门禁。

用法::

    python tools/i18n/i18n_audit.py                     # 全量台账 + 一致性检查
    python tools/i18n/i18n_audit.py --package pymodaq   # 只看某个包
    python tools/i18n/i18n_audit.py --fail-under 100     # 覆盖率低于阈值时返回非零（CI 门禁）

退出码::

    0  正常（覆盖率达标，或未设门禁）
    1  覆盖率低于 ``--fail-under``
    2  **审计结果不可信**：提取到 0 条、条目低于 ``--min-entries``、或没有可审计条目却设了门禁

为什么要有退出码 2：**"提取结果为空"绝不能被当成"100% 覆盖"**。原实现里
``translated / (total - allowed)`` 在 ``total == 0`` 时走了 ``else 1.0`` 分支，
于是 pylupdate6 静默失败 / 镜像复制不全 / `.ts` 被截断这类事故，会被审计工具
报成"✅ 全译 100.0%"——刚好掩盖最需要发现的问题（实测踩过：语言包 0 条 → 界面空白）。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

CORE_PACKAGES = ("pymodaq_utils", "pymodaq_data", "pymodaq_gui", "pymodaq_scripting", "pymodaq")
PLACEHOLDER_RE = re.compile(r"%[sdf]|\{[^{}]*\}|%[0-9]+")
# 源码里"应该产生 .ts 条目"的调用点（用于发现"提取结果为空"的异常）
TRANSLATE_CALL_RE = re.compile(r"QCoreApplication\.translate\(|\.tr\(|\btranslate\(")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def translations_dir(package: str) -> Path:
    return repo_root() / "packages" / package / "src" / package / "resources" / "translations"


def extract_fresh(package: str, language: str) -> Path:
    """全新提取（复用 pymodaq_utils.i18n 的实现：镜像到临时目录再跑 pylupdate6）。

    之所以不直接在这里调 pylupdate6：实测它在本仓库路径下处理"已改写"的文件会抛内部错误，
    而 pymodaq_utils.i18n.extract_fresh 已经带了镜像绕过。
    """
    from pymodaq_utils import i18n as core

    path = core.extract_fresh(package, language)
    if path is None:
        raise RuntimeError(f"提取失败：{package}")
    # 参数标题等静态文案不走 tr()，需要单独并入（与 extract_package 保持一致）
    core.merge_static_messages(path, core.collect_static_messages(package))
    return path


def read_ts(path: Path) -> List[Tuple[str, str, str]]:
    """返回 [(context, source, translation)]；未完成的译文记为 ''. """
    rows: List[Tuple[str, str, str]] = []
    if not path.is_file():
        return rows
    for context in ET.parse(path).getroot().findall("context"):
        name = context.findtext("name") or "general"
        for message in context.findall("message"):
            source = message.findtext("source") or ""
            node = message.find("translation")
            text = (node.text or "").strip() if node is not None else ""
            if node is not None and node.get("type") == "unfinished":
                text = ""
            rows.append((name, source, text))
    return rows


def placeholders(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for match in PLACEHOLDER_RE.findall(text):
        key = re.sub(r"\d+", "N", match)  # %1/%2 视为同类
        counts[key] = counts.get(key, 0) + 1
    return counts


def is_allowed(source: str, allowed: set) -> bool:
    """白名单匹配：整串命中，或**首行**命中（多行文案在白名单里按首行记录）。"""
    return source in allowed or source.split("\n")[0].strip() in allowed


def source_files_with_translate_calls(package: str) -> int:
    """统计包里含 ``translate()``/``tr()`` 调用的 ``.py`` 文件数。

    这是"提取结果为空"的独立旁证：若源码里明明有 N 个文件在调用翻译，
    而提取出来 0 条，那一定是提取环节出了问题，不能算作"无需翻译"。
    """
    src = repo_root() / "packages" / package / "src" / package
    if not src.is_dir():
        return 0
    hits = 0
    for path in src.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            if TRANSLATE_CALL_RE.search(path.read_text(encoding="utf-8", errors="replace")):
                hits += 1
        except OSError:
            continue
    return hits


def parse_min_entries(values) -> Dict[str, int]:
    """把 ``--min-entries pymodaq=400`` 解析成字典。"""
    result: Dict[str, int] = {}
    for item in values or ():
        if "=" not in item:
            raise SystemExit(f"--min-entries 需要 PACKAGE=N 形式，收到 {item!r}")
        package, _, number = item.partition("=")
        try:
            result[package.strip()] = int(number)
        except ValueError:
            raise SystemExit(f"--min-entries 的 N 必须是整数，收到 {item!r}")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="i18n_audit", description="PyMoDAQ i18n 台账与一致性审计")
    parser.add_argument("--package", help="只审计某个包")
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument("--fail-under", type=float, default=None,
                        help="覆盖率低于该百分比时返回非零（CI 门禁）")
    parser.add_argument("--allowlist", default="tools/i18n/allow_english.txt",
                        help="有意保留英文的条目清单（每行一条，统计覆盖率时排除）")
    parser.add_argument("--min-entries", action="append", default=None, metavar="PACKAGE=N",
                        help="该包提取条目数低于 N 就判失败（可重复，用于 CI 钉住底线）")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    min_entries = parse_min_entries(args.min_entries)
    packages = (args.package,) if args.package else CORE_PACKAGES
    allow_path = repo_root() / args.allowlist
    allowed = set()
    if allow_path.is_file():
        allowed = {line.strip() for line in allow_path.read_text(encoding="utf-8").splitlines()
                   if line.strip() and not line.startswith("#")}
    missing_total = 0
    rows_total = 0
    inconsistent: List[Tuple[str, str, str]] = []
    empty_extraction: List[Tuple[str, int]] = []    # (包, 源码里含翻译调用的文件数)
    below_min: List[Tuple[str, int, int]] = []      # (包, 实际条目, 要求下限)

    print("=" * 86)
    print(f"i18n 审计（语言 {args.language}）")
    print("=" * 86)
    print(f"{'包':<18}{'条目':>6}{'已译':>7}{'未译':>7}{'覆盖率':>9}   备注")
    for package in packages:
        dir_ts = translations_dir(package)
        if not dir_ts.is_dir():
            print(f"{package:<18}{'-':>6}{'-':>7}{'-':>7}{'-':>9}   无 translations 目录")
            continue
        committed = dir_ts / f"{package}_{args.language}.ts"
        fresh_rows = read_ts(extract_fresh(package, args.language))
        committed_rows = read_ts(committed)
        translated_map = {(c, s): t for c, s, t in committed_rows if t}

        total = len(fresh_rows)

        # —— 关键守卫：条目为 0 时，先分清"本该有"还是"本来就没有" ——
        if total == 0:
            src_calls = source_files_with_translate_calls(package)
            if src_calls:
                empty_extraction.append((package, src_calls))
                print(f"{package:<18}{0:>6}{0:>7}{0:>7}{'—':>9}   "
                      f"⛔ 提取结果为空，但源码里有 {src_calls} 个文件含 translate()/tr() 调用")
            else:
                print(f"{package:<18}{0:>6}{0:>7}{0:>7}{'—':>9}   "
                      f"—（该包没有界面文案，覆盖率不适用）")
            continue

        translated = sum(1 for c, s, _ in fresh_rows if translated_map.get((c, s)))
        allowed_hits = sum(1 for c, s, _ in fresh_rows
                           if not translated_map.get((c, s)) and is_allowed(s, allowed))
        missing = total - translated - allowed_hits
        missing_total += missing
        rows_total += total - allowed_hits
        ratio = translated / (total - allowed_hits) if total - allowed_hits else 1.0
        if package in min_entries and total < min_entries[package]:
            below_min.append((package, total, min_entries[package]))
        note = "✅ 全译" if missing == 0 else f"缺 {missing} 条"
        note += "（有 .ts）" if committed.is_file() else "（尚无 .ts，先跑 i18n extract）"
        print(f"{package:<18}{total:>6}{translated:>7}{missing:>7}{ratio:>8.1%}   {note}"
              f"（另有 {allowed_hits} 条按设计保留英文）")

        for _, source, translation in committed_rows:
            if translation and placeholders(source) != placeholders(translation):
                inconsistent.append((package, source, translation))

    print("-" * 86)
    ratio_all = (rows_total - missing_total) / rows_total if rows_total else None
    if ratio_all is None:
        print(f"合计：条目 0  未译 0  覆盖率 —（没有可审计的界面文案，不按 100% 计）")
    else:
        print(f"合计：条目 {rows_total}  未译 {missing_total}  覆盖率 {ratio_all:.1%}")
    if inconsistent:
        print(f"\n⚠️ 占位符不一致 {len(inconsistent)} 条（译文与原文的占位符数量/种类不同）：")
        for package, source, translation in inconsistent[:10]:
            print(f"  [{package}] {source!r} -> {translation!r}")
    else:
        print("占位符一致性：全部通过 ✅")

    # —— 硬错误：结果不可信就直接判失败，绝不当成"覆盖率 100%"放行 ——
    if empty_extraction:
        print(f"\n⛔ 提取结果为空 {len(empty_extraction)} 个包 —— 覆盖率不可信，本次审计判失败：")
        for package, src_calls in empty_extraction:
            print(f"  [{package}] 源码里有 {src_calls} 个文件含 translate()/tr() 调用，却提取到 0 条")
        print("  排查顺序：")
        print("    1) .venv\\Scripts\\python.exe -m pymodaq_utils.i18n extract   # 看是否报错")
        print("    2) pylupdate6 是否可用（PyQt6 自带；本仓库必须走“镜像到临时目录”的绕行实现）")
        print("    3) 该包的 src 目录是否完整（镜像复制失败会得到空结果）")
        print("  ⚠ 这种情况**不要**直接看覆盖率，先修提取。")
    if below_min:
        print(f"\n⛔ 提取条目数低于底线 {len(below_min)} 个包：")
        for package, total, required in below_min:
            print(f"  [{package}] 实际 {total} 条 < 要求 {required} 条")

    if empty_extraction or below_min:
        return 2

    if args.fail_under is not None:
        if ratio_all is None:
            print(f"\n⚠ 没有可审计条目，覆盖率门禁（--fail-under {args.fail_under}%）无法判定"
                  f" → 退出码 2（fail-closed，避免“空结果=达标”）")
            return 2
        if ratio_all * 100 < args.fail_under:
            print(f"\n覆盖率 {ratio_all:.1%} 低于阈值 {args.fail_under}% → 退出码 1")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
