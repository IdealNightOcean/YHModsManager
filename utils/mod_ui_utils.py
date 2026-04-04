import os
from typing import Optional, Iterator, TypeVar, Callable, Any

from yh_mods_manager_sdk import Mod, ModType, PlatformUtils

T = TypeVar('T')


class ModUIUtils:
    @staticmethod
    def open_mod_folder(mod: Optional[Mod]) -> bool:
        if mod and mod.path:
            path = mod.path
            if os.path.exists(path):
                if os.path.isfile(path):
                    path = os.path.dirname(path)
                os.startfile(path)
                return True
        return False

    @staticmethod
    def open_workshop_page(mod: Optional[Mod]) -> bool:
        if mod and mod.mod_type == ModType.WORKSHOP and mod.workshop_id:
            result = PlatformUtils.open_workshop_page(mod.workshop_id)
            return result.success
        return False

    @staticmethod
    def iterate_list_items(list_widget, item_type: type = None) -> Iterator[Any]:
        """高效遍历列表控件中的所有项
        
        Args:
            list_widget: QListWidget控件
            item_type: 可选的类型过滤器，只返回该类型的项
            
        Yields:
            列表中的每一项
        """
        count = list_widget.count()
        for i in range(count):
            item = list_widget.item(i)
            if item_type is None or isinstance(item, item_type):
                yield item

    @staticmethod
    def find_item_by_mod_id(list_widget, mod_id: str, item_type: type = None) -> Optional[Any]:
        """根据mod_id查找列表项
        
        Args:
            list_widget: QListWidget控件
            mod_id: 要查找的mod ID
            item_type: 可选的类型过滤器
            
        Returns:
            找到的列表项，未找到返回None
        """
        for item in ModUIUtils.iterate_list_items(list_widget, item_type):
            if item and item.mod.id == mod_id:
                return item
        return None

    @staticmethod
    def count_items_with_condition(list_widget, condition: Callable[[Any], bool], item_type: type = None) -> int:
        """统计满足条件的列表项数量
        
        Args:
            list_widget: QListWidget控件
            condition: 条件函数
            item_type: 可选的类型过滤器
            
        Returns:
            满足条件的项数量
        """
        count = 0
        for item in ModUIUtils.iterate_list_items(list_widget, item_type):
            if condition(item):
                count += 1
        return count
