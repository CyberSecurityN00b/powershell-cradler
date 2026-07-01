<img src=".images/PowerShell Cradler titlescreen.png">

PowerShell Cradler is a cradling framework for PowerShell written in Python for ethical hackers and security researchers.

## Installation
1. `git clone https://github.com/CyberSecurityN00b/powershell-cradler.git`
2. `cd powershell-cradler`
3. `python3 -m venv .venv`
4. `source ./.venv/bin/activate`
5. `pip3 install -r requirements.txt`

## Usage
```
python3 main.py --host <LHOST> --port <LPORT>
```
1. Run the program
2. Create plugins or a chain of plugins
3. Use the provided cradle URL/command to run it!

### Recommended example command to run a stager
```
chain amsi_bypass_ps_sgr enum_processes_ps_sgr proc_shellcode_sgr
```

## Concepts and Terminology

| Term | Definition |
| --- | --- |
| **Chain** | A series of cradles that will call each other sequentially. |
| **Cradle** | A URL which hosts PowerShell content to be passed to IEX to execute. |

## Features

- Obfuscation (including **new** and **improved** Seeded Get-Random (SGR) obfuscation!)
- File hosting
- Plugins
- Notifications

## Official Plugins

| Plugin | Description |
| --- | --- |
| **amsi_bypass_ps_sgr** | Recommended as the first plugin to run in a chain. Disables/bypasses AMSI using the specified technique. Uses Seeded Get-Random (SGR) obfuscation. |
| **enum_processes_ps_sgr** | Basic process enumeration. Uses Seeded Get-Random (SGR) obfuscation. |
| **proc_shellcode_sgr** | Creates a thread in the current process to run shellcode. Uses Seeded Get-Random (SGR) obfuscation. |
