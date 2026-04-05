# 插件开发指南

本指南介绍如何为夜海泛用模组管理器开发插件。

## 概述

本工具采用双插件体系：

| 插件类型 | 基类 | 互斥性 | 用途 |
|---------|------|--------|------|
| 游戏插件 | `GameAdapter` | 同一时间只能启用一个 | 为特定游戏提供 Mod 元数据解析和启动功能 |
| 功能插件 | `FeaturePlugin` | 可以同时启用多个 | 扩展程序功能 |

### 游戏插件必须实现

- **元数据解析** - 解析游戏元数据和 Mod 元数据（就像读取 Mod 的"名片"）
- **启动功能** - 启动游戏，大部分情况下需要将软件内部排序好的 Mod 配置写入游戏的官方 Mod 配置文件

> ⚠️ **ID 转换注意**：软件内部使用带后缀的 ID 来区分本地 Mod 和 Steam Mod，格式类似 `原始ID@local` 或 `原始ID@steam`。在写入游戏配置文件时，需要使用 `original_id` 字段获取原始 ID*（你也可以直接裁）。

### 所有插件都可以

- 添加菜单项、工具栏按钮、自定义面板
- 订阅事件（Mod 列表变化、游戏切换等）
- 自定义高亮规则、过滤规则
- 独立配置存储
- 扩展错误检测、扩展右键菜单

### 游戏插件还可以

- 解析存档文件（从存档导入 Mod 配置）
- 解析外部配置文件
- 自定义拓扑排序逻辑

## 环境准备

### 安装 SDK

SDK 会随 Release 一并发布，下载后本地安装即可：

```bash
pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl
```

### SDK 结构

```
yh_mods_manager_sdk/
├── __init__.py          # 公共接口导出
├── plugin_base.py       # 插件基类定义
├── mod.py               # Mod 数据类
├── enum_types.py        # 枚举类型
├── enum_extension.py    # 枚举扩展
├── events.py            # 事件系统
├── menu.py              # 菜单定义
├── config.py            # 配置类型
├── protocols.py         # 协议接口
├── utils.py             # 工具函数
├── plugin_packer.py     # 插件打包工具
└── py.typed             # 类型标记
```

### 依赖限制

> ⚠️ **重要**：主程序假定用户完全不懂 Python，无法手动安装依赖。因此插件必须开箱即用。

插件只能使用以下三类库：

| 类别 | 说明 | 示例 |
|------|------|------|
| **Python 标准库** | Python 内置库，无需安装 | `os`, `json`, `logging`, `typing`, `subprocess` |
| **SDK** | 本项目提供的开发包 | `yh_mods_manager_sdk` |
| **主程序已打包的库** | 主程序 EXE 中已包含的第三方库 | `PyQt6`, `watchdog` |

**禁止使用**任何需要额外 `pip install` 的第三方库，否则用户运行时会报错。

#### 如果确实需要其他库

如果某个第三方库对插件功能**非常必要且通用性强**，可以申请将其加入主程序的打包列表。申请方式：

1. 在项目 GitHub Issues 中提出需求
2. 说明库的用途、大小、必要性
3. 经评估后可能加入主程序打包

主程序会控制打包体积，只接受真正必要的库。

## 快速开始

> 💡 **AI 友好开发**：本项目本身就是和 AI 合作开发的，所以插件开发也非常适合交给 AI 来完成。你只需要告诉 AI 你的游戏 Mod 结构，AI 就能帮你生成一个可用的游戏插件。基础插件只需 400-500 行代码，包含存档读取等进阶功能也只需约 800 行。

### 最简游戏插件

一个最简游戏插件只需要两个文件：

**manifest.json** - 插件清单：

```json
{
    "plugin_id": "MyGame",
    "plugin_version": "1.0.0",
    "entry_point": "adapter",
    "game_info": {
        "steam_app_id": "123456",
        "game_id": "MyGame",
        "default_name": "My Game"
    },
    "mod_parser": {
        "game_core_folder": "Mods",
        "local_mods_folder": "Mods",
        "game_core_id": "Core",
        "mod_metadata_file": "mod_info.json"
    }
}
```

**adapter.py** - 游戏适配器：

