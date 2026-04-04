from datetime import datetime
from typing import Optional, Callable

from yh_mods_manager_sdk import ModProfile


class ProfileSerializer:
    @staticmethod
    def serialize(profile: ModProfile, get_mod_by_id: Optional[Callable] = None) -> dict:
        mod_order = []
        if get_mod_by_id:
            for mod_id in profile.mod_order:
                mod = get_mod_by_id(mod_id)
                if mod:
                    mod_order.append({
                        "id": mod.id,
                        "name": mod.name,
                        "workshop_id": mod.workshop_id if mod.workshop_id else "-1"
                    })
                else:
                    mod_order.append({
                        "id": mod_id,
                        "name": mod_id,
                        "workshop_id": "-1"
                    })
        else:
            for mod_id in profile.mod_order:
                mod_order.append({
                    "id": mod_id,
                    "name": mod_id,
                    "workshop_id": "-1"
                })

        return {
            "description": profile.description,
            "game_id": profile.game_id,
            "game_version": profile.game_version,
            "created_at": profile.created_at,
            "modified_at": profile.modified_at,
            "mod_order": mod_order
        }

    @staticmethod
    def deserialize(data: dict) -> ModProfile:
        mod_list = data.get("mod_order", [])
        mod_order = [item["id"] for item in mod_list]

        return ModProfile(
            description=data.get("description", ""),
            game_id=data.get("game_id", ""),
            game_version=data.get("game_version", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            modified_at=data.get("modified_at", datetime.now().isoformat()),
            mod_order=mod_order
        )
