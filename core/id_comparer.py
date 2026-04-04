"""
ID比较工具模块
统一管理Mod ID的比较逻辑，支持大小写敏感/不敏感配置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class IdComparer:
    """ID比较工具类
    
    统一管理：
    - original_id_map: 原始ID到软件内部ID的映射
    - 大小写敏感/不敏感的比较逻辑
    
    使用方式：
    1. 创建实例时传入 mods 列表和 case_sensitive 配置
    2. 调用 compare() 方法比较两个ID
    3. 调用 resolve_original_id() 解析原始ID到软件内部ID
    """

    case_sensitive: bool = False
    _original_id_map: Dict[str, List[str]] = field(default_factory=dict)
    _mod_id_set: Set[str] = field(default_factory=set)
    _lowercase_map: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self._original_id_map = {}
        self._mod_id_set = set()
        self._lowercase_map = {}

    def build_from_mods(self, mods: List):
        """从Mod列表构建映射"""
        self._original_id_map.clear()
        self._mod_id_set.clear()
        self._lowercase_map.clear()

        for mod in mods:
            self.add_mod(mod.id, mod.original_id)

    def add_mod(self, mod_id: str, original_id: str):
        """添加单个Mod的ID映射"""
        self._mod_id_set.add(mod_id)

        key = self._get_key(original_id)
        if key not in self._original_id_map:
            self._original_id_map[key] = []
        if mod_id not in self._original_id_map[key]:
            self._original_id_map[key].append(mod_id)

        if not self.case_sensitive:
            self._lowercase_map[mod_id.lower()] = mod_id

    def remove_mod(self, mod_id: str, original_id: str):
        """移除单个Mod的ID映射"""
        self._mod_id_set.discard(mod_id)

        key = self._get_key(original_id)
        if key in self._original_id_map:
            if mod_id in self._original_id_map[key]:
                self._original_id_map[key].remove(mod_id)
            if not self._original_id_map[key]:
                del self._original_id_map[key]

        if not self.case_sensitive:
            self._lowercase_map.pop(mod_id.lower(), None)

    def _get_key(self, id_str: str) -> str:
        """获取用于映射查找的键"""
        return id_str if self.case_sensitive else id_str.lower()

    def compare(self, id1: str, id2: str) -> bool:
        """比较两个ID是否相等
        
        Args:
            id1: 第一个ID
            id2: 第二个ID
        
        Returns:
            是否相等
        """
        if self.case_sensitive:
            return id1 == id2
        return id1.lower() == id2.lower()

    def equals_any(self, target_id: str, id_list: List[str]) -> bool:
        """检查目标ID是否与列表中任一ID相等
        
        Args:
            target_id: 目标ID
            id_list: ID列表
        
        Returns:
            是否存在匹配
        """
        target_key = self._get_key(target_id)
        for id_str in id_list:
            if self._get_key(id_str) == target_key:
                return True
        return False

    def find_in_set(self, target_id: str, id_set: Set[str]) -> Optional[str]:
        """在集合中查找匹配的ID
        
        Args:
            target_id: 目标ID
            id_set: ID集合
        
        Returns:
            匹配的ID（原始大小写），未找到返回None
        """
        if self.case_sensitive:
            return target_id if target_id in id_set else None

        target_lower = target_id.lower()
        for id_str in id_set:
            if id_str.lower() == target_lower:
                return id_str
        return None

    def resolve_original_id(self, original_id: str, enabled_set: Optional[Set[str]] = None,
                            prefer_steam: bool = False) -> Optional[str]:
        """将原始ID解析为软件内部ID
        
        优先级：
        1. 如果提供了enabled_set，优先返回已启用的mod
        2. 默认本地优先（LOCAL > WORKSHOP）
        3. 如果prefer_steam=True，则Steam优先（WORKSHOP > LOCAL）
        4. 完全不匹配则返回None
        
        Args:
            original_id: Mod的原始ID
            enabled_set: 已启用的mod ID集合（可选）
            prefer_steam: 是否优先使用Steam版本（默认False，本地优先）
        
        Returns:
            匹配的软件内部ID，未找到返回None
        """
        key = self._get_key(original_id)
        if key not in self._original_id_map:
            return None

        candidates = self._original_id_map[key]
        if not candidates:
            return None

        if enabled_set:
            for mod_id in candidates:
                if self.find_in_set(mod_id, enabled_set):
                    return mod_id

        def get_priority(inner_mod_id: str) -> int:
            if inner_mod_id.endswith("@local"):
                return 0 if not prefer_steam else 2
            elif inner_mod_id.endswith("@workshop"):
                return 2 if not prefer_steam else 0
            elif inner_mod_id.endswith("@core") or inner_mod_id.endswith("@dlc"):
                return 1
            return 3

        sorted_candidates = sorted(candidates, key=get_priority)
        return sorted_candidates[0] if sorted_candidates else None

    def get_all_mod_ids_by_original_id(self, original_id: str, enabled_set: Optional[Set[str]] = None) -> List[str]:
        """根据原始ID获取所有匹配的mod ID
        
        Args:
            original_id: Mod的原始ID
            enabled_set: 已启用的mod ID集合（可选，用于过滤）
        
        Returns:
            匹配的mod ID列表
        """
        key = self._get_key(original_id)
        if key not in self._original_id_map:
            return []

        candidates = self._original_id_map[key]
        if not enabled_set:
            return candidates.copy()

        result = []
        for mod_id in candidates:
            if self.find_in_set(mod_id, enabled_set):
                result.append(mod_id)
        return result

    def has_original_id(self, original_id: str) -> bool:
        """检查原始ID是否存在
        
        Args:
            original_id: Mod的原始ID
        
        Returns:
            是否存在
        """
        return self._get_key(original_id) in self._original_id_map

    def get_original_id_map(self) -> Dict[str, List[str]]:
        """获取原始ID映射（只读）
        
        注意：返回的是内部映射的副本，修改不会影响内部状态
        """
        return {k: v.copy() for k, v in self._original_id_map.items()}

    def normalize_id(self, id_str: str) -> str:
        """规范化ID（用于显示或存储）
        
        Args:
            id_str: 原始ID字符串
        
        Returns:
            规范化后的ID
        """
        if self.case_sensitive:
            return id_str
        return id_str.lower()

    def hash_id(self, id_str: str) -> int:
        """获取ID的哈希值（用于字典键）
        
        Args:
            id_str: ID字符串
        
        Returns:
            哈希值
        """
        return hash(self._get_key(id_str))

    def create_case_insensitive_dict(self) -> Dict[str, str]:
        """创建大小写不敏感的字典键映射
        
        Returns:
            字典：{小写ID: 原始ID}
        """
        if self.case_sensitive:
            return {}
        return self._lowercase_map.copy()
