"""
Mod模块类型定义
统一管理Mod相关的数据类型，避免重复定义
遵循DRY原则
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ModOperationResult:
    """Mod操作结果
    
    用于表示Mod启用/禁用/删除等操作的结果
    """
    success: bool
    message: str = ""
    affected_mods: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """验证结果
    
    用于表示加载顺序验证等操作的结果
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warning_count: int = 0
