"""
Steam创意工坊服务模块
提供Steam Web API调用功能，用于获取创意工坊Mod的更新信息
"""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.json_serializer import get_json_manager

logger = logging.getLogger(__name__)


@dataclass
class SteamModInfo:
    """Steam创意工坊Mod信息
    
    序列化逻辑由 core.serializers.SteamModInfoSerializer 处理
    """
    workshop_id: str
    title: str = ""
    update_time: Optional[datetime] = None
    file_size: int = 0
    subscriptions: int = 0
    favorited: int = 0
    creator: str = ""
    tags: List[str] = field(default_factory=list)


class SteamAPIService:
    """Steam API服务
    
    使用Steam Web API获取创意工坊Mod信息
    API文档: https://partner.steamgames.com/doc/webapi/ISteamRemoteStorage
    """

    API_URL = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    BATCH_SIZE = 100
    TIMEOUT = 30

    def __init__(self, cache_dir: str = None):
        self._cache: Dict[str, SteamModInfo] = {}
        self._cache_file = None
        self._json_manager = None

        if cache_dir:
            self._json_manager = get_json_manager(cache_dir)
            self._cache_file = os.path.join(cache_dir, "steam_cache.json")
            self._load_cache()

    def _load_cache(self):
        if not self._cache_file or not os.path.exists(self._cache_file):
            return

        try:
            from core.serializers import SteamModInfoSerializer
            serializer = SteamModInfoSerializer()
            data = self._json_manager.load_from_file(self._cache_file)
            if data:
                for workshop_id, info_dict in data.items():
                    self._cache[workshop_id] = serializer.deserialize(info_dict)
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def _save_cache(self):
        if not self._cache_file or not self._json_manager:
            return

        try:
            from core.serializers import SteamModInfoSerializer
            serializer = SteamModInfoSerializer()
            cache_data = {
                wid: serializer.serialize(info)
                for wid, info in self._cache.items()
            }
            self._json_manager.save_to_file(cache_data, self._cache_file)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get_cached_info(self, workshop_id: str) -> Optional[SteamModInfo]:
        return self._cache.get(workshop_id)

    def get_all_cached_info(self) -> Dict[str, SteamModInfo]:
        return self._cache.copy()

    def fetch_mod_info(self, workshop_ids: List[str]) -> Dict[str, SteamModInfo]:
        """获取创意工坊Mod信息
        
        Args:
            workshop_ids: 创意工坊ID列表
            
        Returns:
            workshop_id -> SteamModInfo 的映射
        """
        if not workshop_ids:
            return {}

        results = {}
        uncached_ids = []

        for wid in workshop_ids:
            if wid in self._cache:
                results[wid] = self._cache[wid]
            else:
                uncached_ids.append(wid)

        if uncached_ids:
            fetched = self._fetch_from_api(uncached_ids)
            results.update(fetched)
            self._cache.update(fetched)
            self._save_cache()

        return results

    def _fetch_from_api(self, workshop_ids: List[str]) -> Dict[str, SteamModInfo]:
        """从Steam API获取Mod信息"""
        results = {}

        for i in range(0, len(workshop_ids), self.BATCH_SIZE):
            batch = workshop_ids[i:i + self.BATCH_SIZE]
            batch_results = self._fetch_batch(batch)
            results.update(batch_results)

        return results

    def _fetch_batch(self, workshop_ids: List[str]) -> Dict[str, SteamModInfo]:
        """批量获取Mod信息（最多100个）"""
        if not workshop_ids:
            return {}

        post_data = {"itemcount": len(workshop_ids)}
        for i, wid in enumerate(workshop_ids):
            post_data[f"publishedfileids[{i}]"] = wid

        encoded_data = urllib.parse.urlencode(post_data).encode("utf-8")

        request = urllib.request.Request(
            self.API_URL,
            data=encoded_data,
            method="POST"
        )
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                return self._parse_response(response_data)
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error: {e.code} {e.reason}")
            return {}
        except urllib.error.URLError as e:
            logger.error(f"Network error: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {}

    @staticmethod
    def _parse_response(response_data: dict) -> Dict[str, SteamModInfo]:
        """解析Steam API响应"""
        results = {}

        response = response_data.get("response", {})
        published_file_details = response.get("publishedfiledetails", [])

        for item in published_file_details:
            workshop_id = item.get("publishedfileid", "")
            if not workshop_id:
                continue

            result = item.get("result", 0)
            if result != 1:
                continue

            update_timestamp = item.get("time_updated", 0)
            update_time = datetime.fromtimestamp(update_timestamp) if update_timestamp else None

            tags = []
            for tag in item.get("tags", []):
                tag_name = tag.get("tag", "")
                if tag_name:
                    tags.append(tag_name)

            info = SteamModInfo(
                workshop_id=workshop_id,
                title=item.get("title", ""),
                update_time=update_time,
                file_size=item.get("file_size", 0),
                subscriptions=item.get("subscriptions", 0),
                favorited=item.get("favorited", 0),
                creator=item.get("creator", ""),
                tags=tags
            )
            results[workshop_id] = info

        return results

    def clear_cache(self):
        self._cache.clear()
        if self._cache_file and os.path.exists(self._cache_file):
            try:
                os.remove(self._cache_file)
            except Exception as e:
                logger.warning(f"Failed to remove cache file {self._cache_file}: {e}")


class SteamFetchWorker(QThread):
    """Steam数据获取工作线程"""

    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, steam_service: SteamAPIService, workshop_ids: List[str]):
        super().__init__()
        self._steam_service = steam_service
        self._workshop_ids = workshop_ids

    def run(self):
        if not self._workshop_ids:
            self.finished.emit({})
            return

        self.progress.emit(f"Fetching {len(self._workshop_ids)} workshop items...")

        try:
            results = self._steam_service.fetch_mod_info(self._workshop_ids)
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Error fetching mod info: {e}", exc_info=True)
            self.error.emit(str(e))


def create_steam_service(cache_dir: str = None) -> SteamAPIService:
    """创建Steam API服务实例
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        SteamAPIService实例
    """
    return SteamAPIService(cache_dir)
