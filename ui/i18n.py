"""
多语言国际化支持模块
支持可扩展的多语言架构，包括插件翻译
使用 JsonSerializeManager 统一管理 JSON 序列化

优化说明：
- 采用延迟加载策略，只在需要时加载翻译文件
- 由于语言设置只在重启后生效，运行时无需加载所有语言
"""

import logging
import os
from enum import Enum
from typing import Dict, Optional

from PyQt6.QtCore import QTranslator, QLibraryInfo

from core.json_serializer import get_json_manager
from ui.styles import get_ui_constant_dict
from utils.file_utils import get_resource_path

logger = logging.getLogger(__name__)


class Language(Enum):
    """支持的语言列表"""
    ZH_CN = "zh_CN"
    ZH_TW = "zh_TW"
    EN_US = "en_US"
    JA_JP = "ja_JP"
    KO_KR = "ko_KR"
    DE_DE = "de_DE"
    FR_FR = "fr_FR"
    RU_RU = "ru_RU"


class I18nManager:
    """多语言管理器"""

    DEFAULT_LANGUAGE = Language.ZH_CN

    LANGUAGE_NAMES = {
        Language.ZH_CN: "简体中文",
        Language.ZH_TW: "繁體中文",
        Language.EN_US: "English",
        Language.JA_JP: "日本語",
        Language.KO_KR: "한국어",
        Language.DE_DE: "Deutsch",
        Language.FR_FR: "Français",
        Language.RU_RU: "Русский",
    }

    def __init__(self, config_dir: str = "config", initial_language: Language = None):
        self.config_dir = config_dir
        self.i18n_dir = os.path.join(config_dir, "i18n")
        self._translations: Dict[str, Dict[str, str]] = {}
        self._plugin_translations: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._current_language: Language = initial_language or self.DEFAULT_LANGUAGE

        self._json = get_json_manager(config_dir)

        self._ensure_translation_loaded(self._current_language)
        if self._current_language != self.DEFAULT_LANGUAGE:
            self._ensure_translation_loaded(self.DEFAULT_LANGUAGE)

    def _ensure_translation_loaded(self, lang: Language):
        lang_code = lang.value
        if lang_code in self._translations:
            return
        self._load_translation(lang)

    def _load_translation(self, lang: Language):
        filepath = os.path.join(self.i18n_dir, f"{lang.value}.json")
        if not os.path.exists(filepath):
            resource_i18n_dir = get_resource_path(os.path.join("config", "i18n"))
            filepath = os.path.join(resource_i18n_dir, f"{lang.value}.json")
        self._translations[lang.value] = self._json.load_from_file(filepath, default={})

    def _save_translation(self, lang: Language):
        filepath = os.path.join(self.i18n_dir, f"{lang.value}.json")
        self._json.save_to_file(self._translations.get(lang.value, {}), filepath)

    def load_plugin_translations(self, plugin_id: str, i18n_dir: str):
        if not os.path.exists(i18n_dir):
            return

        if plugin_id not in self._plugin_translations:
            self._plugin_translations[plugin_id] = {}

        lang_code = self._current_language.value
        filepath = os.path.join(i18n_dir, f"{lang_code}.json")
        self._plugin_translations[plugin_id][lang_code] = self._json.load_from_file(filepath, default={})
        if lang_code != self.DEFAULT_LANGUAGE.value:
            default_filepath = os.path.join(i18n_dir, f"{self.DEFAULT_LANGUAGE.value}.json")
            self._plugin_translations[plugin_id][self.DEFAULT_LANGUAGE.value] = self._json.load_from_file(
                default_filepath, default={})

    def unload_plugin_translations(self, plugin_id: str):
        if plugin_id in self._plugin_translations:
            del self._plugin_translations[plugin_id]

    def set_language(self, lang: Language):
        self._current_language = lang

    def get_language(self) -> Language:
        return self._current_language

    def get_language_name(self, lang: Language = None) -> str:
        if lang is None:
            lang = self._current_language
        return self.LANGUAGE_NAMES.get(lang, lang.value)

    def get_available_languages(self) -> Dict[Language, str]:
        return self.LANGUAGE_NAMES.copy()

    def translate(self, key: str, *args) -> str:
        lang_code = self._current_language.value
        self._ensure_translation_loaded(self._current_language)

        if key.startswith("plugin."):
            parts = key.split(".", 2)
            if len(parts) >= 3:
                plugin_id = parts[1]
                plugin_key = parts[2]
                plugin_trans = self._plugin_translations.get(plugin_id, {})
                translations = plugin_trans.get(lang_code, {})
                text = translations.get(plugin_key)
                if text is None:
                    main_translations = self._translations.get(lang_code, {})
                    text = main_translations.get(plugin_key, key)
            else:
                text = key
        else:
            translations = self._translations.get(lang_code, {})
            text = translations.get(key, key)

        if args:
            try:
                text = text.format(*args)
            except (IndexError, KeyError) as e:
                logger.debug(f"Translation format error for key '{key}': {e}")

        return text

    def tr(self, key: str, *args) -> str:
        return self.translate(key, *args)

    def update_translation(self, lang: Language, key: str, value: str):
        lang_code = lang.value
        if lang_code not in self._translations:
            self._translations[lang_code] = {}
        self._translations[lang_code][key] = value
        self._save_translation(lang)

    def get_all_translations(self, lang: Language = None) -> Dict[str, str]:
        if lang is None:
            lang = self._current_language
        return self._translations.get(lang.value, {}).copy()


_i18n_instance: Optional[I18nManager] = None


def init_i18n(config_dir: str = "config", initial_language: Language = None) -> I18nManager:
    global _i18n_instance
    _i18n_instance = I18nManager(config_dir, initial_language)
    return _i18n_instance


def get_i18n() -> I18nManager:
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nManager()
    return _i18n_instance


def tr(key: str, *args) -> str:
    return get_i18n().tr(key, *args)


def set_language(lang: Language):
    get_i18n().set_language(lang)


def get_language() -> Language:
    return get_i18n().get_language()


_qt_translator: Optional[QTranslator] = None


def get_qt_translation_file(lang_code: str) -> str:
    qt_lang_map = get_ui_constant_dict("qt_translations", {})
    return qt_lang_map.get(lang_code, qt_lang_map.get("default", "qtbase_en"))


def load_qt_translations(app, lang_code: str) -> bool:
    global _qt_translator

    translation_name = get_qt_translation_file(lang_code)
    translations_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)

    _qt_translator = QTranslator()

    if _qt_translator.load(translation_name, translations_dir):
        app.installTranslator(_qt_translator)
        logger.info(f"Qt translations loaded for language: {lang_code}")
        return True

    import PyQt6
    pyqt6_dir = os.path.dirname(PyQt6.__file__)
    alt_translations_dir = os.path.join(pyqt6_dir, "Qt6", "translations")

    if os.path.exists(alt_translations_dir):
        if _qt_translator.load(translation_name, alt_translations_dir):
            app.installTranslator(_qt_translator)
            logger.info(f"Qt translations loaded for language: {lang_code}")
            return True

    logger.debug(f"Qt translations not found for language: {lang_code}")
    return False