```python
import logging
import subprocess
from typing import Optional, List, Tuple
from yh_mods_manager_sdk import (
    GameAdapter,
    ModParserBase,
    Mod,
    ModType,
    GamePaths,
    ModIDUtils,
    I18nProtocol,
    ManagerCollectionProtocol,
)

logger = logging.getLogger(__name__)


class MyGameParser(ModParserBase):
    """Mod 元数据解析器"""
    
    def _parse_mod(
        self, 
        mod_path: str, 
        mod_type: ModType = ModType.LOCAL,
        workshop_id: Optional[str] = None
    ) -> Optional[Mod]:
        """解析 Mod 元数据文件，就像读取 Mod 的"名片""""
        mod_info_path = os.path.join(mod_path, self.MOD_METADATA_FILE)
        if not os.path.exists(mod_info_path):
            return None
        
        try:
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
                mod_type=self._determine_mod_type(original_id, mod_type),
                workshop_id=workshop_id,
                depended_modules=data.get("dependencies", []),
            )
        except Exception as e:
            logger.error(f"解析 Mod 失败: {mod_path}, 错误: {e}")
            return None


class MyGameAdapter(GameAdapter):
    """游戏适配器"""
    
    def get_mod_parser(
        self,
        paths: GamePaths,
        i18n: Optional[I18nProtocol] = None
    ) -> ModParserBase:
        return MyGameParser(config=self._config, paths=paths, i18n=i18n)
    
    def _write_mod_config(
        self, 
        manager_collection: ManagerCollectionProtocol
    ) -> Tuple[bool, str]:
        """将 Mod 配置写入游戏配置文件
        
        注意：需要使用 original_id 而非内部 id
        """
        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return False, "Mod 管理器不可用"
        
        enabled_mods = mod_manager.get_enabled_mods()
        original_ids = [mod.original_id for mod in enabled_mods]
        
        config_path = os.path.join(
            manager_collection.get_config_manager().get_game_config_dir_path(),
            "mods_config.json"
        )
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"enabled_mods": original_ids}, f, indent=2)
            return True, ""
        except Exception as e:
            return False, f"写入配置失败: {e}"
    
    def launch_game_native(
        self, 
        manager_collection: ManagerCollectionProtocol
    ) -> Tuple[bool, str]:
        """本地启动游戏"""
        success, error = self._write_mod_config(manager_collection)
        if not success:
            return False, error
        
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "配置管理器不可用"
        
        game_dir = config_manager.get_game_dir_path()
        if not game_dir or not os.path.exists(game_dir):
            return False, "游戏目录不存在"
        
        executable = os.path.join(game_dir, "MyGame.exe")
        if os.path.exists(executable):
            subprocess.Popen([executable], cwd=game_dir)
            return True, ""
        
        return False, "找不到游戏可执行文件"
    
    def launch_game_steam(
        self, 
        manager_collection: ManagerCollectionProtocol
    ) -> Tuple[bool, str]:
        """通过 Steam 启动游戏"""
        success, error = self._write_mod_config(manager_collection)
        if not success:
            return False, error
        
        if not self.game_steam_app_id:
            return False, "未配置 Steam App ID"
        
        steam_uri = f"steam://rungameid/{self.game_steam_app_id}"
        subprocess.Popen([steam_uri], shell=True)
        return True, ""
```

## 游戏插件开发

### 目录结构

```
plugins_dev/game/MyGame/
├── manifest.json        # 插件清单（必需）
├── adapter.py           # 游戏适配器（必需）
└── i18n/                # 国际化（可选）
    ├── zh_CN.json
    └── en_US.json
```

### 清单文件详解

