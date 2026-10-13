# -*- coding: utf-8 -*-
"""PyMoDAQ 国际化（i18n）核心：语言解析、语言包加载与查找。

设计要点
--------
* 本模块**不依赖 Qt**，因此 pymodaq_utils / pymodaq_data 在没有 Qt 的环境也能用；
  Qt 侧的 ``QTranslator`` 实现放在 ``pymodaq_gui.i18n``（把 ``tr()`` 的查找转到这里）。
* 语言包是 **TOML** 文件（人可读、可 diff、便于评审），由 ``.ts``（Qt Linguist 作者格式）
  用本模块的命令行编译而来；因此**不依赖 Qt 的 lrelease**（本机 PyQt6 实测没有该工具）。
* 语言包文件命名：``<scope>_<语言>.toml``（如 ``pymodaq_zh_CN.toml``、
  ``pymodaq_plugins_usb2830_zh_CN.toml``）；可多个文件，按文件名排序**后者覆盖前者**，
  因此插件可以用自己的语言包补充/覆盖核心条目。
* 查找顺序：``[contexts.<上下文>]`` → ``[general]`` → 回退语言包 → 原文。

配置（``~/.pymodaq/config/utils.toml``）::

    [i18n]
    language = "auto"   # auto | en | zh_CN | ...
    fallback = "en"
    extra_paths = []

环境变量 ``PYMODAQ_LANG`` 优先级最高（便于临时切换与 CI）。

命令行::

    python -m pymodaq_utils.i18n status    # 翻译进度
    python -m pymodaq_utils.i18n extract   # pylupdate6 提取 -> .ts
    python -m pymodaq_utils.i18n pack      # .ts -> TOML 语言包（运行时用）
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from pymodaq_utils.logger import get_module_name, set_logger

logger = set_logger(get_module_name(__file__))

ENV_LANG = "PYMODAQ_LANG"
DEFAULT_LANGUAGE = "en"
GENERAL = "general"
TRANSLATIONS_DIRNAME = ("resources", "translations")

# 核心包（用于定位仓库与语言包目录）
CORE_PACKAGES = ("pymodaq_utils", "pymodaq_data", "pymodaq_gui", "pymodaq_scripting", "pymodaq")


def _config():
    try:
        from pymodaq_utils.config import GlobalConfig

        return GlobalConfig()
    except Exception:  # pragma: no cover - 无配置时用默认值
        return None


def _config_get(key: str, default):
    config = _config()
    if config is None:
        return default
    try:
        return config["i18n", key]
    except Exception:
        return default


def _module_translations_dir(module_name: str) -> Optional[Path]:
    """某个已安装包的 ``resources/translations`` 目录（不导入该包）。"""
    try:
        spec = importlib.util.find_spec(module_name)
    except Exception:
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(list(spec.submodule_search_locations)[0]).joinpath(*TRANSLATIONS_DIRNAME)


def package_dirs() -> List[Path]:
    """所有可能存放语言包的目录（去重、只保留存在的）。"""
    dirs: List[Path] = []

    for name in CORE_PACKAGES:
        directory = _module_translations_dir(name)
        if directory is not None:
            dirs.append(directory)

    # 插件包（允许插件自带语言包）
    try:
        from pymodaq_utils.utils import get_entrypoints

        for group in ("pymodaq.plugins", "pymodaq.instruments", "pymodaq.extensions"):
            for entry_point in get_entrypoints(group):
                directory = _module_translations_dir(entry_point.value.split(":")[0])
                if directory is not None:
                    dirs.append(directory)
    except Exception:
        pass

    for extra in _config_get("extra_paths", []) or []:
        dirs.append(Path(extra))

    unique: List[Path] = []
    seen = set()
    for directory in dirs:
        if directory.is_dir() and directory not in seen:
            seen.add(directory)
            unique.append(directory)
    return unique


def available_languages() -> List[str]:
    """扫描语言包得到的可用语言（含回退语言 ``en``）。"""
    languages = {DEFAULT_LANGUAGE}
    for directory in package_dirs():
        for path in directory.glob("*.toml"):
            try:
                meta = tomllib.loads(path.read_text(encoding="utf-8")).get("meta", {})
            except Exception:
                continue
            language = str(meta.get("language", "")).strip()
            if language:
                languages.add(language)
    return sorted(languages)


def system_language() -> Optional[str]:
    """按系统区域在没有明确配置时猜测语言（只返回已有语言包的语言）。"""
    tag = ""
    try:
        import locale

        tag = locale.getlocale()[0] or ""
    except Exception:
        pass
    tag = tag or os.environ.get("LANG", "")
    if not tag:
        return None
    tag = tag.replace("-", "_")
    for language in available_languages():
        if tag.lower().startswith(language.lower()):
            return language
    return None


def resolve_language() -> str:
    """最终语言：环境变量 > 配置 > 系统区域 > ``en``。"""
    env = os.environ.get(ENV_LANG, "").strip()
    if env and env.lower() != "auto":
        return env
    configured = str(_config_get("language", "auto")).strip()
    if configured and configured.lower() != "auto":
        return configured
    return system_language() or DEFAULT_LANGUAGE


_current: Optional[str] = None


def current_language() -> str:
    """当前生效的语言。"""
    global _current
    if _current is None:
        _current = resolve_language()
    return _current


def set_language(language: str) -> str:
    """切换语言（进程内生效，并写入环境变量以便子进程一致）。"""
    global _current
    _current = language
    os.environ[ENV_LANG] = language
    _packs.pop(language, None)
    return language


@dataclass
class LanguagePack:
    """一种语言的全部词条（可来自多个 TOML 文件合并）。"""

    language: str
    name: str = ""
    general: Dict[str, str] = field(default_factory=dict)
    contexts: Dict[str, Dict[str, str]] = field(default_factory=dict)
    sources: List[Path] = field(default_factory=list)

    def lookup(self, source: str, context: Optional[str] = None) -> Optional[str]:
        if context:
            hit = self.contexts.get(context, {}).get(source)
            if hit:
                return hit
        return self.general.get(source) or None

    @property
    def entries(self) -> int:
        return len(self.general) + sum(len(items) for items in self.contexts.values())


_packs: Dict[str, LanguagePack] = {}


def pack_files(language: str) -> List[Path]:
    """某种语言的所有语言包文件（按文件名排序，后者覆盖前者）。"""
    files: List[Path] = []
    for directory in package_dirs():
        files.extend(sorted(directory.glob(f"*_{language}.toml")))
    return files


def load_pack(language: Optional[str] = None, refresh: bool = False) -> LanguagePack:
    """加载（并缓存）语言包，缺失条目用回退语言补齐。"""
    language = language or current_language()
    if not refresh and language in _packs:
        return _packs[language]

    pack = LanguagePack(language=language)
    for path in pack_files(language):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pack.name = str(data.get("meta", {}).get("name", pack.name))
        pack.general.update({str(k): str(v) for k, v in (data.get(GENERAL) or {}).items()})
        for context, entries in (data.get("contexts") or {}).items():
            pack.contexts.setdefault(str(context), {}).update(
                {str(k): str(v) for k, v in entries.items()}
            )
        pack.sources.append(path)

    fallback = str(_config_get("fallback", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE)
    if fallback and fallback != language:
        base = load_pack(fallback, refresh=refresh)
        for source, target in base.general.items():
            pack.general.setdefault(source, target)
        for context, entries in base.contexts.items():
            merged = pack.contexts.setdefault(context, {})
            for source, target in entries.items():
                merged.setdefault(source, target)

    _packs[language] = pack
    return pack


def lookup(source: str, context: Optional[str] = None, language: Optional[str] = None) -> Optional[str]:
    """查找译文；无译文（或目标语言就是英文）时返回 ``None``。"""
    if not source:
        return None
    language = language or current_language()
    if language == DEFAULT_LANGUAGE:
        return None
    return load_pack(language).lookup(source, context)


def repo_root() -> Optional[Path]:
    """从 editable 安装的包位置推断仓库根目录。"""
    directory = _module_translations_dir("pymodaq_utils")
    if directory is None:
        return None
    for candidate in directory.parents:
        if (candidate / "packages" / "pymodaq_utils").is_dir() and (candidate / "install-packages.py").is_file():
            return candidate
    return None


def repo_package_dir(package: str) -> Optional[Path]:
    """``<repo>/packages/<package>/src/<package>``。"""
    root = repo_root()
    if root is None:
        return None
    path = root / "packages" / package / "src" / package
    return path if path.is_dir() else None


def translations_dir(package: str) -> Optional[Path]:
    """``<repo>/packages/<package>/src/<package>/resources/translations``（不存在则创建）。"""
    package_dir = repo_package_dir(package)
    if package_dir is None:
        return None
    path = package_dir.joinpath(*TRANSLATIONS_DIRNAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pylupdate() -> Optional[str]:
    """定位 pylupdate6（PyQt6 自带）。"""
    for name in ("pylupdate6.exe", "pylupdate6"):
        candidate = Path(sys.executable).parent / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which("pylupdate6")


def _mirror_source(package: str, destination: Path) -> Optional[Path]:
    """把包源码镜像到 ``destination``（跳过 ``__pycache__``），返回镜像出的包目录。"""
    source_dir = repo_package_dir(package)
    if source_dir is None:
        return None
    mirror = destination / package
    shutil.copytree(source_dir, mirror,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    return mirror


def _fix_locations(ts_text: str, mirror: Path, package: str) -> str:
    """把 .ts 里的临时镜像路径还原成仓库内相对路径（纯美观，便于评审）。"""
    original = repo_package_dir(package)
    if original is None:
        return ts_text
    mirror_str = str(mirror)
    original_str = str(original)
    for separator in ("\\", "/"):
        ts_text = ts_text.replace(mirror_str.replace("/", separator), original_str.replace("/", separator))
    return ts_text


def extract_fresh(package: str, language: str = "zh_CN", keep_obsolete: bool = False) -> Optional[Path]:
    """**全新**提取一个包的 ``.ts``（不含既有译文），返回临时文件路径（调用方负责删除）。

    注意：在**临时目录的源码镜像**里执行 pylupdate6 —— 实测 pylupdate6 6.11.0
    在本仓库路径下处理"已改写"的文件时会抛出内部错误（同一字节放到临时目录就正常，
    ASCII 与中文路径均已验证），因此统一走镜像，避免踩这个工具 bug。
    """
    tool = _pylupdate()
    if tool is None:
        raise RuntimeError("找不到 pylupdate6（PyQt6 自带：pip install pyqt6 即可）")
    temporary = Path(tempfile.mkdtemp(prefix="pymodaq_i18n_"))
    mirror = _mirror_source(package, temporary)
    if mirror is None:
        return None
    target = temporary / f"{package}_{language}.ts"
    command = [tool, str(mirror), "--exclude", "*__pycache__*", "--ts", str(target)]
    if not keep_obsolete:
        command.insert(1, "--no-obsolete")
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode or not target.is_file():
        raise RuntimeError(f"pylupdate6 提取 {package} 失败（退出码 {result.returncode}）："
                           f"{(result.stdout or '')[-300:]}{(result.stderr or '')[-300:]}")
    target.write_text(_fix_locations(target.read_text(encoding="utf-8"), mirror, package), encoding="utf-8")
    return target


def extract_package(package: str, language: str = "zh_CN", keep_obsolete: bool = False) -> Optional[Path]:
    """提取并**合并**到仓库里的 ``<package>_<language>.ts``（保留既有译文），返回该文件路径。"""
    target_dir = translations_dir(package)
    if target_dir is None:
        return None
    target = target_dir / f"{package}_{language}.ts"
    fresh = extract_fresh(package, language, keep_obsolete=keep_obsolete)
    if fresh is None:
        return None
    if target.is_file():
        # 用既有 .ts 作为输入，让 pylupdate6 合并（保留已翻译条目）
        tool = _pylupdate()
        temporary = fresh.parent
        mirror = temporary / package
        merged = temporary / f"{package}_{language}_merged.ts"
        shutil.copy(target, merged)
        subprocess.run([tool, str(mirror), "--exclude", "*__pycache__*", "--ts", str(merged)],
                       capture_output=True, encoding="utf-8", errors="replace")
        fresh = merged if merged.is_file() else fresh
        fresh.write_text(_fix_locations(fresh.read_text(encoding="utf-8"), mirror, package),
                         encoding="utf-8")
    shutil.copy(fresh, target)
    shutil.rmtree(fresh.parent, ignore_errors=True)
    added = merge_static_messages(target, collect_static_messages(package))
    if added:
        logger.debug(f"{package}: 追加静态文案（参数标题等）{added} 条")
    return target


_SKIP_STATIC = {
    "True", "False", "None", "nan", "inf", "h5py", "h5pyd", "zlib", "pymodaq",
    "scan", "hdf5", "txt", "csv", "Mock", "Remote", "LECODirector", "DataMixer",
    "ROI", "H5", "DAQ0D", "DAQ1D", "DAQ2D", "DAQND",
}


def collect_static_messages(package: str) -> Dict[str, List[str]]:
    """收集**无法用 tr() 包装、但必须翻译**的静态文案（当前：参数树的 ``title``/``tip``）。

    参数定义是类属性里的字典字面量（导入期就求值，那时翻译器还没装），所以不能改写成
    ``tr()``；做法是运行时在构建参数树时集中翻译（见 ``pymodaq_gui.i18n.translate_params``），
    而这里负责把它们**收进 .ts**，让译者能看到并翻译。
    """
    source_dir = repo_package_dir(package)
    messages: Dict[str, List[str]] = {GENERAL: []}
    if source_dir is None:
        return messages
    seen = set()

    def add(text: str) -> None:
        stripped = text.strip()
        if not stripped or stripped in _SKIP_STATIC or stripped in seen:
            return
        if any(token in stripped for token in ("/", "\\", "://")):
            return
        seen.add(stripped)
        messages[GENERAL].append(text)

    for path in sorted(source_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (isinstance(key, ast.Constant) and key.value in ("title", "tip")
                            and isinstance(value, ast.Constant) and isinstance(value.value, str)):
                        add(value.value)
            elif isinstance(node, ast.Call):
                try:
                    function_name = ast.unparse(node.func).split(".")[-1]
                except Exception:
                    function_name = ""
                if "Parameter" not in function_name:
                    continue
                for keyword in node.keywords:
                    if (keyword.arg in ("title", "tip")
                            and isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, str)):
                        add(keyword.value.value)
    return messages


def merge_static_messages(ts_path: Path, extra: Dict[str, List[str]]) -> int:
    """把静态文案并进 ``.ts``（缺失的条目以 unfinished 形式追加），返回新增条数。"""
    if not ts_path.is_file():
        return 0
    tree = ET.parse(ts_path)
    root = tree.getroot()
    existing = {message.findtext("source") or ""
                for context in root.findall("context")
                for message in context.findall("message")}
    added = 0
    for context_name, sources in extra.items():
        target = None
        for context in root.findall("context"):
            if (context.findtext("name") or "") == context_name:
                target = context
                break
        if target is None:
            target = ET.SubElement(root, "context")
            ET.SubElement(target, "name").text = context_name
        for source in sources:
            if source in existing:
                continue
            message = ET.SubElement(target, "message")
            ET.SubElement(message, "source").text = source
            ET.SubElement(message, "translation").set("type", "unfinished")
            existing.add(source)
            added += 1
    if added:
        ET.indent(tree, space="    ")
        body = ET.tostring(root, encoding="unicode")
        ts_path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body,
                           encoding="utf-8")
    return added


def cmd_extract(args) -> int:
    """用 pylupdate6 从源码提取 ``tr()`` 字符串到 ``.ts``。"""
    languages = args.languages or ["zh_CN"]
    packages = args.packages or list(CORE_PACKAGES)
    failures = 0
    for package in packages:
        for language in languages:
            try:
                ts_file = extract_package(package, language, keep_obsolete=args.keep_obsolete)
            except Exception as exc:
                print(f"[extract] {package} 失败：{exc}", file=sys.stderr)
                failures += 1
                continue
            if ts_file is None:
                print(f"跳过 {package}：找不到源码目录（非仓库布局？）")
                continue
            messages = ET.parse(ts_file).getroot().findall(".//message")
            untranslated = sum(1 for m in messages
                               if (m.find("translation") is None
                                   or not (m.findtext("translation") or "").strip()))
            print(f"[extract] {package} -> {ts_file.name}  条目 {len(messages)}（未译 {untranslated}）")
    return 1 if failures else 0


def _read_ts(path: Path) -> Dict[str, Dict[str, str]]:
    """解析 .ts，返回 ``{context: {source: translation}}``（跳过未翻译项）。"""
    tree = ET.parse(path)
    root = tree.getroot()
    collected: Dict[str, Dict[str, str]] = {GENERAL: {}, "_language": {"": root.get("language", "")}}
    for context in root.findall("context"):
        name = (context.findtext("name") or GENERAL).strip() or GENERAL
        bucket = collected.setdefault(name, {})
        for message in context.findall("message"):
            source = message.findtext("source") or ""
            node = message.find("translation")
            if node is None or not source:
                continue
            translation = (node.text or "").strip()
            if not translation or node.get("type") == "unfinished":
                continue
            bucket[source] = translation
    return collected


def _toml_quote(text: str) -> str:
    """转义为 TOML 基本字符串。

    注意：**必须**转义换行/回车/制表符——TOML 的双引号字符串里不允许出现裸换行，
    否则整个语言包会解析失败（实测：一个多行译文就让 `tomllib` 报错，导致语言包 0 条、
    界面上的未译条目变成空白）。
    """
    escaped = (text.replace("\\", "\\\\")
                   .replace('"', '\\"')
                   .replace("\r", "\\r")
                   .replace("\n", "\\n")
                   .replace("\t", "\\t"))
    return '"' + escaped + '"'


def cmd_pack(args) -> int:
    """把 ``.ts`` 编译成运行时用的 TOML 语言包（承担 lrelease 的职责）。"""
    packages = args.packages or list(CORE_PACKAGES)
    generated = 0
    for package in packages:
        package_dir = repo_package_dir(package)
        if package_dir is None:
            continue
        target_dir = package_dir.joinpath(*TRANSLATIONS_DIRNAME)
        for ts_file in sorted(target_dir.glob(f"{package}_*.ts")):
            contexts = _read_ts(ts_file)
            language = (contexts.pop("_language", {}).get("", "") or "").strip()
            if not language:
                # pylupdate6 生成的 .ts 不带 language 属性（Qt Linguist 才会写），
                # 因此从文件名推断：<包名>_<语言>.ts
                stem = ts_file.stem
                if stem.startswith(f"{package}_"):
                    language = stem[len(package) + 1:]
            if not language:
                print(f"跳过 {ts_file.name}：缺少 language 属性")
                continue
            names = {"zh_CN": "简体中文", "zh_TW": "繁體中文", "en": "English"}
            lines = [
                "# 由 python -m pymodaq_utils.i18n pack 生成，请勿手工编辑；",
                f"# 源文件：{ts_file.name}（用 Qt Linguist 或文本编辑器维护 .ts）",
                "",
                "[meta]",
                f'language = "{language}"',
                f'name = "{names.get(language, language)}"',
                f'generated_from = "{ts_file.name}"',
                "",
                "[general]",
            ]
            general = contexts.pop(GENERAL, {})
            for source, translation in sorted(general.items()):
                lines.append(f"{_toml_quote(source)} = {_toml_quote(translation)}")
            for context, entries in sorted(contexts.items()):
                if not entries:
                    continue
                lines.append("")
                lines.append(f"[contexts.{_toml_quote(context)}]")
                for source, translation in sorted(entries.items()):
                    lines.append(f"{_toml_quote(source)} = {_toml_quote(translation)}")
            out_file = target_dir / f"{package}_{language}.toml"
            out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            total = len(general) + sum(len(v) for v in contexts.values())
            print(f"[pack] {ts_file.name} -> {out_file.name}  词条 {total}")
            generated += 1
    if not generated:
        print("没有可编译的 .ts（先运行 extract，并在 .ts 里填写译文）")
    return 0


def cmd_status(args) -> int:
    """打印语言与翻译进度。"""
    print("=" * 72)
    print(f"当前语言：{current_language()}    可用语言：{', '.join(available_languages())}")
    print("=" * 72)
    print("运行时语言包（TOML）：")
    found = False
    for language in available_languages():
        pack = load_pack(language, refresh=True)
        if pack.entries or pack.sources:
            found = True
            names = ", ".join(path.name for path in pack.sources)
            print(f"  {language:<8} 词条 {pack.entries:>5}    来源：{names or '（无）'}")
    if not found:
        print("  （无：还没有生成任何语言包）")

    print("\n作者格式（.ts）：")
    if repo_root() is None:
        print("  （不在仓库布局中，跳过）")
        return 0
    rows = 0
    for package in CORE_PACKAGES:
        package_dir = repo_package_dir(package)
        if package_dir is None:
            continue
        target_dir = package_dir.joinpath(*TRANSLATIONS_DIRNAME)
        for ts_file in sorted(target_dir.glob("*.ts")):
            messages = ET.parse(ts_file).getroot().findall(".//message")
            translated = 0
            for message in messages:
                node = message.find("translation")
                if node is not None and (node.text or "").strip() and node.get("type") != "unfinished":
                    translated += 1
            ratio = translated / len(messages) if messages else 0.0
            print(f"  {ts_file.name:<34} {translated:>5}/{len(messages):<5} ({ratio:5.1%})")
            rows += 1
    if not rows:
        print("  （还没有 .ts：先运行 python -m pymodaq_utils.i18n extract）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pymodaq_utils.i18n", description="PyMoDAQ 国际化工具")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="用 pylupdate6 从源码提取 tr() 字符串到 .ts")
    extract.add_argument("--packages", nargs="*", help="只处理这些包")
    extract.add_argument("--languages", nargs="*", help="目标语言（默认 zh_CN）")
    extract.add_argument("--keep-obsolete", action="store_true", help="保留过时条目")
    extract.add_argument("--verbose", action="store_true")
    extract.set_defaults(func=cmd_extract)

    pack = sub.add_parser("pack", help="把 .ts 编译成运行时用的 TOML 语言包")
    pack.add_argument("--packages", nargs="*", help="只处理这些包")
    pack.set_defaults(func=cmd_pack)

    status = sub.add_parser("status", help="查看语言与翻译进度")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
