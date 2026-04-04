"""
Mod解析器模块
提供通用的Mod解析接口，具体实现由游戏适配器提供

设计原则：
- 解析器仅负责解析，不负责存储
- Mod实例统一由ModManager存储和管理
- 插件异常不会导致程序崩溃

遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
"""

import logging
from typing import List, Optional

from yh_mods_manager_sdk import I18nProtocol, Mod, GamePaths

logger = logging.getLogger(__name__)


class ModParser:
    """Mod解析器包装类
    
    职责：
    1. 委托游戏适配器解析Mod
    2. 提供游戏版本信息
    3. 捕获插件异常，保护主程序
    
    不负责：
    - Mod实例存储（由ModManager负责）
    - Mod查询（由ModManager负责）
    """

    def __init__(self, paths: GamePaths, game_adapter=None,
                 i18n: Optional["I18nProtocol"] = None):
        self._paths = paths
        self._game_adapter = game_adapter
        self._i18n = i18n
        self._actual_parser = None
        self._last_error: Optional[str] = None

    @property
    def paths(self) -> GamePaths:
        """获取路径配置"""
        return self._paths

    @property
    def game_dir_path(self) -> str:
        return self._paths.game_dir_path

    @property
    def workshop_dir_path(self) -> str:
        return self._paths.workshop_dir_path

    @property
    def local_mod_dir_path(self) -> str:
        return self._paths.local_mod_dir_path

    @property
    def last_error(self) -> Optional[str]:
        """获取最后一次错误信息"""
        return self._last_error

    def _get_actual_parser(self):
        if self._actual_parser is None and self._game_adapter:
            try:
                self._actual_parser = self._game_adapter.get_mod_parser(
                    self._paths,
                    i18n=self._i18n
                )
            except TypeError as e:
                self._last_error = f"插件接口版本不兼容: {e}"
                logger.error(f"Plugin get_mod_parser() signature mismatch: {e}")
            except Exception as e:
                self._last_error = f"创建解析器失败: {e}"
                logger.error(f"Failed to create mod parser from plugin: {e}")
        return self._actual_parser

    @property
    def game_version(self) -> str:
        parser = self._get_actual_parser()
        if parser:
            try:
                return parser.game_version
            except Exception as e:
                logger.error(f"Failed to get game version: {e}")
        return ""

    def scan_all_mods(self) -> List["Mod"]:
        """扫描所有Mod，返回列表（不存储）
        
        异常安全：插件崩溃不会影响主程序
        """
        parser = self._get_actual_parser()
        if parser:
            try:
                return parser.scan_all_mods()
            except Exception as e:
                self._last_error = f"扫描Mod失败: {e}"
                logger.error(f"Plugin scan_all_mods() failed: {e}", exc_info=True)
        return []


def create_mod_parser(game_adapter, paths: GamePaths,
                      i18n: Optional["I18nProtocol"] = None) -> ModParser:
    """创建Mod解析器
    
    Args:
        game_adapter: 游戏适配器
        paths: 游戏路径配置（GamePaths聚合类）
        i18n: 国际化管理器
    """
    return ModParser(
        paths=paths,
        game_adapter=game_adapter,
        i18n=i18n
    )
