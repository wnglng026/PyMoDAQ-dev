# -*- coding: utf-8 -*-
"""PyMoDAQ 国际化（i18n）的 Qt 侧：把 ``tr()`` 的查找接到语言包上。

为什么不用 ``.qm``
------------------
Qt 标准流程需要 ``lrelease`` 把 ``.ts`` 编译成二进制 ``.qm``，而 PyQt6 只自带 ``pylupdate6``
（本机实测无 ``lrelease``）。这里改为实现一个 Python 版 ``QTranslator``：

* ``.ts`` 仍是作者格式（``pylupdate6`` 提取，可用 Qt Linguist 翻译）；
* 编译目标改成 TOML 语言包（``python -m pymodaq_utils.i18n pack``）；
* :class:`PackTranslator.translate` 把 Qt 的 ``tr()`` 查找转到语言包查找。

好处：不依赖 ``lrelease``、语言包可 diff 评审、插件可自带语言包；Qt 自带控件的翻译
仍由 ``qtbase_<lang>.qm`` 提供（存在则自动加载）。

安装时机：``pymodaq_gui.qt_utils.mkQApp()`` 创建 QApplication 后立即安装，
因此所有 GUI 入口（pymodaq / dashboard / daq_viewer / daq_move / 扩展）自动生效。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from qtpy import QtCore, QtWidgets

from pymodaq_utils import i18n as core

_installed: List[QtCore.QTranslator] = []
_pack_translator: Optional["PackTranslator"] = None


class PackTranslator(QtCore.QTranslator):
    """用 TOML 语言包实现 QTranslator 的查找（覆盖虚拟方法 ``translate``）。"""

    def translate(self, context: str, source_text: str, disambiguation: str = None, n: int = -1) -> str:
        try:
            hit = core.lookup(source_text, context)
        except Exception:
            hit = None
        return hit or ""

    def isEmpty(self) -> bool:  # noqa: N802 - Qt 命名约定
        return core.load_pack().entries == 0


def _qt_translations_dir() -> Optional[Path]:
    """当前 Qt 绑定自带的翻译目录。"""
    from qtpy import API_NAME

    mapping = {
        "PyQt6": ("PyQt6", "Qt6"),
        "PyQt5": ("PyQt5", "Qt5"),
        "PySide6": ("PySide6", None),
        "PySide2": ("PySide2", None),
    }
    entry = mapping.get(API_NAME)
    if entry is None:
        return None
    module_name, sub = entry
    try:
        module = __import__(module_name)
    except Exception:
        return None
    base = Path(module.__file__).parent
    directory = base / sub / "translations" if sub else base / "translations"
    return directory if directory.is_dir() else None


def install_translators(app: QtWidgets.QApplication = None, language: str = None) -> str:
    """安装 L1（Qt 自带 ``.qm``）+ L2（PyMoDAQ 语言包）翻译器，返回生效语言。

    幂等：重复调用只刷新语言包（切换语言后调用即可重新查表）。
    """
    global _pack_translator
    app = app or QtWidgets.QApplication.instance()
    if app is None:
        return language or core.current_language()

    if language:
        core.set_language(language)
    current = core.current_language()

    if _pack_translator is None:
        _pack_translator = PackTranslator(app)
    if _pack_translator not in _installed:
        app.installTranslator(_pack_translator)
        _installed.append(_pack_translator)
    core.load_pack(current, refresh=True)  # 切换语言后立即生效

    if not any(getattr(t, "_pymodaq_qt_native", False) for t in _installed):
        directory = _qt_translations_dir()
        if directory is not None:
            for name in (f"qtbase_{current}", f"qt_{current}"):
                translator = QtCore.QTranslator(app)
                if translator.load(name, str(directory)):
                    translator._pymodaq_qt_native = True  # type: ignore[attr-defined]
                    app.installTranslator(translator)
                    _installed.append(translator)
    return current


def current_language() -> str:
    """当前生效语言。"""
    return core.current_language()


def switch_language(language: str, app: QtWidgets.QApplication = None) -> str:
    """运行中切换语言（已构建界面的文本不会自动刷新，建议重启界面）。"""
    return install_translators(app=app, language=language)
