# NightOcean's Mods Manager

**Game-Agnostic · Plugin-Driven**

[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)

[中文文档](README.md)

<div align="center">

![Main Interface Demo](docs/images/介绍.gif)

</div>

---

## Table of Contents

- [Introduction](#introduction)
- [Core Features](#core-features)
- [Plugin System](#plugin-system)
- [Quick Start](#quick-start)
- [Developer Guide](#developer-guide)
- [Contributing](#contributing)
- [License](#license)

---

## Introduction

NightOcean's Mods Manager is a **universal Mod management tool** that adopts a **plugin-driven architecture**. It is not bound to any specific game but supports various games through game plugins.

### Core Characteristics

| Feature | Description |
|---------|-------------|
| One Manager, Multiple Games | Manage Mods for multiple games with a single manager |
| Community Extension | The community can develop support plugins for any game |
| Feature Extension | Features can be continuously extended through plugins |

### Scope of Functionality

#### ✅ What It Can Do

This tool focuses on **Mod management and organization**:

- **View Information** - View Mod name, version, author, dependencies, and other information (requires plugins to correctly parse metadata)
- **Problem Detection** - Detect missing dependencies, load order errors, duplicate Mods, and other issues
- **Order Adjustment** - Adjust Mod load order through drag-and-drop or smart sorting
- **Profile Management** - Save multiple Mod configuration profiles and switch between them at any time

#### ❌ What It Cannot Do

| Limitation | Description |
|------------|-------------|
| Does Not Load Mods | Mods are actually loaded by the game; this tool only generates configuration files |
| Does Not Provide Downloads | No Mod download functionality; obtain Mods through Steam Workshop or other means |
| Limited Deep Features | Some games' deep customization features may not match dedicated managers |

### Suitable Scenarios

#### Suitable Mod Types

This tool is suitable for managing **non-intrusive Mods**:

| Characteristic | Description |
|----------------|-------------|
| Independent Directory | Each Mod has its own directory and does not directly overwrite game files |
| Metadata File | Mods come with description files containing name, version, dependencies, etc. |
| Unique Identifier | Different Mods can be distinguished by ID or folder name |

**Typical Examples:**

| Game | Mod Metadata File |
|------|-------------------|
| RimWorld | `About.xml` |
| Mount & Blade II: Bannerlord | `SubModule.xml` |
| Kenshi | `*.info` files |

> ⚠️ **Note**: For "intrusive Mods" that directly overwrite game files, this tool cannot manage them well.

> I think this tool has a promising future: if the plugin ecosystem can be perfected, for those indie games or games that lack deep Mod management support, external Mod order management can be quickly achieved through this tool.

#### Usage Recommendations

- **Single Game Scenario**: If you only manage one game and that game already has a dedicated manager, the dedicated manager may have more comprehensive features
- **Multi-Game Scenario**: If you play multiple Mod-heavy games simultaneously, or your favorite game doesn't have a dedicated manager, this tool is a good choice *(if someone develops plugins for it)*

### Development Advantages

The biggest advantage of this manager is that it is **not bound to any game**. Developing game plugins is very simple:

| Plugin Type | Lines of Code | Scope of Functionality |
|-------------|---------------|------------------------|
| Basic Plugin | 400-500 lines | Basic Mod metadata parsing and management |
| Advanced Plugin | ~800 lines | Includes advanced features like save file reading |

> 💡 **AI-Friendly Development**: This project is developed in collaboration with AI, and plugin development is also very suitable for AI completion. Just tell AI your game's Mod structure, and AI can generate a usable game plugin.

---

## Core Features

### Multi-Game Support

Supports multiple games through game plugins:

| Example Games | Steam App ID | Notes |
|---------------|--------------|-------|
| Mount & Blade II: Bannerlord | 261550 | Multiplayer and singleplayer separated |
| RimWorld | 294100 | Includes save file Mod order import |
| Kenshi | 233860 | Basic functionality only |

> 💡 Example game plugins can be obtained from the [Example Plugin Repository](https://github.com/IdealNightOcean/YHModsManagerPlugins).

**Want to support a new game?** Just write a game plugin, no need to modify the main program.

![Game Switching](docs/images/游戏切换.gif)

### Interface Design

| Feature | Description |
|---------|-------------|
| Dual-List Layout | Disabled on the left, enabled on the right, clear at a glance |
| Drag-and-Drop Sorting | Adjust load order by dragging |
| Dependency Visualization | Display dependencies between Mods through detailed info, highlighting, and dependency lines |
| Info Panel | View Mod details, tags, notes, etc. |

![Drag Sorting](docs/images/拖动排序.gif)

![Info Panel Management](docs/images/信息面板管理.gif)

### Management Features

#### Dependency Management

| Feature | Description |
|---------|-------------|
| Dependency Visualization | Display dependencies between Mods through detailed info, highlighting, and dependency lines |
| Simple Sorting | Automatically adjust order based on Mod-declared dependencies (for reference only) |
| Problem Detection | One-click detection of missing dependencies, order errors, and other issues |

![Dependency Line View](docs/images/依赖线查看.gif)

![Problem Detection](docs/images/问题监测.gif)

#### Profile Management

| Feature | Description |
|---------|-------------|
| Multiple Profiles | Save different Mod combinations for easy switching between playstyles |
| Import/Export | Easy to share and backup configurations |
| Import from Save | Some games support restoring Mod configurations from save files (requires plugin support) |

![MOD Profile Switching](docs/images/MOD配置切换.gif)

#### Personalized Marking

| Feature | Description |
|---------|-------------|
| Tag System | Add tags to Mods for easier filtering |
| Color Marking | Mark Mods with colors for instant recognition |
| Notes Feature | Add notes to Mods; sometimes nicknames are easier to remember |

![Custom Name](docs/images/备注名.gif)

### Search and Filter

| Feature | Description |
|---------|-------------|
| Keyword Search | Quickly find the Mod you want |
| Structured Search | Use syntax like `@tag=tagname`, `@author=author` |
| Type Filter | Filter by base game, DLC, Workshop, local Mod |

![Structured Search](docs/images/结构化搜索.gif)

### Themes and Languages

| Feature | Description |
|---------|-------------|
| Multiple Themes | Default theme, dark theme, etc. |
| Multiple Languages | Chinese, English, etc. |
| Font Adjustment | Adjust interface font size |

![Theme Switching](docs/images/主题切换.gif)

---

## Plugin System

The plugin system is the core feature of this tool.

### Architecture Design

Traditional Mod managers usually only support one game with fixed functionality. NightOcean's Mods Manager uses plugin-driven architecture:

```
┌─────────────────────────────────────────────────────────┐
│                 NightOcean's Mods Manager               │
│                    (Main Program Core)                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Game Plugin │  │ Game Plugin │  │   Game Plugin   │  │
│  │      A      │  │      B      │  │        C        │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Feature    │  │  Feature    │  │     Feature     │  │
│  │  Plugin X   │  │  Plugin Y   │  │     Plugin Z    │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Dual Plugin System

| Plugin Type | Description | Mutual Exclusivity |
|-------------|-------------|-------------------|
| **Game Plugin** | Provides Mod parsing and launch functionality for specific games | Only one can be enabled at a time |
| **Feature Plugin** | Extends program functionality | Multiple can be enabled simultaneously |

### Plugin Capabilities

#### Game Plugins Must Implement

- Parse game metadata and Mod metadata
- Provide game launch functionality (local launch, Steam launch)
- Define game-specific path validation rules

#### All Plugins Can Implement

| Capability | Description |
|------------|-------------|
| Add Menu Items | Add own operations to menu bar |
| Add Toolbar Buttons | Quick access to plugin features |
| Add Custom Panels | Display plugin-specific interfaces |
| Subscribe to Events | Respond to Mod list changes, game switching, etc. |
| Custom Highlight Rules | Highlight Mods by conditions |
| Custom Filter Rules | Implement complex filtering logic |
| Independent Config Storage | Save plugin's own settings |
| Extend Error Detection | Add game-specific Mod problem detection |
| Extend Context Menu | Add operations to Mod list right-click menu |

#### Game Plugins Can Also Implement

- Parse save files (import Mod configuration from saves)
- Parse external configuration files
- Custom topological sorting logic

### SDK-Based Development

Plugin development is fully SDK-based; developers don't need access to the main program source code. The SDK is released alongside the main program:

```bash
pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl
```

**Simple Feature Plugin Example:**

```python
from yh_mods_manager_sdk import FeaturePlugin, PluginMenuItem

class MyPlugin(FeaturePlugin):
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "My Plugin"
    PLUGIN_VERSION = "1.0.0"
    
    def get_menu_items(self):
        return [
            PluginMenuItem(id="action", label="My Action", action_id="do_it")
        ]
    
    def on_menu_action(self, action_id, manager_collection):
        if action_id == "do_it":
            print("Action triggered!")
```

> 📖 **Detailed Development Guide**: [Plugin Development Documentation](docs/PLUGIN_DEVELOPMENT.md)
> 📦 **Example Plugin Repository**: [YHModsManagerPlugins](https://github.com/IdealNightOcean/YHModsManagerPlugins) - Check it out for reference

---

## Quick Start

The program is packaged as a standalone executable for one-click operation, no Python environment configuration needed.

### Running the Program

1. Download the executable for your platform
2. Double-click to run

### First Time Use

1. **Install Game Plugin** - After the program starts, it will prompt you to install game plugins; select the plugin for the game you want to manage
2. **Set Paths** - Specify the game installation directory and Mod directory (the program will attempt auto-detection)
3. **Scan Mods** - The program automatically scans available Mods
4. **Start Managing** - Enable, sort, and manage your Mods

![Plugin Installation](docs/images/插件安装.gif)

---

## Developer Guide

### Project Structure

```
YHModsManager/
├── core/                    # Core business logic
├── ui/                      # User interface
├── plugin_system/           # Plugin system
├── utils/                   # Utility functions
├── config/                  # Configuration files
├── docs/                    # Documentation
└── yh_mods_manager_sdk/     # Plugin SDK
```

### Core Architecture

The project adopts a layered architecture:

| Layer | Responsibility |
|-------|----------------|
| UI Layer | Interface display and user interaction |
| Business Logic Layer | Mod operations, dependency resolution |
| Data Management Layer | Configuration, metadata management |
| Plugin System Layer | Plugin loading and scheduling |
| Infrastructure Layer | Logging, event bus, etc. |

### Related Documentation

- [Plugin Development Guide](docs/PLUGIN_DEVELOPMENT.md) - Plugin development tutorial

---

## Contributing

Welcome to participate in development, submit issues, or give suggestions! The author has limited experience in open source project management, please bear with any shortcomings.

- **Issues and Suggestions**: Submit through [Issues](https://github.com/IdealNightOcean/YHModsManager/issues)
- **Code Contribution**: Pull Requests are welcome

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**.

### License Key Points

| Permission | Description |
|------------|-------------|
| ✅ Free Use | Can freely use, modify, and distribute |
| ⚠️ Open Source Requirement | Modified versions must be open-sourced under the same license |
| ⚠️ Network Service | Network service usage also requires providing source code |
| ⚠️ Copyright Notice | Must retain copyright notice and license copy |

See the [LICENSE](LICENSE) file for the complete license text.

---

## Acknowledgments

**Thanks to all contributors and supporters!**
