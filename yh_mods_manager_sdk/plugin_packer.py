"""
插件打包工具
将插件源代码打包成 .vpkg 文件
支持双插件体系：游戏插件和功能插件分别输出到不同目录
"""

import fnmatch
import json
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .menu import PluginType

logger = logging.getLogger(__name__)

PLUGIN_EXTENSION = ".vpkg"
PLUGIN_MANIFEST = "manifest.json"


class PluginPacker:
    """插件打包器"""

    @staticmethod
    def pack(plugin_dir: str, output_dir: str = None,
             exclude_files: List[str] = None,
             plugin_type: PluginType = PluginType.GAME) -> Optional[str]:
        """打包插件
        
        Args:
            plugin_dir: 插件源代码目录
            output_dir: 输出目录，默认为 plugins 目录
            exclude_files: 排除的文件列表
            plugin_type: 插件类型
            
        Returns:
            打包后的文件路径，失败返回 None
        """
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin directory not found: {plugin_dir}")

        config_file = plugin_path / PLUGIN_MANIFEST
        if not config_file.exists():
            raise FileNotFoundError(f"Plugin config not found: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        plugin_id = config_data.get("plugin_id") or config_data.get("game_info", {}).get("game_id", "")
        if not plugin_id:
            raise ValueError("Plugin ID not found in config")

        plugin_version = config_data.get("plugin_version", "1.0.0")

        manifest_type = config_data.get("plugin_type")
        if manifest_type:
            plugin_type = PluginType(manifest_type)

        if output_dir is None:
            output_dir = plugin_path.parent.parent / "plugins" / plugin_type.value
        else:
            output_dir = Path(output_dir) / plugin_type.value

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_file = output_path / f"{plugin_id}{PLUGIN_EXTENSION}"

        exclude_files = exclude_files or ["__pycache__", "*.pyc", ".git", ".idea", "*.md"]

        manifest = PluginPacker._build_manifest(config_data, plugin_path, plugin_type)

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
            zf.writestr(PLUGIN_MANIFEST, manifest_json)

            for file_path in plugin_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(plugin_path)

                    if PluginPacker._should_exclude(str(rel_path), exclude_files):
                        continue

                    zf.write(file_path, str(rel_path))

        return str(output_file)

    @staticmethod
    def _build_manifest(config_data: dict, plugin_path: Path, plugin_type: PluginType = PluginType.GAME) -> dict:
        """构建清单文件"""
        manifest = {
            "plugin_id": config_data.get("plugin_id") or config_data.get("game_info", {}).get("game_id", ""),
            "plugin_type": config_data.get("plugin_type", plugin_type.value),
            "plugin_version": config_data.get("plugin_version", "1.0.0"),
            "packed_at": datetime.now().isoformat(),
            "entry_point": config_data.get("entry_point", "adapter"),
        }

        if plugin_type == PluginType.GAME:
            manifest.update({
                "game_info": config_data.get("game_info", {}),
                "path_validation": config_data.get("path_validation", {}),
                "default_settings": config_data.get("default_settings", {}),
                "custom_data": config_data.get("custom_data", {}),
                "detector_class": config_data.get("detector_class", "Detector"),
                "parser_class": config_data.get("parser_class", "Parser"),
            })
        else:
            manifest.update({
                "name": config_data.get("name", ""),
                "description": config_data.get("description", ""),
                "author": config_data.get("author", ""),
            })

        return manifest

    @staticmethod
    def _should_exclude(rel_path: str, exclude_patterns: List[str]) -> bool:
        """检查是否应该排除文件"""
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if any(part.startswith('__pycache__') for part in Path(rel_path).parts):
                return True

        return False

    @staticmethod
    def unpack(vpkg_path: str, output_dir: str) -> bool:
        """解包插件
        
        Args:
            vpkg_path: 插件包路径
            output_dir: 输出目录
            
        Returns:
            是否成功
        """
        if not os.path.exists(vpkg_path):
            raise FileNotFoundError(f"Plugin package not found: {vpkg_path}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(vpkg_path, 'r') as zf:
            zf.extractall(output_path)

        return True

    @staticmethod
    def verify(vpkg_path: str) -> dict:
        """验证插件包
        
        Returns:
            验证结果字典
        """
        result = {
            "valid": False,
            "plugin_id": "",
            "plugin_version": "",
            "errors": [],
            "files": []
        }

        if not os.path.exists(vpkg_path):
            result["errors"].append("File not found")
            return result

        if not vpkg_path.endswith(PLUGIN_EXTENSION):
            result["errors"].append(f"Invalid extension, expected {PLUGIN_EXTENSION}")
            return result

        try:
            with zipfile.ZipFile(vpkg_path, 'r') as zf:
                result["files"] = zf.namelist()

                if PLUGIN_MANIFEST not in result["files"]:
                    result["errors"].append(f"Missing {PLUGIN_MANIFEST}")
                    return result

                manifest_data = json.loads(zf.read(PLUGIN_MANIFEST).decode('utf-8'))
                result["plugin_id"] = manifest_data.get("plugin_id", "")
                result["plugin_version"] = manifest_data.get("plugin_version", "")

                if not result["plugin_id"]:
                    result["errors"].append("Missing plugin_id in manifest")
                    return result

                entry_point = manifest_data.get("entry_point", "adapter")
                adapter_file = f"{entry_point}.py"

                if adapter_file not in result["files"]:
                    result["errors"].append(f"Missing entry point: {adapter_file}")
                    return result

                result["valid"] = True

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file: {vpkg_path}: {e}")
            result["errors"].append("Invalid zip file")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid manifest JSON in {vpkg_path}: {e}")
            result["errors"].append("Invalid manifest JSON")
        except Exception as e:
            logger.error(f"Error verifying plugin {vpkg_path}: {e}", exc_info=True)
            result["errors"].append(str(e))

        return result


def pack_plugin(plugin_dir: str, output_dir: str = None, plugin_type: PluginType = PluginType.GAME) -> Optional[str]:
    """打包插件的便捷函数"""
    return PluginPacker.pack(plugin_dir, output_dir, plugin_type=plugin_type)


def verify_plugin(vpkg_path: str) -> dict:
    """验证插件的便捷函数"""
    return PluginPacker.verify(vpkg_path)
