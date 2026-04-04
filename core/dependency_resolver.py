from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple

from yh_mods_manager_sdk import Mod
from yh_mods_manager_sdk.enum_types import ModType, ModIssueStatus
from ui.i18n import tr
from .id_comparer import IdComparer


class DependencyResolver:
    def __init__(self, mods: List[Mod], id_comparer: IdComparer):
        self.mods = {mod.id: mod for mod in mods}
        self.id_comparer = id_comparer
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def _resolve_original_id_to_mod_id(self, original_id: str, enabled_set: Set[str]) -> str:
        """将原始ID解析为软件内部ID
        
        优先级：
        1. 已启用的mod中匹配原始ID
        2. 否则返回第一个匹配的mod
        3. 完全匹配则返回原始ID本身
        """
        result = self.id_comparer.resolve_original_id(original_id, enabled_set)
        return result if result else original_id

    def _get_enabled_mod_ids_by_original_id(self, original_id: str, enabled_set: Set[str]) -> List[str]:
        """根据原始ID获取所有已启用的mod ID"""
        return self.id_comparer.get_all_mod_ids_by_original_id(original_id, enabled_set)

    def _build_topological_graph(self, enabled_mods: List[str]) -> Tuple[bool, List[str]]:
        self.graph.clear()
        self.reverse_graph.clear()
        self.in_degree.clear()

        enabled_set = set(enabled_mods)

        for mod_id in enabled_mods:
            self.graph[mod_id] = set()
            self.in_degree[mod_id] = 0

        for mod_id in enabled_mods:
            mod = self.mods.get(mod_id)
            if not mod:
                continue

            for dep_original_id in mod.depended_modules:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(dep_original_id, enabled_set)
                if matched_mod_ids:
                    for dep_id in matched_mod_ids:
                        if mod_id not in self.graph[dep_id] and dep_id not in self.graph[mod_id]:
                            self.graph[dep_id].add(mod_id)
                            self.reverse_graph[mod_id].add(dep_id)
                            self.in_degree[mod_id] += 1
                elif not self.id_comparer.has_original_id(dep_original_id):
                    mod.add_issue(ModIssueStatus.MISSING_DEPENDENCIES)
                    mod.add_issue_detail(ModIssueStatus.MISSING_DEPENDENCIES, dep_original_id)

            for before_original_id in mod.load_before:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(before_original_id, enabled_set)
                for before_id in matched_mod_ids:
                    if before_id not in self.graph[mod_id] and mod_id not in self.graph[before_id]:
                        self.graph[mod_id].add(before_id)
                        self.reverse_graph[before_id].add(mod_id)
                        self.in_degree[before_id] += 1

            for after_original_id in mod.load_after:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(after_original_id, enabled_set)
                for after_id in matched_mod_ids:
                    if mod_id not in self.graph[after_id] and after_id not in self.graph[mod_id]:
                        self.graph[after_id].add(mod_id)
                        self.reverse_graph[mod_id].add(after_id)
                        self.in_degree[mod_id] += 1

        has_cycle, cycle = self._detect_cycle(enabled_mods)
        return has_cycle, cycle

    def _detect_cycle(self, nodes: List[str]) -> Tuple[bool, List[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in nodes}
        parent = {}
        cycle_path = []

        def dfs(node: str, path: List[str]) -> bool:
            color[node] = GRAY
            path.append(node)

            for neighbor in self.graph.get(node, set()):
                if color.get(neighbor, WHITE) == GRAY:
                    cycle_start = path.index(neighbor)
                    nonlocal cycle_path
                    cycle_path = path[cycle_start:] + [neighbor]
                    return True
                if color.get(neighbor, WHITE) == WHITE:
                    if dfs(neighbor, path):
                        return True

            path.pop()
            color[node] = BLACK
            return False

        for node in nodes:
            if color[node] == WHITE:
                if dfs(node, []):
                    return True, cycle_path

        return False, []

    def _get_mod_priority(self, mod_id: str) -> int:
        """获取mod的排序优先级（数值越小越优先）"""
        mod = self.mods.get(mod_id)
        if not mod:
            return 3
        if mod.mod_type == ModType.CORE:
            return 0
        if mod.mod_type == ModType.DLC:
            return 1
        return 2

    def topological_sort(self, enabled_mods: List[str]) -> List[str]:
        has_cycle, cycle = self._build_topological_graph(enabled_mods)

        if has_cycle:
            raise ValueError(tr("msg_circular_dependency") + f": {' -> '.join(cycle)}")

        in_degree = {node: cnt for node, cnt in self.in_degree.items()}

        queue = deque()
        zero_in_degree = [mod_id for mod_id in enabled_mods if in_degree.get(mod_id, 0) == 0]
        zero_in_degree.sort(key=lambda x: (self._get_mod_priority(x), x))
        queue.extend(zero_in_degree)

        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            neighbors = list(self.graph.get(current, set()))
            neighbors.sort(key=lambda x: (self._get_mod_priority(x), x))

            for neighbor in neighbors:
                if neighbor not in in_degree:
                    continue

                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(enabled_mods):
            raise RuntimeError("环")

        return result

    def get_missing_dependencies(self, mod_id: str, enabled_mods: List[str]) -> List[str]:
        """获取缺失的依赖列表
        
        强依赖必须被启用。如果依赖存在于所有Mod中但未被启用，也是缺失依赖。
        如果依赖完全不存在于扫描的Mod中，也是缺失依赖。
        """
        mod = self.mods.get(mod_id)
        if not mod:
            return []

        enabled_set = set(enabled_mods)
        missing_dependencies = []

        for dep_original_id in mod.depended_modules:
            matched_mod_ids = self._get_enabled_mod_ids_by_original_id(dep_original_id, enabled_set)
            if not matched_mod_ids:
                missing_dependencies.append(dep_original_id)

        return missing_dependencies

    def validate_load_order(self, ordered_mods: List[str]) -> Tuple[bool, List[str]]:
        errors = []
        mod_positions = {mod_id: i for i, mod_id in enumerate(ordered_mods)}
        enabled_set = set(ordered_mods)

        for i, mod_id in enumerate(ordered_mods):
            mod = self.mods.get(mod_id)
            if not mod:
                continue

            for dep_original_id in mod.depended_modules:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(dep_original_id, enabled_set)
                for dep_id in matched_mod_ids:
                    if dep_id in mod_positions:
                        if mod_positions[dep_id] > i:
                            errors.append(tr("error_should_load_after").format(mod.name, dep_original_id))

            for before_original_id in mod.load_before:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(before_original_id, enabled_set)
                for before_id in matched_mod_ids:
                    if before_id in mod_positions:
                        if mod_positions[before_id] < i:
                            errors.append(tr("error_should_load_before").format(mod.name, before_original_id))

            for after_original_id in mod.load_after:
                matched_mod_ids = self._get_enabled_mod_ids_by_original_id(after_original_id, enabled_set)
                for after_id in matched_mod_ids:
                    if after_id in mod_positions:
                        if mod_positions[after_id] > i:
                            errors.append(tr("error_should_load_after").format(mod.name, after_original_id))

        return len(errors) == 0, errors
