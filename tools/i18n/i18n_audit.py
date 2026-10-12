# -*- coding: utf-8 -*-
"""i18n 审计：台账（提取条目 vs 已译）、占位符一致性、覆盖率门禁。

用法::

    python tools/i18n/i18n_audit.py                     # 全量台账 + 一致性检查
    python tools/i18n/i18n_audit.py --package pymodaq   # 只看某个包
    python tools/i18n/i18n_audit.py --fail-under 100     # 覆盖率低于阈值时返回非零（CI 门禁）
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="i18n_audit", description="PyMoDAQ i18n 台账与一致性审计")
    parser.add_argument("--package", help="只审计某个包")
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument("--fail-under", type=float, default=None,
                        help="覆盖率低于该百分比时返回非零（CI 门禁）")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    packages = (args.package,) if args.package else CORE_PACKAGES
    missing_total = 0
    rows_total = 0
    inconsistent: List[Tuple[str, str, str]] = []

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
        translated = sum(1 for c, s, _ in fresh_rows if translated_map.get((c, s)))
        missing = total - translated
        missing_total += missing
        rows_total += total
        ratio = translated / total if total else 1.0
        note = "✅ 全译" if missing == 0 else f"缺 {missing} 条"
        note += "（有 .ts）" if committed.is_file() else "（尚无 .ts，先跑 i18n extract）"
        print(f"{package:<18}{total:>6}{translated:>7}{missing:>7}{ratio:>8.1%}   {note}")

        for _, source, translation in committed_rows:
            if translation and placeholders(source) != placeholders(translation):
                inconsistent.append((package, source, translation))

    print("-" * 86)
    ratio_all = (rows_total - missing_total) / rows_total if rows_total else 1.0
    print(f"合计：条目 {rows_total}  未译 {missing_total}  覆盖率 {ratio_all:.1%}")
    if inconsistent:
        print(f"\n⚠️ 占位符不一致 {len(inconsistent)} 条（译文与原文的占位符数量/种类不同）：")
        for package, source, translation in inconsistent[:10]:
            print(f"  [{package}] {source!r} -> {translation!r}")
    else:
        print("占位符一致性：全部通过 ✅")

    if args.fail_under is not None and ratio_all * 100 < args.fail_under:
        print(f"\n覆盖率 {ratio_all:.1%} 低于阈值 {args.fail_under}% → 退出码 1")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
