import json
import os
import secrets
import string
import re

from typing import Dict, List, Optional, Tuple, Type
from core.models import CradleInstance, CradleType
from plugins._base import BaseCradlePlugin
from datetime import datetime

_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "cradles.json"
)
_NOTIFICATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "notifications",
)

class EndpointRegistry:
    def __init__(
            self,
            plugin_map: Dict[Tuple[str, str], Type[BaseCradlePlugin]],
            server_config: dict,
    ):
        self.plugin_map    = plugin_map
        self.server_config = server_config
        self._instances: Dict[str, CradleInstance] = {}
        self._next_index = 1
        self._load()

    def _get_uid(self) -> str:
        while True:
            uid = ''.join(secrets.choice(string.ascii_lowercase+string.digits) for i in range(8))
            if not uid in self._instances.keys():
                return uid

    # -----------------------------------
    # Persistence
    # -----------------------------------

    def _load(self):
        if not os.path.exists(_STORAGE_PATH):
            return
        with open(_STORAGE_PATH) as f:
            data = json.load(f)
        for item in data.get("instances", []):
            inst = CradleInstance.from_dict(item)
            self._instances[inst.uid] = inst
            if inst.index >= self._next_index:
                self._next_index = inst.index + 1

    def _save(self):
        os.makedirs(os.path.dirname(_STORAGE_PATH), exist_ok=True)
        with open(_STORAGE_PATH, "w") as f:
            json.dump(
                {"instances": [i.to_dict() for i in self._instances.values()]},
                f,
                indent=2
            )

    # -----------------------------------
    # CRUD
    # -----------------------------------

    def create(
            self,
            cradle_type: CradleType,
            cradle_context: str,
            options: dict
    ) -> CradleInstance:
        if cradle_type == CradleType.Plugin:
            if cradle_context not in self.plugin_map:
                raise ValueError(f"Unknown plugin type: {cradle_context}")
            plugin_cls = self.plugin_map[cradle_context]
        elif cradle_type == CradleType.File:
            path = cradle_context.strip()
            if not os.path.isfile(path):
                raise ValueError(f"File not found: {path}")
        elif cradle_type == CradleType.Notification:
            pass
        else:
            raise ValueError(f"Unknown CradleType: {cradle_type}")
        
        uid  = self._get_uid()
        inst = CradleInstance(
            uid=uid,
            index=self._next_index,
            cradle_type=cradle_type,
            cradle_context=cradle_context,
            options=options,
        )
        self._next_index += 1
        self._instances[uid] = inst
        self._save()
        return inst
    
    def create_notification_channel_for(self, ref: str, single_use: bool = True) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            return self.create(CradleType.Notification,inst.uid, {"single_use":single_use})
        return inst
        
    def get_by_ref(self, ref: str) -> Optional[CradleInstance]:
        if ref in self._instances:
            return self._instances[ref]
        for inst in self._instances.values():
            if inst.index == int(ref):
                return inst
        return None
    
    def delete(self, ref: str) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            del self._instances[inst.uid]
            self._save()
        return inst
    
    def enable(self, ref: str) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            inst.enabled = True
            self._save()
        return inst
    
    def disable(self, ref: str) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            inst.enabled = False
            self._save()
        return inst
    
    def set_single_use(self, ref: str) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            inst.single_use = True
            self._save()
        return inst
    
    def set_multi_use(self, ref: str) -> Optional[CradleInstance]:
        inst = self.get_by_ref(ref)
        if inst:
            inst.single_use = False
            self._save()
        return inst
    
    def list_all_instances(self) -> List[CradleInstance]:
        return sorted(self._instances.values(), key=lambda x: x.index)
    
    def list_instances(self, cradle_type: CradleType) -> List[CradleInstance]:
        return sorted([x for x in self._instances.values() if x.cradle_type == cradle_type], key=lambda x: x.index)
    
    # -----------------------------------
    # Payload generation (called by Flask)
    # -----------------------------------

    def generate_payload(self, uid: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (cradle_type, payload_text, content_type)"""
        inst = self._instances.get(uid)
        if not inst or not inst.enabled:
            return None, None, None
        if inst.single_use and inst.used_count > 0:
            return None, None, None
        
        if inst.cradle_type == CradleType.Plugin:
            plugin = self.plugin_map.get(inst.cradle_context)
            if not plugin:
                return None, None, None
            
            plugin_cls  = plugin(self)
            payload     = plugin_cls.generate(inst)

            inst.used_count += 1
            self._save()

            return inst.cradle_type, payload, plugin.CONTENT_TYPE

        elif inst.cradle_type == CradleType.File:
            return inst.cradle_type, inst.cradle_context, None
        else:
            return None, None, None
        
    def get_cradle_command(self, ref: str) -> str:
        inst = self.get_by_ref(ref)
        if inst:
            url = f"http://{self.server_config['domain']}/{inst.uid}"
            if inst.cradle_type == CradleType.Plugin:
                plugin = self.plugin_map.get(inst.cradle_context)
                if not plugin:
                    return ""
                plugin_cls = plugin(self)
                return plugin_cls.cradle_command(inst,url)
            else:
                return url
        return inst
    
    # -----------------------------------
    # Notifications (called by Flask)
    # -----------------------------------

    def handle_notification(self, uid: str, remote_addr: str, body_json) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns cradle_type, cradle_context, notification"""
        inst = self._instances.get(uid)
        if not inst or not inst.enabled:
            return None, None, None
        if inst.single_use and inst.used_count > 0:
            return None, None, None

        remote_addr = re.sub(r':', '.', remote_addr)
        remote_addr = re.sub(r'[^\w\s.-]', '', remote_addr)
        
        context_inst = self._instances.get(inst.cradle_context)
        if not inst:
            context_text = inst.cradle_context
        else:
            context_text = f"{context_inst.cradle_context}_{inst.cradle_context}"
        outpath = os.path.join(_NOTIFICATION_PATH,remote_addr,f"{datetime.strftime(datetime.now(),"%Y-%m-%dT%H.%M.%S")}_{context_text}")
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(
                body_json,
                f,
                indent=2
            )

        if inst.options.get("single_use",True):
            self.delete(inst.uid)
        
        return inst.cradle_type, inst.cradle_context, f"Notification for {inst.cradle_context} ({inst.uid}) from {remote_addr} written to {outpath}"
    
    # -----------------------------------
    # File Hosting Stuff
    # -----------------------------------
    
    def filename(self, ref: str) -> str:
        inst = self.get_by_ref(ref)
        if inst:
            if inst.cradle_type == CradleType.File:
                return os.path.basename(inst.cradle_context)
            return ""
        return ""
    
    def filesize(self, ref: str) -> int:
        inst = self.get_by_ref(ref)
        if inst:
            if inst.cradle_type == CradleType.File:
                try:
                    return os.path.getsize(inst.cradle_context)
                except OSError:
                    return 0
            return 0
        return 0