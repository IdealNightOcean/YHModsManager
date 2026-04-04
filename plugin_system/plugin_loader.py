"""
插件加载器
支持热加载和打包插件
支持双插件体系：游戏插件(互斥) + 功能插件(不互斥)
"""

import importlib
import importlib.util
import json
import logging
import os
import shutil
import sys
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Callable, Tuple

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from watchdog.observers import Observer

from core.manager_collection import ManagerCollection
from yh_mods_manager_sdk import GameAdapter, PluginConfig, FeaturePlugin, PluginType, PLUGIN_MANIFEST, PLUGIN_EXTENSION
from utils.file_utils import FileUtils, get_app_data_dir, get_resource_path

logger = logging.getLogger(__name__)

PROJECT_ROOT = get_resource_path("")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@dataclass
class PluginInfo:
    """插件信息"""
    plugin_id: str
    plugin_version: str
    plugin_path: str
    config: PluginConfig
    plugin_type: PluginType = PluginType.GAME
    adapter_class: Type[GameAdapter] = None
    feature_plugin_class: Type[FeaturePlugin] = None
    checksum: str = ""
    is_loaded: bool = False


class PluginLoader:
    """插件加载器
    
    支持双插件体系：
    - 游戏插件(GamePlugin)：互斥，同一时间仅能启用一个
    - 功能插件(FeaturePlugin)：不互斥，可同时启用多个
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.plugins: Dict[str, PluginInfo] = {}
        self.adapters: Dict[str, GameAdapter] = {}
        self._feature_plugins: Dict[str, FeaturePlugin] = {}
        self._current_adapter: Optional[GameAdapter] = None
        self._plugins_dir: str = ""
        self._game_plugins_dir: str = ""
        self._feature_plugins_dir: str = ""
        self._observer: Optional[Observer] = None
        self._on_plugin_loaded: Optional[Callable[[str], None]] = None
        self._on_plugin_unloaded: Optional[Callable[[str], None]] = None
        self._temp_dirs: List[str] = []

    def initialize(self, plugins_dir: str = None):
        """初始化插件加载器
        
        Args:
            plugins_dir: 插件目录，默认为程序所在目录下的plugins文件夹
        """
        if plugins_dir is None:
            plugins_dir = os.path.join(get_app_data_dir(), "plugins")
        self._plugins_dir = plugins_dir

        self._game_plugins_dir = os.path.join(plugins_dir, "game")
        self._feature_plugins_dir = os.path.join(plugins_dir, "feature")

        os.makedirs(self._game_plugins_dir, exist_ok=True)
        os.makedirs(self._feature_plugins_dir, exist_ok=True)

        self.load_all_plugins()

    def load_all_plugins(self) -> List[str]:
        """加载所有插件包（仅从plugins目录加载.vpkg文件）"""
        loaded = []

        if os.path.exists(self._game_plugins_dir):
            for filename in os.listdir(self._game_plugins_dir):
                if filename.endswith(PLUGIN_EXTENSION):
                    plugin_path = os.path.join(self._game_plugins_dir, filename)
                    try:
                        if self.load_plugin(plugin_path, PluginType.GAME):
                            loaded.append(filename)
                    except Exception as e:
                        logger.error(f"Failed to load game plugin {filename}: {e}")

        if os.path.exists(self._feature_plugins_dir):
            for filename in os.listdir(self._feature_plugins_dir):
                if filename.endswith(PLUGIN_EXTENSION):
                    plugin_path = os.path.join(self._feature_plugins_dir, filename)
                    try:
                        if self.load_plugin(plugin_path, PluginType.FEATURE):
                            loaded.append(filename)
                    except Exception as e:
                        logger.error(f"Failed to load feature plugin {filename}: {e}")

        return loaded

    def load_plugin(self, plugin_path: str, plugin_type: PluginType = PluginType.GAME) -> bool:
        """加载单个插件包（支持游戏插件和功能插件）
        
        Args:
            plugin_path: 插件包路径
            plugin_type: 插件类型（由目录位置决定）
        """
        checksum = FileUtils.calculate_checksum(plugin_path)

        with zipfile.ZipFile(plugin_path, 'r') as zf:
            if PLUGIN_MANIFEST not in zf.namelist():
                raise ValueError(f"Invalid plugin: missing {PLUGIN_MANIFEST}")

            manifest_data = json.loads(zf.read(PLUGIN_MANIFEST).decode('utf-8'))
            plugin_id = manifest_data.get("plugin_id", "")

            if not plugin_id:
                raise ValueError("Invalid plugin: missing plugin_id")

            if plugin_id in self.plugins:
                self.unload_plugin(plugin_id)

            cache_dir = os.path.join(get_app_data_dir(), "cache", "plugins_code")
            os.makedirs(cache_dir, exist_ok=True)
            temp_dir = os.path.join(cache_dir, f"plugin_{plugin_id}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            os.makedirs(temp_dir, exist_ok=True)
            self._temp_dirs.append(temp_dir)

            zf.extractall(temp_dir)

            from core.serializers import PluginConfigSerializer
            serializer = PluginConfigSerializer()
            config = serializer.deserialize(manifest_data)

            adapter_class = None
            feature_plugin_class = None

            if plugin_type == PluginType.GAME:
                adapter_class = self._load_adapter_class(temp_dir, manifest_data)
            else:
                feature_plugin_class = self._load_feature_plugin_class(temp_dir, manifest_data)

            plugin_info = PluginInfo(
                plugin_id=plugin_id,
                plugin_version=manifest_data.get("plugin_version", "1.0.0"),
                plugin_path=plugin_path,
                config=config,
                plugin_type=plugin_type,
                adapter_class=adapter_class,
                feature_plugin_class=feature_plugin_class,
                checksum=checksum,
                is_loaded=True
            )

            self.plugins[plugin_id] = plugin_info

            if plugin_type == PluginType.GAME and adapter_class:
                self.adapters[plugin_id] = adapter_class(config)
            elif plugin_type == PluginType.FEATURE and feature_plugin_class:
                self._feature_plugins[plugin_id] = feature_plugin_class()

            i18n_dir = os.path.join(temp_dir, "i18n")
            if os.path.exists(i18n_dir):
                from ui.i18n import get_i18n
                get_i18n().load_plugin_translations(plugin_id, i18n_dir)

            if self._on_plugin_loaded:
                self._on_plugin_loaded(plugin_id)

            return True

    @staticmethod
    def _load_adapter_class(temp_dir: str, manifest: dict) -> Optional[Type[GameAdapter]]:
        """加载游戏适配器类"""
        entry_point = manifest.get("entry_point", "adapter")
        plugin_id = manifest.get('plugin_id', 'unknown')

        adapter_file = os.path.join(temp_dir, f"{entry_point}.py")
        if not os.path.exists(adapter_file):
            return None

        package_name = f"plugin_pkg_{plugin_id}"
        module_name = f"{package_name}.{entry_point}"

        for name in [module_name, package_name, entry_point]:
            if name in sys.modules:
                del sys.modules[name]

        init_file = os.path.join(temp_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("")

        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        parent_dir = os.path.dirname(temp_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        plugin_dir_name = os.path.basename(temp_dir)
        actual_package_name = plugin_dir_name
        actual_module_name = f"{actual_package_name}.{entry_point}"

        try:
            module = importlib.import_module(actual_module_name)
        except ImportError as e:
            logger.debug(f"Failed to import module {actual_module_name}: {e}")
            spec = importlib.util.spec_from_file_location(
                module_name, 
                adapter_file,
                submodule_search_locations=[temp_dir]
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, GameAdapter) and obj is not GameAdapter:
                return obj

        return None

    @staticmethod
    def _load_feature_plugin_class(temp_dir: str, manifest: dict) -> Optional[Type[FeaturePlugin]]:
        """加载功能插件类"""
        entry_point = manifest.get("entry_point", "plugin")
        plugin_id = manifest.get('plugin_id', 'unknown')

        plugin_file = os.path.join(temp_dir, f"{entry_point}.py")
        if not os.path.exists(plugin_file):
            return None

        package_name = f"feature_plugin_pkg_{plugin_id}"
        module_name = f"{package_name}.{entry_point}"

        for name in [module_name, package_name, entry_point]:
            if name in sys.modules:
                del sys.modules[name]

        init_file = os.path.join(temp_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("")

        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        parent_dir = os.path.dirname(temp_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        plugin_dir_name = os.path.basename(temp_dir)
        actual_package_name = plugin_dir_name
        actual_module_name = f"{actual_package_name}.{entry_point}"

        try:
            module = importlib.import_module(actual_module_name)
        except ImportError as e:
            logger.debug(f"Failed to import module {actual_module_name}: {e}")
            spec = importlib.util.spec_from_file_location(
                module_name, 
                plugin_file,
                submodule_search_locations=[temp_dir]
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, FeaturePlugin) and obj is not FeaturePlugin:
                return obj

        return None

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self.plugins:
            return False

        plugin_info = self.plugins[plugin_id]

        if self._on_plugin_unloaded:
            self._on_plugin_unloaded(plugin_id)

        from core.manager_collection import get_manager_collection
        manager_collection = get_manager_collection()

        highlight_manager = manager_collection.get_highlight_rule_manager()
        if highlight_manager:
            highlight_manager.unregister_plugin_rules(plugin_id)

        filter_manager = manager_collection.get_mod_filter_manager()
        if filter_manager:
            filter_manager.unregister_plugin_filters(plugin_id)

        if plugin_info.plugin_type == PluginType.GAME:
            if plugin_id in self.adapters:
                adapter = self.adapters[plugin_id]
                adapter.on_shutdown()
                del self.adapters[plugin_id]
            if self._current_adapter and self._current_adapter == self.adapters.get(plugin_id):
                self._current_adapter = None
        else:
            if plugin_id in self._feature_plugins:
                feature_plugin = self._feature_plugins[plugin_id]
                feature_plugin.on_shutdown()
                del self._feature_plugins[plugin_id]

        from ui.i18n import get_i18n
        get_i18n().unload_plugin_translations(plugin_id)

        module_name = f"plugin_{plugin_id}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        feature_module_name = f"feature_plugin_{plugin_id}"
        if feature_module_name in sys.modules:
            del sys.modules[feature_module_name]

        del self.plugins[plugin_id]

        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """重新加载插件"""
        if plugin_id not in self.plugins:
            return False

        plugin_path = self.plugins[plugin_id].plugin_path
        self.unload_plugin(plugin_id)
        return self.load_plugin(plugin_path)

    def get_adapter(self, plugin_id: str = None) -> Optional[GameAdapter]:
        """获取游戏适配器"""
        if plugin_id:
            return self.adapters.get(plugin_id)
        return self._current_adapter

    def get_available_plugins(self) -> List[str]:
        """获取所有可用插件ID"""
        return list(self.plugins.keys())

    def get_available_game_plugins(self) -> List[str]:
        """获取所有可用的游戏插件ID"""
        return [pid for pid, info in self.plugins.items() if info.plugin_type == PluginType.GAME]

    def get_available_feature_plugin_ids(self) -> List[str]:
        """获取所有可用的功能插件ID"""
        return [pid for pid, info in self.plugins.items() if info.plugin_type == PluginType.FEATURE]

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugins.get(plugin_id)

    def get_game_plugins_dir(self) -> str:
        """获取游戏插件目录"""
        return self._game_plugins_dir

    def get_feature_plugins_dir(self) -> str:
        """获取功能插件目录"""
        return self._feature_plugins_dir

    def get_feature_plugin(self, plugin_id: str) -> Optional[FeaturePlugin]:
        """获取功能插件实例"""
        return self._feature_plugins.get(plugin_id)

    def get_available_feature_plugins(self) -> Dict[str, FeaturePlugin]:
        """获取所有已启用的功能插件实例
        
        只返回未被禁用的功能插件
        """
        disabled_plugins = self._get_disabled_feature_plugins()
        return {
            plugin_id: plugin
            for plugin_id, plugin in self._feature_plugins.items()
            if plugin_id not in disabled_plugins
        }

    def get_all_feature_plugins(self) -> Dict[str, FeaturePlugin]:
        """获取所有功能插件实例（包含禁用的）
        
        用于设置界面显示所有插件
        """
        return self._feature_plugins.copy()

    def set_current_plugin(self, plugin_id: str) -> bool:
        """设置当前游戏插件（游戏插件互斥）
        
        切换时会自动清理旧游戏相关的元数据
        """
        if plugin_id not in self.adapters:
            return False

        old_adapter = self._current_adapter
        old_game_id = old_adapter.game_id if old_adapter else None

        self._current_adapter = self.adapters[plugin_id]

        if old_game_id and old_game_id != plugin_id:
            from core.manager_collection import get_manager_collection
            manager_collection = get_manager_collection()
            if manager_collection:
                manager_collection.clear_game_data(old_game_id)

        return True

    def get_current_adapter(self) -> Optional[GameAdapter]:
        """获取当前游戏适配器"""
        return self._current_adapter

    def initialize_feature_plugins(self, manager_collection: "ManagerCollection", config_dir: str = None) -> Dict[
        str, Tuple[bool, str]]:
        """初始化所有功能插件
        
        遵循生命周期：
        1. on_pre_initialize() - 预初始化
        2. load_config() - 加载配置
        3. on_initialize() - 初始化
        4. 订阅事件
        5. on_startup_complete() - 启动完成
        
        Args:
            manager_collection: 管理者集合
            config_dir: 配置目录路径
        
        Returns:
            Dict[plugin_id, (success, error_message)]
        """
        from .plugin_events import get_event_bus

        results = {}
        event_bus = get_event_bus()

        disabled_plugins = self._get_disabled_feature_plugins()

        for plugin_id, feature_plugin in self._feature_plugins.items():
            if plugin_id in disabled_plugins:
                results[plugin_id] = (True, "disabled")
                logger.info(f"Feature plugin {plugin_id} is disabled, skipping initialization")
                continue

            try:
                context = {
                    "plugin_dir": self.plugins.get(plugin_id, PluginInfo(
                        plugin_id=plugin_id,
                        plugin_version="",
                        plugin_path="",
                        config=None
                    )).plugin_path,
                    "config_dir": config_dir or os.path.join(get_app_data_dir(), "config"),
                }

                success, error = feature_plugin.on_pre_initialize(context)
                if not success:
                    results[plugin_id] = (False, f"pre_initialize failed: {error}")
                    continue

                if config_dir:
                    feature_plugin.load_config(config_dir)
                    default_config = feature_plugin.get_default_config()
                    for key, value in default_config.items():
                        if feature_plugin.get_config(key) is None:
                            feature_plugin.set_config(key, value)

                success, error = feature_plugin.on_initialize(manager_collection)
                if not success:
                    results[plugin_id] = (False, f"initialize failed: {error}")
                    continue

                subscribed_events = feature_plugin.get_subscribed_events()
                for event_type in subscribed_events:
                    event_bus.subscribe(event_type, feature_plugin.on_event)

                feature_plugin.on_startup_complete(context)

                results[plugin_id] = (True, "")

            except Exception as e:
                logger.error(f"Failed to initialize feature plugin {plugin_id}: {e}", exc_info=True)
                results[plugin_id] = (False, str(e))

        return results

    @staticmethod
    def _get_disabled_feature_plugins() -> List[str]:
        """获取被禁用的功能插件列表"""
        from core.config_manager import ConfigManager
        try:
            temp_config = ConfigManager()
            return temp_config.get_disabled_feature_plugins()
        except Exception as e:
            logger.warning(f"Failed to get disabled feature plugins: {e}")
            return []

    def is_feature_plugin_enabled(self, plugin_id: str) -> bool:
        """检查功能插件是否启用"""
        disabled_plugins = self._get_disabled_feature_plugins()
        return plugin_id not in disabled_plugins

    def get_feature_plugin_status(self) -> Dict[str, bool]:
        """获取所有功能插件的启用状态"""
        disabled_plugins = self._get_disabled_feature_plugins()
        return {
            plugin_id: plugin_id not in disabled_plugins
            for plugin_id in self._feature_plugins.keys()
        }

    def shutdown_feature_plugins(self) -> None:
        """关闭所有功能插件"""
        from .plugin_events import get_event_bus

        event_bus = get_event_bus()

        for plugin_id, feature_plugin in self._feature_plugins.items():
            try:
                subscribed_events = feature_plugin.get_subscribed_events()
                for event_type in subscribed_events:
                    event_bus.unsubscribe(event_type, feature_plugin.on_event)

                feature_plugin.save_config()
                feature_plugin.on_shutdown()
            except Exception as e:
                logger.error(f"Error shutting down feature plugin {plugin_id}: {e}")

    def notify_game_changed(self, game_id: str) -> None:
        """通知所有功能插件游戏已切换"""
        from .plugin_events import get_event_bus, PluginEventType

        for feature_plugin in self._feature_plugins.values():
            feature_plugin.on_game_changed(game_id)

        get_event_bus().publish(PluginEventType.GAME_CHANGED, {"game_id": game_id})

    def start_hot_reload(self, on_loaded: Callable[[str], None] = None,
                         on_unloaded: Callable[[str], None] = None):
        """启动热加载监听"""
        self._on_plugin_loaded = on_loaded
        self._on_plugin_unloaded = on_unloaded

        if self._observer:
            self.stop_hot_reload()

        event_handler = _PluginFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(event_handler, self._plugins_dir, recursive=False)
        self._observer.start()

    def stop_hot_reload(self):
        """停止热加载监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def cleanup(self):
        """清理临时文件"""
        self.stop_hot_reload()

        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_dirs.clear()


class _PluginFileHandler(FileSystemEventHandler):
    """插件文件变化处理器"""

    def __init__(self, loader: PluginLoader):
        self.loader = loader
        super().__init__()

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory and event.src_path.endswith(PLUGIN_EXTENSION):
            try:
                self.loader.load_plugin(event.src_path)
            except Exception as e:
                logger.error(f"Failed to load new plugin: {e}")

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory and event.src_path.endswith(PLUGIN_EXTENSION):
            for plugin_id, info in list(self.loader.plugins.items()):
                if info.plugin_path == event.src_path:
                    new_checksum = FileUtils.calculate_checksum(event.src_path)
                    if new_checksum != info.checksum:
                        try:
                            self.loader.reload_plugin(plugin_id)
                        except Exception as e:
                            logger.error(f"Failed to reload plugin {plugin_id}: {e}")
                    break


def get_plugin_loader() -> PluginLoader:
    """获取插件加载器单例"""
    return PluginLoader()
