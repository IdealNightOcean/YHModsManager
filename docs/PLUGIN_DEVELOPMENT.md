# Plugin Development Guide

This guide introduces how to develop plugins for NightOcean's Mods Manager.

[中文文档](插件开发指南.md)

## Overview

This tool adopts a dual plugin system:

| Plugin Type | Base Class | Mutual Exclusivity | Purpose |
|-------------|------------|-------------------|---------|
| Game Plugin | `GameAdapter` | Only one can be enabled at a time | Provides Mod metadata parsing and launch functionality for specific games |
| Feature Plugin | `FeaturePlugin` | Multiple can be enabled simultaneously | Extends program functionality |

### Game Plugins Must Implement

- **Metadata Parsing** - Parse game metadata and Mod metadata (like reading a Mod's "business card")
- **Launch Functionality** - Launch the game; in most cases, needs to write the internally sorted Mod configuration to the game's official Mod configuration file

> ⚠️ **ID Conversion Note**: The software internally uses suffixed IDs to distinguish between local Mods and Steam Mods, formatted like `OriginalID@local` or `OriginalID@steam`. When writing to game configuration files, use the `original_id` field to get the original ID *(you can also directly strip it)*.

### All Plugins Can

- Add menu items, toolbar buttons, custom panels
- Subscribe to events (Mod list changes, game switching, etc.)
- Custom highlight rules, filter rules
- Independent configuration storage
- Extend error detection, extend context menu

### Game Plugins Can Also

- Parse save files (import Mod configuration from saves)
- Parse external configuration files
- Custom topological sorting logic

## Environment Setup

### Installing the SDK

The SDK is released alongside the main program. Download and install locally:

```bash
pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl
```

### SDK Structure

```
yh_mods_manager_sdk/
├── __init__.py          # Public interface exports
├── plugin_base.py       # Plugin base class definitions
├── mod.py               # Mod data classes
├── enum_types.py        # Enum types
├── enum_extension.py    # Enum extensions
├── events.py            # Event system
├── menu.py              # Menu definitions
├── config.py            # Configuration types
├── protocols.py         # Protocol interfaces
├── utils.py             # Utility functions
├── plugin_packer.py     # Plugin packing tool
└── py.typed             # Type marker
```

### Dependency Restrictions

> ⚠️ **Important**: The main program assumes users have no Python knowledge and cannot manually install dependencies. Therefore, plugins must work out-of-the-box.

Plugins can only use the following three types of libraries:

| Category | Description | Examples |
|----------|-------------|----------|
| **Python Standard Library** | Python built-in libraries, no installation needed | `os`, `json`, `logging`, `typing`, `subprocess` |
| **SDK** | Development kit provided by this project | `yh_mods_manager_sdk` |
| **Libraries Packaged with Main Program** | Third-party libraries already included in the main program EXE | `PyQt6`, `watchdog` |

**Prohibited** from using any third-party libraries that require additional `pip install`, otherwise users will encounter errors at runtime.

#### If You Really Need Other Libraries

If a third-party library is **very necessary for plugin functionality and has strong generality**, you can apply to add it to the main program's packaging list. Application method:

1. Submit a request in the project GitHub Issues
2. Explain the library's purpose, size, and necessity
3. After evaluation, it may be added to the main program packaging

The main program controls packaging size and only accepts truly necessary libraries.

## Quick Start

> 💡 **AI-Friendly Development**: This project itself is developed in collaboration with AI, so plugin development is also very suitable for AI completion. You just need to tell AI your game's Mod structure, and AI can generate a usable game plugin for you. A basic plugin only needs 400-500 lines of code, and even advanced features like save file reading only need about 800 lines.

### Minimal Game Plugin

A minimal game plugin only needs two files:

**manifest.json** - Plugin manifest:

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

**adapter.py** - Game adapter:

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
    """Mod metadata parser"""
    
    def _parse_mod(
        self, 
        mod_path: str, 
        mod_type: ModType = ModType.LOCAL,
        workshop_id: Optional[str] = None
    ) -> Optional[Mod]:
        """Parse Mod metadata file, like reading a Mod's 'business card'"""
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
            logger.error(f"Failed to parse Mod: {mod_path}, Error: {e}")
            return None


class MyGameAdapter(GameAdapter):
    """Game adapter"""
    
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
        """Write Mod configuration to game config file
        
        Note: Use original_id instead of internal id
        """
        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return False, "Mod manager unavailable"
        
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
            return False, f"Failed to write config: {e}"
    
    def launch_game_native(
        self, 
        manager_collection: ManagerCollectionProtocol
    ) -> Tuple[bool, str]:
        """Launch game locally"""
        success, error = self._write_mod_config(manager_collection)
        if not success:
            return False, error
        
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "Config manager unavailable"
        
        game_dir = config_manager.get_game_dir_path()
        if not game_dir or not os.path.exists(game_dir):
            return False, "Game directory does not exist"
        
        executable = os.path.join(game_dir, "MyGame.exe")
        if os.path.exists(executable):
            subprocess.Popen([executable], cwd=game_dir)
            return True, ""
        
        return False, "Game executable not found"
    
    def launch_game_steam(
        self, 
        manager_collection: ManagerCollectionProtocol
    ) -> Tuple[bool, str]:
        """Launch game via Steam"""
        success, error = self._write_mod_config(manager_collection)
        if not success:
            return False, error
        
        if not self.game_steam_app_id:
            return False, "Steam App ID not configured"
        
        steam_uri = f"steam://rungameid/{self.game_steam_app_id}"
        subprocess.Popen([steam_uri], shell=True)
        return True, ""
```

## Game Plugin Development

### Directory Structure

```
plugins_dev/game/MyGame/
├── manifest.json        # Plugin manifest (required)
├── adapter.py           # Game adapter (required)
└── i18n/                # Internationalization (optional)
    ├── zh_CN.json
    └── en_US.json
```

### Manifest File Details

```json
{
    "plugin_id": "MyGame",
    "plugin_version": "1.0.0",
    "entry_point": "adapter",
    
    "game_info": {
        "steam_app_id": "123456",
        "game_id": "MyGame",
        "default_name": "My Awesome Game",
        "description": "Game description",
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

#### game_info Fields

| Field | Required | Description |
|-------|----------|-------------|
| `steam_app_id` | Yes | Steam App ID |
| `game_id` | Yes | Game unique identifier |
| `default_name` | Yes | Game display name |
| `description` | No | Game description |
| `icon` | No | Icon identifier |
| `author` | No | Game author |
| `website` | No | Official website |

#### mod_parser Fields

| Field | Description |
|-------|-------------|
| `game_core_folder` | Core Mod folder name |
| `local_mods_folder` | Local Mod folder name |
| `game_core_id` | Core Mod ID |
| `game_dlc_ids` | DLC Mod ID list |
| `mod_metadata_file` | Mod metadata file name |

### Save File Parsing (Optional)

If the game supports importing Mod configuration from save files, you can implement save file parsing:

```python
from typing import List
from yh_mods_manager_sdk import SaveParseResult, SaveParserCapability, ManagerCollectionProtocol

class MyGameAdapter(GameAdapter):
    
    @staticmethod
    def get_save_parser_capabilities() -> List[SaveParserCapability]:
        return [
            SaveParserCapability(
                supported_extensions=[".sav"],
                description="Save files (*.sav)"
            )
        ]
    
    @staticmethod
    def parse_save_file(
        file_path: str, 
        manager_collection: ManagerCollectionProtocol = None,
        **kwargs
    ) -> SaveParseResult:
        """Parse save file, extract Mod list"""
        try:
            with open(file_path, 'rb') as f:
                data = parse_save_format(f)
            
            mod_ids = data.get("mods", [])
            return SaveParseResult(success=True, mod_order=mod_ids)
        except Exception as e:
            return SaveParseResult.error(str(e))
```

## Feature Plugin Development

### Directory Structure

```
plugins_dev/feature/my_plugin/
├── manifest.json        # Plugin manifest
├── plugin.py            # Plugin implementation
└── i18n/                # Internationalization (optional)
```

### Manifest File

```json
{
    "plugin_id": "my_plugin",
    "plugin_type": "feature",
    "plugin_version": "1.0.0",
    "entry_point": "plugin",
    "name": "My Plugin",
    "description": "Plugin description",
    "author": "Your Name"
}
```

### Plugin Implementation

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
    """My feature plugin"""
    
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "My Plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR = "Your Name"
    PLUGIN_DESCRIPTION = "Plugin description"
    
    @staticmethod
    def get_menu_items() -> List[PluginMenuItem]:
        """Add menu items"""
        return [
            PluginMenuItem(
                id="my_action",
                label="Execute Action",
                action_id="do_something",
                shortcut="Ctrl+M",
            ),
        ]
    
    @staticmethod
    def get_subscribed_events() -> List[PluginEventType]:
        """Subscribe to events"""
        return [
            PluginEventType.MOD_LIST_CHANGED,
            PluginEventType.MOD_ORDER_CHANGED,
        ]
    
    def on_initialize(
        self, 
        manager_collection: "ManagerCollectionProtocol"
    ) -> Tuple[bool, str]:
        """Initialize plugin"""
        mod_manager = manager_collection.get_mod_manager()
        if mod_manager:
            mods = mod_manager.get_all_mods()
            logger.info(f"Loaded {len(mods)} Mods")
        return True, ""
    
    @staticmethod
    def on_menu_action(
        action_id: str, 
        manager_collection: "ManagerCollectionProtocol"
    ) -> Optional[Any]:
        """Handle menu action"""
        if action_id == "do_something":
            logger.info("Executing action")
            return PluginResult.success({"success": True})
        return None
    
    def on_event(self, event: PluginEvent) -> None:
        """Handle event"""
        if event.event_type == PluginEventType.MOD_LIST_CHANGED:
            mods = event.get("mods", [])
            logger.info(f"Mod list changed, now has {len(mods)} Mods")
```

## API Reference

### ManagerCollectionProtocol

Manager collection, provides interfaces to access various managers:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_config_manager()` | ConfigManagerProtocol | Config manager |
| `get_mod_manager()` | ModManagerProtocol | Mod manager |
| `get_game_metadata_manager()` | GameMetadataManagerProtocol | Game metadata manager |
| `get_mod_metadata_manager()` | ModMetadataManagerProtocol | Mod metadata manager |
| `get_highlight_rule_manager()` | HighlightRuleManagerProtocol | Highlight rule manager |
| `get_mod_filter_manager()` | ModFilterManagerProtocol | Filter rule manager |
| `get_i18n()` | I18nProtocol | Internationalization manager |
| `get_theme_manager()` | ThemeManagerProtocol | Theme manager |
| `is_ready()` | bool | Check if core managers are ready |

### ModManagerProtocol

Mod manager:

| Method | Description |
|--------|-------------|
| `get_all_mods()` | Get all Mods |
| `get_enabled_mods()` | Get enabled Mods |
| `get_disabled_mods()` | Get disabled Mods |
| `get_mod_by_id(mod_id)` | Get Mod by ID |
| `enable_mod(mod_id)` | Enable Mod |
| `disable_mod(mod_id)` | Disable Mod |
| `move_mod(mod_id, new_index)` | Move Mod to new position |

### Mod Data Class

```python
@dataclass
class Mod:
    id: str                           # Internal ID (with suffix, e.g., MyMod@local)
    original_id: str = ""             # Original ID (real ID used by game)
    name: str = ""                    # Mod name
    version: str = "1.0.0"            # Version number
    supported_versions: List[str] = []  # Supported game versions
    authors: List[str] = []           # Author list
    official_tags: List[str] = []     # Official tags
    path: str = ""                    # Path
    mod_type: ModType = ModType.LOCAL # Type
    workshop_id: Optional[str] = None # Workshop ID
    preview_image: Optional[str] = None  # Preview image path
    description: Optional[str] = None # Description
    
    depended_modules: List[str] = []      # Dependencies
    load_before: List[str] = []           # Load before these
    load_after: List[str] = []            # Load after these
    incompatible_modules: List[str] = []  # Incompatible
    
    is_enabled: bool = False          # Is enabled
    order_index: int = 0              # Order index
    custom_meta: ModCustomMeta = None # User custom metadata (tags, notes, etc.)
    issue_status: ModIssueStatus = ModIssueStatus.NORMAL  # Issue status
```

> 💡 **ID Field Notes**:
> - `id`: Unique identifier used internally by the software, format is `OriginalID@Type` (e.g., `MyMod@local`)
> - `original_id`: The ID actually used by the game, use this field when writing to game config files
> - Use `ModIDUtils.generate_mod_id(original_id, mod_type)` to generate internal ID

### Event Types

| Event Type | Description |
|------------|-------------|
| `GAME_CHANGED` | Game switched |
| `GAME_LAUNCHED` | Game launched |
| `GAME_CLOSED` | Game closed |
| `MOD_LIST_CHANGED` | Mod list changed |
| `MOD_ORDER_CHANGED` | Mod order changed |
| `MOD_ENABLED` | Mod enabled |
| `MOD_DISABLED` | Mod disabled |
| `CONFIG_CHANGED` | Configuration changed |
| `THEME_CHANGED` | Theme changed |
| `LANGUAGE_CHANGED` | Language changed |
| `PLUGIN_LOADED` | Plugin loaded |
| `PLUGIN_UNLOADED` | Plugin unloaded |
| `UI_READY` | UI ready |
| `SHUTDOWN` | Shutdown |

## Internationalization

### Creating Translation Files

`i18n/zh_CN.json`:

```json
{
    "plugin_name": "My Plugin",
    "action_label": "Execute Action",
    "success_message": "Action successful"
}
```

### Using Translations

```python
class MyPlugin(FeaturePlugin):
    def on_initialize(self, manager_collection):
        i18n = manager_collection.get_i18n()
        if i18n:
            i18n.load_plugin_translations(self.PLUGIN_ID, "i18n_directory_path")
            label = i18n.tr("action_label")
```

## Debugging

### Log Output

Use Python's standard logging module:

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(FeaturePlugin):
    def some_method(self):
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
```

### Testing Process

Plugin development is now independent of the main program; developers can develop and test in their own projects.

**Method 1: Independent Development**

1. Create an independent plugin project directory
2. Install SDK: `pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl`
3. Write plugin code
4. Use `plugin_packer` to package the plugin
5. Put the packaged plugin into the main program's `plugins` directory for testing

**Method 2: Develop in Main Program Directory**

1. Create plugin in the main program's `plugins_dev/feature/` or `plugins_dev/game/` directory
2. Start the main program for testing
3. Package and release after development is complete

## Example Plugins and Packaging Tool

> 📦 **Example Repository**: [YHModsManagerPlugins](https://github.com/IdealNightOcean/YHModsManagerPlugins)

The example repository contains:

- **Example Game Plugins** - Reference actual plugin structure and implementation
- **Example Feature Plugins** - Learn feature plugin development patterns
- **Packaging Scripts** - Scripts using `plugin_packer` to package plugins

## Error Detection

### Static Errors vs Dynamic Errors

Mod errors are divided into two categories, plugin developers need to reasonably control detection timing:

| Type | Characteristic | Example | Detection Timing |
|------|----------------|---------|------------------|
| **Static Error** | Once occurred, won't automatically disappear | Incomplete files, game version incompatibility | Detect once during Mod scan |
| **Dynamic Error** | May change with operations | Sort order errors, dependencies not enabled | Re-detect when Mod list/order changes |

### Detection Recommendations

- **Static Errors**: Detect in `static_error_check` method, run only once
- **Dynamic Errors**: Subscribe to `MOD_LIST_CHANGED`, `MOD_ORDER_CHANGED` and other events, re-detect in event callbacks
- **Performance Consideration**: Dynamic error detection may trigger frequently, avoid time-consuming operations

```python
class MyGameAdapter(GameAdapter):
    
    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        """Static error detection - runs only once during scan"""
        for mod in mods:
            if not self._check_mod_integrity(mod):
                mod.add_issue(ModIssueStatus.INCOMPLETE)
            
            if not self._check_version_compatibility(mod, game_metadata.game_version):
                mod.add_issue(ModIssueStatus.VERSION_MISMATCH)
```

## Best Practices

### Code Organization

1. **Separation of Concerns** - Separate parsing logic, business logic, and UI logic
2. **Error Handling** - Use try-except to catch exceptions and log errors
3. **Type Hints** - Use Python type hints to improve code readability

### Performance Optimization

1. **Lazy Loading** - Load data only when needed
2. **Caching** - Cache parsed results to avoid repeated parsing
3. **Batch Operations** - Batch process when handling multiple Mods

### Compatibility

1. **Cross-Platform** - Consider path differences on different operating systems
2. **Encoding** - Use UTF-8 encoding to handle multi-language characters
3. **Path Management** - Use `GamePaths` aggregate class, avoid discrete path parameters
