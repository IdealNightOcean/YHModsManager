"""
JSON 序列化管理模块
统一管理所有数据类型的序列化/反序列化逻辑
遵循单一职责原则，业务类仅保留属性和业务逻辑
"""

import json
import logging
from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Callable

from .serializers import TypeSerializer, DataclassSerializer

T = TypeVar('T')

logger = logging.getLogger(__name__)


class JsonSerializeManager:
    """JSON 序列化管理器
    
    统一管理所有数据类型的序列化/反序列化逻辑
    提供文件持久化功能，支持异常捕获和日志输出
    """

    def __init__(self, config_dir: str = "config"):
        self._config_dir = Path(config_dir)
        self._serializers: Dict[Type, TypeSerializer] = {}
        self._serializer_factories: Dict[Type, Callable[[], TypeSerializer]] = {}
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def register_serializer(self, target_type: Type[T], serializer: TypeSerializer[T]):
        """注册类型序列化器
        
        Args:
            target_type: 目标类型
            serializer: 序列化器实例
        """
        self._serializers[target_type] = serializer
        logger.debug(f"Registered serializer for type: {target_type.__name__}")

    def register_serializer_factory(self, target_type: Type[T], factory: Callable[[], TypeSerializer[T]]):
        """注册序列化器工厂函数（延迟初始化）
        
        Args:
            target_type: 目标类型
            factory: 创建序列化器的工厂函数
        """
        self._serializer_factories[target_type] = factory
        logger.debug(f"Registered serializer factory for type: {target_type.__name__}")

    def register_dataclass(self, target_class: Type[T]) -> Type[T]:
        """装饰器：自动注册 dataclass 的序列化器
        
        用法:
            @json_manager.register_dataclass
            @dataclass
            class MyData:
                field1: str
                field2: int
        """
        self.register_serializer(target_class, DataclassSerializer(target_class))
        return target_class

    def get_serializer(self, target_type: Type[T]) -> Optional[TypeSerializer[T]]:
        """获取类型的序列化器"""
        if target_type in self._serializers:
            return self._serializers[target_type]

        if target_type in self._serializer_factories:
            serializer = self._serializer_factories[target_type]()
            self._serializers[target_type] = serializer
            return serializer

        if is_dataclass(target_type):
            serializer = DataclassSerializer(target_type)
            self._serializers[target_type] = serializer
            return serializer

        return None

    def serialize(self, obj: Any) -> Dict[str, Any]:
        """将对象序列化为字典
        
        Args:
            obj: 要序列化的对象
            
        Returns:
            序列化后的字典
            
        Raises:
            ValueError: 未找到对应的序列化器
        """
        obj_type = type(obj)
        serializer = self.get_serializer(obj_type)

        if serializer:
            return serializer.serialize(obj)

        if is_dataclass(obj):
            return asdict(obj)

        if isinstance(obj, dict):
            return obj

        raise ValueError(f"No serializer found for type: {obj_type.__name__}")

    def deserialize(self, data: Dict[str, Any], target_type: Type[T]) -> T:
        """从字典反序列化为对象
        
        Args:
            data: 源数据字典
            target_type: 目标类型
            
        Returns:
            反序列化后的对象
            
        Raises:
            ValueError: 未找到对应的序列化器
        """
        serializer = self.get_serializer(target_type)

        if serializer:
            return serializer.deserialize(data)

        if is_dataclass(target_type):
            return target_type()

        raise ValueError(f"No serializer found for type: {target_type.__name__}")

    def save_to_file(
            self,
            data: Any,
            filepath: str,
            indent: int = 2,
            ensure_ascii: bool = False,
            create_dirs: bool = True
    ) -> bool:
        """将数据保存到 JSON 文件
        
        Args:
            data: 要保存的数据（对象或字典）
            filepath: 目标文件路径
            indent: 缩进空格数
            ensure_ascii: 是否转义非 ASCII 字符
            create_dirs: 是否自动创建目录
            
        Returns:
            保存是否成功
        """
        try:
            path = Path(filepath)

            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)

            if not isinstance(data, dict):
                data = self.serialize(data)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

            logger.debug(f"Successfully saved data to: {filepath}")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Failed to save file {filepath}: {e}")
            return False
        except ValueError as e:
            logger.error(f"Serialization error for {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving {filepath}: {e}")
            return False

    def load_from_file(
            self,
            filepath: str,
            target_type: Optional[Type[T]] = None,
            default: Any = None
    ) -> Optional[Any]:
        """从 JSON 文件加载数据
        
        Args:
            filepath: 源文件路径
            target_type: 目标类型（可选，用于反序列化）
            default: 文件不存在或加载失败时的默认值
            
        Returns:
            加载的数据（字典或反序列化后的对象）
        """
        try:
            path = Path(filepath)

            if not path.exists():
                logger.debug(f"File not found: {filepath}, returning default")
                return default

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if target_type is not None:
                return self.deserialize(data, target_type)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return default
        except (IOError, OSError) as e:
            logger.error(f"Failed to load file {filepath}: {e}")
            return default
        except ValueError as e:
            logger.error(f"Deserialization error for {filepath}: {e}")
            return default
        except Exception as e:
            logger.error(f"Unexpected error loading {filepath}: {e}")
            return default

    def load_with_defaults(
            self,
            filepath: str,
            defaults: Dict[str, Any],
            target_type: Optional[Type[T]] = None
    ) -> Any:
        """从文件加载数据并与默认值合并
        
        Args:
            filepath: 源文件路径
            defaults: 默认值字典
            target_type: 目标类型（可选）
            
        Returns:
            合并后的数据
        """
        loaded = self.load_from_file(filepath, default={})
        merged = {**defaults, **loaded}

        if target_type is not None:
            return self.deserialize(merged, target_type)

        return merged

    def save_dict_to_file(
            self,
            data: Dict[str, Any],
            filepath: str,
            indent: int = 2,
            ensure_ascii: bool = False
    ) -> bool:
        """保存字典到 JSON 文件（便捷方法）
        
        Args:
            data: 数据字典
            filepath: 目标文件路径
            indent: 缩进空格数
            ensure_ascii: 是否转义非 ASCII 字符
            
        Returns:
            保存是否成功
        """
        return self.save_to_file(data, filepath, indent, ensure_ascii)

    def load_dict_from_file(
            self,
            filepath: str,
            default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """从 JSON 文件加载字典（便捷方法）
        
        Args:
            filepath: 源文件路径
            default: 默认值
            
        Returns:
            加载的字典
        """
        if default is None:
            default = {}
        return self.load_from_file(filepath, default=default)

    def get_config_dir_path(self, filename: str) -> str:
        """获取配置文件完整路径
        
        Args:
            filename: 文件名
            
        Returns:
            完整路径
        """
        return str(self._config_dir / filename)

    @property
    def config_dir(self) -> Path:
        """获取配置目录"""
        return self._config_dir


_json_manager: Optional[JsonSerializeManager] = None


def get_json_manager(config_dir: str = "config") -> JsonSerializeManager:
    """获取 JSON 序列化管理器实例"""
    global _json_manager
    if _json_manager is None:
        _json_manager = JsonSerializeManager(config_dir)
    return _json_manager


def init_json_manager(config_dir: str = "config") -> JsonSerializeManager:
    """初始化 JSON 序列化管理器"""
    global _json_manager
    _json_manager = JsonSerializeManager(config_dir)
    return _json_manager
