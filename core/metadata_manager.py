"""
元数据管理器模块
遵循插件系统需求文档规范：
- 游戏元数据 ≠ Mod元数据，完全独立管理
- 主程序负责存储、管理、分发
- 插件仅负责读取和输出
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from yh_mods_manager_sdk import GameMetadata, ModMetadata


class GameMetadataManager:
    """游戏元数据管理器
    
    职责：
    1. 接收插件输出的游戏元数据
    2. 独立存储游戏元数据
    3. 独立分发游戏元数据给需要的组件
    
    不负责：
    - 读取原始游戏数据（由插件负责）
    - 解析游戏配置（由插件负责）
    - 生成游戏元数据（由插件负责）
    """

    def __init__(self):
        self._metadata: Dict[str, GameMetadata] = {}
        self._current_game_id: str = ""

    def receive_metadata(self, game_id: str, metadata: GameMetadata) -> None:
        """接收插件输出的游戏元数据"""
        metadata.game_id = game_id
        metadata.last_scan_time = datetime.now().isoformat()
        self._metadata[game_id] = metadata

    def get_metadata(self, game_id: str = None) -> Optional[GameMetadata]:
        """获取游戏元数据"""
        target_id = game_id or self._current_game_id
        return self._metadata.get(target_id)

    def get_all_metadata(self) -> Dict[str, GameMetadata]:
        """获取所有游戏元数据"""
        return self._metadata.copy()

    def set_current_game(self, game_id: str) -> None:
        """设置当前游戏"""
        self._current_game_id = game_id

    def get_current_game_id(self) -> str:
        """获取当前游戏ID"""
        return self._current_game_id

    def get_game_version(self, game_id: str = None) -> str:
        """获取游戏版本"""
        metadata = self.get_metadata(game_id)
        return metadata.game_version if metadata else ""

    def get_game_paths(self, game_id: str = None) -> Dict[str, str]:
        """获取游戏相关路径"""
        metadata = self.get_metadata(game_id)
        if not metadata:
            return {}
        return {
            "install_path": metadata.install_path,
            "workshop_path": metadata.workshop_path,
            "local_mod_path": metadata.local_mod_path,
            "config_path": metadata.config_path
        }

    def update_path(self, game_id: str, path_type: str, path_value: str) -> None:
        """更新特定路径"""
        if game_id in self._metadata:
            setattr(self._metadata[game_id], path_type, path_value)

    def clear_metadata(self, game_id: str = None) -> None:
        """清除元数据"""
        if game_id:
            self._metadata.pop(game_id, None)
        else:
            self._metadata.clear()


class ModMetadataManager:
    """Mod元数据管理器
    
    职责：
    1. 接收插件输出的Mod元数据
    2. 独立存储Mod元数据
    3. 独立分发Mod元数据给需要的组件
    
    不负责：
    - 读取原始Mod数据（由插件负责）
    - 解析Mod配置（由插件负责）
    - 生成Mod元数据（由插件负责）
    """

    def __init__(self):
        self._metadata: Dict[str, ModMetadata] = {}
        self._game_mods: Dict[str, List[str]] = {}
        self._current_game_id: str = ""

    def receive_metadata(self, game_id: str, metadata: ModMetadata) -> None:
        """接收插件输出的Mod元数据"""
        mod_id = metadata.mod_id
        if not mod_id:
            return

        metadata.scan_time = datetime.now().isoformat()
        self._metadata[mod_id] = metadata

        if game_id not in self._game_mods:
            self._game_mods[game_id] = []
        if mod_id not in self._game_mods[game_id]:
            self._game_mods[game_id].append(mod_id)

    def receive_batch_metadata(self, game_id: str, metadata_list: List[ModMetadata]) -> None:
        """批量接收Mod元数据"""
        for metadata in metadata_list:
            self.receive_metadata(game_id, metadata)

    def get_metadata(self, mod_id: str) -> Optional[ModMetadata]:
        """获取单个Mod元数据"""
        return self._metadata.get(mod_id)

    def get_all_metadata(self) -> Dict[str, ModMetadata]:
        """获取所有Mod元数据"""
        return self._metadata.copy()

    def get_game_mods(self, game_id: str = None) -> List[ModMetadata]:
        """获取指定游戏的所有Mod元数据"""
        target_id = game_id or self._current_game_id
        mod_ids = self._game_mods.get(target_id, [])
        return [self._metadata[mid] for mid in mod_ids if mid in self._metadata]

    def get_mod_ids(self, game_id: str = None) -> List[str]:
        """获取指定游戏的所有Mod ID"""
        target_id = game_id or self._current_game_id
        return self._game_mods.get(target_id, []).copy()

    def set_current_game(self, game_id: str) -> None:
        """设置当前游戏"""
        self._current_game_id = game_id

    def get_current_game_id(self) -> str:
        """获取当前游戏ID"""
        return self._current_game_id

    def update_metadata(self, mod_id: str, updates: Dict[str, Any]) -> None:
        """更新Mod元数据"""
        if mod_id in self._metadata:
            mod = self._metadata[mod_id]
            for key, value in updates.items():
                if hasattr(mod, key):
                    setattr(mod, key, value)

    def clear_game_mods(self, game_id: str = None) -> None:
        """清除指定游戏的Mod元数据"""
        target_id = game_id or self._current_game_id
        if target_id in self._game_mods:
            for mod_id in self._game_mods[target_id]:
                self._metadata.pop(mod_id, None)
            del self._game_mods[target_id]

    def clear_all(self) -> None:
        """清除所有Mod元数据"""
        self._metadata.clear()
        self._game_mods.clear()