```json
{
    "plugin_id": "MyGame",
    "plugin_version": "1.0.0",
    "entry_point": "adapter",
    
    "game_info": {
        "steam_app_id": "123456",
        "game_id": "MyGame",
        "default_name": "My Awesome Game",
        "description": "游戏描述",
        "icon": "mygame",
        "author": "Game Studio",
        "website": "https://example.com"
    },
    
    "path_validation": {
        "game_folder_names": {
            "windows": ["MyGame", "My Game"],
            "linux": ["MyGame"],
            "macos": ["MyGame.app"]
        },
        "executable_paths": {
            "windows": ["MyGame.exe", "bin/MyGame.exe"],
            "linux": ["MyGame", "bin/MyGame"],
            "macos": ["Contents/MacOS/MyGame"]
        },
        "config_dir_paths": {
            "windows": ["{USERPROFILE}/Documents/MyGame"],
            "linux": ["{HOME}/.config/MyGame"],
            "macos": []
        }
    },
    
    "mod_parser": {
        "game_core_folder": "Mods",
        "local_mods_folder": "Mods",
        "game_core_id": "Core",
        "game_dlc_ids": ["DLC1", "DLC2"],
        "mod_metadata_file": "mod_info.json"
    },
    
    "default_settings": {
        "auto_sort": true,
        "launch_steam": true,
        "auto_detect_paths": true
    },
    
    "custom_data": {
        "custom_key": "custom_value"
    }
}
```

#### game_info 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `steam_app_id` | 是 | Steam 应用 ID |
| `game_id` | 是 | 游戏唯一标识 |
| `default_name` | 是 | 游戏显示名称 |
| `description` | 否 | 游戏描述 |
| `icon` | 否 | 图标标识 |
| `author` | 否 | 游戏作者 |
| `website` | 否 | 官方网站 |

#### mod_parser 字段

| 字段 | 说明 |
|------|------|
| `game_core_folder` | 核心 Mod 文件夹名 |
| `local_mods_folder` | 本地 Mod 文件夹名 |
| `game_core_id` | 核心 Mod ID |
| `game_dlc_ids` | DLC Mod ID 列表 |
| `mod_metadata_file` | Mod 元数据文件名 |

### 存档解析（可选）

如果游戏支持从存档导入 Mod 配置，可以实现存档解析：

```python
from typing import List
from yh_mods_manager_sdk import SaveParseResult, SaveParserCapability, ManagerCollectionProtocol

class MyGameAdapter(GameAdapter):
    
    @staticmethod
    def get_save_parser_capabilities() -> List[SaveParserCapability]:
        return [
            SaveParserCapability(
                supported_extensions=[".sav"],
                description="存档文件 (*.sav)"
            )
        ]
    
    @staticmethod
    def parse_save_file(
        file_path: str, 
        manager_collection: ManagerCollectionProtocol = None,
        **kwargs
    ) -> SaveParseResult:
        """解析存档文件，提取 Mod 列表"""
        try:
            with open(file_path, 'rb') as f:
                data = parse_save_format(f)
            
            mod_ids = data.get("mods", [])
            return SaveParseResult(success=True, mod_order=mod_ids)
        except Exception as e:
            return SaveParseResult.error(str(e))
```

## 功能插件开发

### 目录结构

```
plugins_dev/feature/my_plugin/
├── manifest.json        # 插件清单
├── plugin.py            # 插件实现
└── i18n/                # 国际化（可选）
```

### 清单文件

```json
{
    "plugin_id": "my_plugin",
    "plugin_type": "feature",
    "plugin_version": "1.0.0",
    "entry_point": "plugin",
    "name": "My Plugin",
    "description": "插件描述",
    "author": "Your Name"
}
```

### 插件实现

```python
import logging
from typing import List, Tuple, Optional, Any, TYPE_CHECKING
from yh_mods_manager_sdk import (
    FeaturePlugin,
    PluginMenuItem,
    PluginEventType,
    PluginEvent,
    PluginResult,
)

if TYPE_CHECKING:
    from yh_mods_manager_sdk import ManagerCollectionProtocol

logger = logging.getLogger(__name__)


class MyPlugin(FeaturePlugin):
    """我的功能插件"""
    
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "My Plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR = "Your Name"
    PLUGIN_DESCRIPTION = "插件描述"
    
    @staticmethod
    def get_menu_items() -> List[PluginMenuItem]:
        """添加菜单项"""
        return [
            PluginMenuItem(
                id="my_action",
                label="执行操作",
                action_id="do_something",
                shortcut="Ctrl+M",
            ),
        ]
    
    @staticmethod
    def get_subscribed_events() -> List[PluginEventType]:
        """订阅事件"""
        return [
            PluginEventType.MOD_LIST_CHANGED,
            PluginEventType.MOD_ORDER_CHANGED,
        ]
    
    def on_initialize(
        self, 
        manager_collection: "ManagerCollectionProtocol"
    ) -> Tuple[bool, str]:
        """初始化插件"""
        mod_manager = manager_collection.get_mod_manager()
        if mod_manager:
            mods = mod_manager.get_all_mods()
            logger.info(f"已加载 {len(mods)} 个 Mod")
        return True, ""
    
    @staticmethod
    def on_menu_action(
        action_id: str, 
        manager_collection: "ManagerCollectionProtocol"
    ) -> Optional[Any]:
        """处理菜单动作"""
        if action_id == "do_something":
            logger.info("执行操作")
            return PluginResult.success({"success": True})
        return None
    
    def on_event(self, event: PluginEvent) -> None:
        """处理事件"""
        if event.event_type == PluginEventType.MOD_LIST_CHANGED:
            mods = event.get("mods", [])
            logger.info(f"Mod 列表已变更，现有 {len(mods)} 个 Mod")
```

