# -*- coding: utf-8 -*-
"""给 `.ts` 打种子译文：复用现有 L3 词典（`pymodaq_zh`）与人工映射文件。

为什么复用 L3 词典：`pymodaq_zh/dictionary.py` 里已有 **650 条**中英对照（译自 7 个界面的实测文案），
而且它带的匹配规则（末尾冒号、省略号归一）与 `.ts` 的 `<source>` 写法基本一致，能直接当种子。

用法::

    python tools/i18n/i18n_seed.py                      # 只用 L3 词典打底
    python tools/i18n/i18n_seed.py --map tools/i18n/zh_map.toml   # 再应用人工映射
    python tools/i18n/i18n_seed.py --report             # 只统计能命中多少，不写文件

映射文件格式（TOML，键是英文原文，值是中文）::

    [map]
    "Main Settings:" = "主设置："
    "Wait time (ms):" = "等待时间(ms)："

注意：**只填空着的 `<translation>`**，不覆盖已有译文（避免把人工润色过的内容冲掉）。
"""

from __future__ import annotations

import argparse
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

CORE_PACKAGES = ("pymodaq", "pymodaq_gui")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def translations_dir(package: str) -> Path:
    return repo_root() / "packages" / package / "src" / package / "resources" / "translations"


def load_l3_dictionary() -> Dict[str, str]:
    """载入 L3 词典（优先用已安装的包，失败则按路径加载）。"""
    try:
        from pymodaq_zh.dictionary import TRANSLATIONS

        return dict(TRANSLATIONS)
    except Exception:
        pass
    path = repo_root().parent / "pymodaq_zh" / "pymodaq_zh" / "dictionary.py"
    if not path.is_file():
        return {}
    import importlib.util

    spec = importlib.util.spec_from_file_location("pymodaq_zh_dictionary", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses 需要
    spec.loader.exec_module(module)
    return dict(getattr(module, "TRANSLATIONS", {}))


def normalize_like_l3(source: str, dictionary: Dict[str, str]) -> str:
    """按 L3 的规则查表（末尾冒号/省略号归一），查不到返回原串。"""
    hit = dictionary.get(source)
    if hit:
        return hit
    last = source[-1:] if source else ""
    if last in (":", "："):
        base = dictionary.get(source[:-1].strip())
        if base:
            return base + "："
    for suffix, replacement in (("...", "…"), ("…", "…")):
        if source.endswith(suffix):
            base = dictionary.get(source[: -len(suffix)].strip())
            if base:
                return base + replacement
    return source


def normalize_like_l3_map(source: str, mapping: Dict[str, str]) -> str:
    """人工映射文件同规则：先精确，再按末尾冒号/省略号归一。"""
    return normalize_like_l3(source, mapping)


def fill_ts(path: Path, mapping: Dict[str, str], write: bool = True) -> Tuple[int, int]:
    """把 mapping 里能对上的空译文填进 `.ts`；返回（填入条数, 总条目数）。"""
    if not path.is_file():
        return 0, 0
    tree = ET.parse(path)
    root = tree.getroot()
    filled = 0
    total = 0
    for context in root.findall("context"):
        for message in context.findall("message"):
            source = message.findtext("source") or ""
            node = message.find("translation")
            if node is None or not source:
                continue
            total += 1
            existing = (node.text or "").strip()
            if existing and node.get("type") != "unfinished":
                continue                      # 已有译文，跳过（不覆盖）
            translated = normalize_like_l3_map(source, mapping)
            if translated == source:
                continue                      # 没命中
            node.text = translated
            if node.get("type") == "unfinished":
                del node.attrib["type"]
            filled += 1
    if filled and write:
        ET.indent(tree, space="    ")
        body = ET.tostring(root, encoding="unicode")
        path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body,
                        encoding="utf-8")
    return filled, total


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="i18n_seed", description="给 .ts 打种子译文")
    parser.add_argument("--map", default=None, help="额外的人工映射文件（TOML，[map] 段）")
    parser.add_argument("--packages", nargs="*", default=list(CORE_PACKAGES))
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument("--report", action="store_true", help="只统计不写文件")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    mapping = load_l3_dictionary()
    print(f"L3 词典载入 {len(mapping)} 条")
    if args.map:
        map_path = Path(args.map)
        if map_path.is_file():
            extra = tomllib.loads(map_path.read_text(encoding="utf-8")).get("map", {})
            mapping.update(extra)
            print(f"人工映射载入 {len(extra)} 条（合计 {len(mapping)}）")
        else:
            print(f"警告：映射文件不存在 {map_path}", file=sys.stderr)

    for package in args.packages:
        ts_file = translations_dir(package) / f"{package}_{args.language}.ts"
        if not ts_file.is_file():
            print(f"{package:<14} 无 .ts（先跑 i18n extract）")
            continue
        filled, total = fill_ts(ts_file, mapping, write=not args.report)
        ratio = filled / total if total else 0.0
        action = "可填" if args.report else "已填"
        print(f"{package:<14} {action} {filled:>4} / {total:>4}（{ratio:.1%}）"
              f"{'   [只统计]' if args.report else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
