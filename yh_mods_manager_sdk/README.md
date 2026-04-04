# VibeUI Plugin SDK

插件开发SDK，提供插件开发所需的所有接口、类型定义和基类。

## 安装

```bash
pip install vibe-ui-plugin-sdk
```

## 功能特性

- **完全解耦**：插件开发者无需获取主程序源码
- **类型安全**：完整的类型提示支持
- **双插件体系**：支持游戏插件和功能插件

## 快速开始

### 功能插件示例

```python
from yh_mods_manager_sdk import (
    FeaturePlugin,
    PluginMenuItem,
    PluginEventType,
    PluginEvent,
    Mod,
)
from typing import List, Tuple, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from yh_mods_manager_sdk import ManagerCollectionProtocol


class MyPlugin(FeaturePlugin):
    """我的功能插件"""
    
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "My Plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR = "Your Name"
    PLUGIN_DESCRIPTION = "A sample feature plugin"
    
    def get_menu_items(self) -> List[PluginMenuItem]:
        """添加菜单项"""
        return [
            PluginMenuItem(
                id="my_action",
                label="My Action",
                action_id="do_something",
                shortcut="Ctrl+M",
            )
        ]
    
    @staticmethod
    def get_subscribed_events() -> List[PluginEventType]:
        """订阅事件"""
        return [PluginEventType.MOD_LIST_CHANGED]
    
    def on_initialize(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """初始化插件"""
        mod_manager = manager_collection.get_mod_manager()
        if mod_manager:
            mods = mod_manager.get_all_mods()
            self._logger.info(f"Loaded {len(mods)} mods")
        return True, ""
    
    def on_menu_action(self, action_id: str, manager_collection: "ManagerCollectionProtocol") -> Optional[Any]:
        """处理菜单动作"""
        if action_id == "do_something":
            self._logger.info("Action triggered!")
            return {"success": True}
        return None
    
    def on_event(self, event: PluginEvent) -> None:
        """处理事件"""
        if event.event_type == PluginEventType.MOD_LIST_CHANGED:
            mods = event.get("mods", [])
            self._logger.info(f"Mod list changed, now has {len(mods)} mods")
```

### 游戏适配器示例

```python
from yh_mods_manager_sdk import (
    GameAdapter,
    PluginConfig,
    ModParserBase,
    Mod,
    ModType,
    GamePaths,
    ModIDUtils,
    I18nProtocol,
    ManagerCollectionProtocol,
)
from typing import Optional, List, Tuple
import os
import subprocess


class MyGameParser(ModParserBase):
    """游戏Mod解析器
    
    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL,
                   workshop_id: Optional[str] = None) -> Optional[Mod]:
        """解析单个Mod"""
        mod_info_path = os.path.join(mod_path, self.MOD_METADATA_FILE)
        if not os.path.exists(mod_info_path):
            return None

        try:
            import json
            with open(mod_info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            original_id = data.get("id", os.path.basename(mod_path))
            mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)

            return Mod(
                id=mod_id,
                original_id=original_id,
                name=data.get("name", original_id),
                version=data.get("version", ""),
                path=mod_path,
                mod_type=mod_type,
                workshop_id=workshop_id,
                depended_modules=data.get("dependencies", []),
            )
        except Exception as e:
            self._logger.error(f"Failed to parse mod: {mod_path}, error: {e}")
            return None


class MyGameAdapter(GameAdapter):
    """游戏适配器
    
    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def get_mod_parser(self, paths: GamePaths,
                       i18n: Optional[I18nProtocol] = None) -> ModParserBase:
        """获取Mod解析器
        
        Args:
            paths: 游戏路径配置（GamePaths聚合类）
            i18n: 国际化管理器（可选）
            
        Returns:
            Mod解析器实例
        """
        return MyGameParser(
            config=self._config,
            paths=paths,
            i18n=i18n
        )

    def launch_game_native(self, manager_collection: ManagerCollectionProtocol) -> Tuple[bool, str]:
        """本地启动游戏
        
        Args:
            manager_collection: 管理者集合
            
        Returns:
            (是否启动成功, 错误信息)
        """
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "Config manager not available"

        game_dir = config_manager.get_game_dir_path()
        if not game_dir or not os.path.exists(game_dir):
            return False, "Game directory not found"

        executable = self._find_executable(game_dir)
        if executable:
            try:
                subprocess.Popen([executable], cwd=game_dir)
                return True, ""
            except Exception as e:
                return False, str(e)

        return False, "Executable not found"

    def launch_game_steam(self, manager_collection: ManagerCollectionProtocol) -> Tuple[bool, str]:
        """通过Steam启动游戏
        
        Args:
            manager_collection: 管理者集合
            
        Returns:
            (是否启动成功, 错误信息)
        """
        if not self.game_steam_app_id:
            return False, "Steam App ID not configured"

        steam_uri = f"steam://rungameid/{self.game_steam_app_id}"
        try:
            subprocess.Popen([steam_uri], shell=True)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _find_executable(self, game_dir: str) -> Optional[str]:
        """查找游戏可执行文件"""
        exec_paths = self._get_executable_paths()
        for rel_path in exec_paths:
            full_path = os.path.join(game_dir, rel_path)
            if os.path.exists(full_path):
                return full_path
        return None

    def _get_executable_paths(self) -> List[str]:
        """获取可执行文件路径列表"""
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_executable_paths()
        return []
```

## API 参考

### 核心类型

- `Mod` - Mod数据类
- `ModType` - Mod类型枚举
- `ModIssueStatus` - Mod问题状态
- `GamePaths` - 游戏路径配置类

### 插件基类

- `PluginBase` - 插件基类
- `GameAdapter` - 游戏适配器基类
- `FeaturePlugin` - 功能插件基类
- `ModParserBase` - Mod解析器基类
- `GameDetectorBase` - 游戏检测器基类

### 事件系统

- `PluginEventType` - 事件类型枚举
- `PluginEvent` - 事件数据类
- `PluginEventBus` - 事件总线

### 协议接口

- `ManagerCollectionProtocol` - 管理者集合协议
- `ModManagerProtocol` - Mod管理器协议
- `ConfigManagerProtocol` - 配置管理器协议
- `I18nProtocol` - 国际化管理器协议
- `ThemeManagerProtocol` - 主题管理器协议

## 许可证

AGPL v3 License