## API 参考

### ManagerCollectionProtocol

管理者集合，提供访问各种管理器的接口：

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `get_config_manager()` | ConfigManagerProtocol | 配置管理器 |
| `get_mod_manager()` | ModManagerProtocol | Mod 管理器 |
| `get_game_metadata_manager()` | GameMetadataManagerProtocol | 游戏元数据管理器 |
| `get_mod_metadata_manager()` | ModMetadataManagerProtocol | Mod 元数据管理器 |
| `get_highlight_rule_manager()` | HighlightRuleManagerProtocol | 高亮规则管理器 |
| `get_mod_filter_manager()` | ModFilterManagerProtocol | 过滤规则管理器 |
| `get_i18n()` | I18nProtocol | 国际化管理器 |
| `get_theme_manager()` | ThemeManagerProtocol | 主题管理器 |
| `is_ready()` | bool | 检查核心管理器是否就绪 |

### ModManagerProtocol

Mod 管理器：

| 方法 | 说明 |
|------|------|
| `get_all_mods()` | 获取所有 Mod |
| `get_enabled_mods()` | 获取已启用的 Mod |
| `get_disabled_mods()` | 获取已禁用的 Mod |
| `get_mod_by_id(mod_id)` | 根据 ID 获取 Mod |
| `enable_mod(mod_id)` | 启用 Mod |
| `disable_mod(mod_id)` | 禁用 Mod |
| `move_mod(mod_id, new_index)` | 移动 Mod 到新位置 |

### Mod 数据类

```python
@dataclass
class Mod:
    id: str                           # 内部 ID（带后缀，如 MyMod@local）
    original_id: str = ""             # 原始 ID（游戏使用的真实 ID）
    name: str = ""                    # Mod 名称
    version: str = "1.0.0"            # 版本号
    supported_versions: List[str] = []  # 支持的游戏版本
    authors: List[str] = []           # 作者列表
    official_tags: List[str] = []     # 官方标签
    path: str = ""                    # 路径
    mod_type: ModType = ModType.LOCAL # 类型
    workshop_id: Optional[str] = None # 创意工坊 ID
    preview_image: Optional[str] = None  # 预览图路径
    description: Optional[str] = None # 描述
    
    depended_modules: List[str] = []      # 依赖
    load_before: List[str] = []           # 在此之前加载
    load_after: List[str] = []            # 在此之后加载
    incompatible_modules: List[str] = []  # 不兼容
    
    is_enabled: bool = False          # 是否启用
    order_index: int = 0              # 排序索引
    custom_meta: ModCustomMeta = None # 用户自定义元数据（标签、备注等）
    issue_status: ModIssueStatus = ModIssueStatus.NORMAL  # 问题状态
```

> 💡 **ID 字段说明**：
> - `id`：软件内部使用的唯一标识，格式为 `原始ID@类型`（如 `MyMod@local`）
> - `original_id`：游戏实际使用的 ID，写入游戏配置文件时应使用此字段
> - 使用 `ModIDUtils.generate_mod_id(original_id, mod_type)` 生成内部 ID

### 事件类型

