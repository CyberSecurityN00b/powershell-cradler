from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from enum import IntEnum

class CradleType(IntEnum):
    Unknown = 0
    Plugin = 1
    File = 2
    Notification = 3

@dataclass
class CradleInstance:
    uid: str
    index: int
    cradle_type: CradleType
    cradle_context: str #plugin_type for plugin, filepath for file, plugin id for notification
    options: Dict[str, Any]
    enabled: bool = True
    single_use: bool = False
    used_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "index": self.index,
            "cradle_type": self.cradle_type,
            "cradle_context": self.cradle_context,
            "options": self.options,
            "enabled": self.enabled,
            "single_use": self.single_use,
            "used_count": self.used_count,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data:dict) -> "CradleInstance":
        return cls(**data)