| 事件类型 | 说明 |
|---------|------|
| `GAME_CHANGED` | 游戏切换 |
| `GAME_LAUNCHED` | 游戏启动 |
| `GAME_CLOSED` | 游戏关闭 |
| `MOD_LIST_CHANGED` | Mod 列表变更 |
| `MOD_ORDER_CHANGED` | Mod 顺序变更 |
| `MOD_ENABLED` | Mod 启用 |
| `MOD_DISABLED` | Mod 禁用 |
| `CONFIG_CHANGED` | 配置变更 |
| `THEME_CHANGED` | 主题变更 |
| `LANGUAGE_CHANGED` | 语言变更 |
| `PLUGIN_LOADED` | 插件加载 |
| `PLUGIN_UNLOADED` | 插件卸载 |
| `UI_READY` | UI 就绪 |
| `SHUTDOWN` | 关闭 |

## 国际化

### 创建翻译文件

`i18n/zh_CN.json`:

```json
{
    "plugin_name": "我的插件",
    "action_label": "执行操作",
    "success_message": "操作成功"
}
```

### 使用翻译

```python
class MyPlugin(FeaturePlugin):
    def on_initialize(self, manager_collection):
        i18n = manager_collection.get_i18n()
        if i18n:
            i18n.load_plugin_translations(self.PLUGIN_ID, "i18n目录路径")
            label = i18n.tr("action_label")
```

## 调试

### 日志输出

使用 Python 标准 logging 模块：

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(FeaturePlugin):
    def some_method(self):
        logger.debug("调试信息")
        logger.info("普通信息")
        logger.warning("警告信息")
        logger.error("错误信息")
```

### 测试流程

插件开发已独立于主程序，开发者可以在自己的项目中进行开发和测试。

**方式一：独立开发**

1. 创建独立的插件项目目录
2. 安装 SDK：`pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl`
3. 编写插件代码
4. 使用 `plugin_packer` 打包插件
5. 将打包后的插件放入主程序的 `plugins` 目录测试

**方式二：在主程序目录开发**

1. 在主程序的 `plugins_dev/feature/` 或 `plugins_dev/game/` 目录创建插件
2. 启动主程序进行测试
3. 开发完成后打包发布

## 示例插件和打包工具

> 📦 **示例仓库**：[YHModsManagerPlugins](https://github.com/IdealNightOcean/YHModsManagerPlugins)

示例仓库包含：

- **示例游戏插件** - 参考实际插件的结构和实现
- **示例功能插件** - 学习功能插件的开发模式
- **打包脚本** - 使用 `plugin_packer` 打包插件的脚本

## 错误检测

### 静态错误与动态错误

Mod 错误分为两类，插件开发者需要合理控制检测时机：

| 类型 | 特点 | 示例 | 检测时机 |
|------|------|------|---------|
| **静态错误** | 一旦发生不会自动消失 | 文件不完整、游戏版本不兼容 | Mod 扫描时检测一次 |
| **动态错误** | 可能随操作而变化 | 排序错误、依赖未启用 | Mod 列表/顺序变化时重新检测 |

### 检测建议

- **静态错误**：在 `static_error_check` 方法中检测，只运行一次
- **动态错误**：订阅 `MOD_LIST_CHANGED`、`MOD_ORDER_CHANGED` 等事件，在事件回调中重新检测
- **性能考虑**：动态错误检测可能频繁触发，避免耗时操作

```python
class MyGameAdapter(GameAdapter):
    
    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        """静态错误检测 - 只在扫描时运行一次"""
        for mod in mods:
            if not self._check_mod_integrity(mod):
                mod.add_issue(ModIssueStatus.INCOMPLETE)
            
            if not self._check_version_compatibility(mod, game_metadata.game_version):
                mod.add_issue(ModIssueStatus.VERSION_MISMATCH)
    
    def on_event(self, event: PluginEvent) -> None:
        """动态错误检测 - 响应列表变化"""
        if event.event_type in (PluginEventType.MOD_LIST_CHANGED, PluginEventType.MOD_ORDER_CHANGED):
            self._check_dynamic_issues()
```

## 最佳实践

1. **单一职责** - 每个插件只负责一个明确的功能
2. **错误处理** - 所有操作都应有适当的错误处理
3. **日志记录** - 关键操作记录日志
4. **资源清理** - 在 `on_shutdown` 中清理资源
5. **路径管理** - 使用 `GamePaths` 聚合类，避免离散路径参数
