import os
import shlex

from datetime import datetime
from typing import Dict, Optional, Tuple, Type

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from plugins._base import BaseCradle
from core.models import CradleType

PROMPT_STYLE = Style.from_dict({"": "#00d7ff"})

BANNER = r"""
 ███████████                                               █████████  █████               ████  ████ 
░░███░░░░░███                                             ███░░░░░███░░███               ░░███ ░░███ 
 ░███    ░███  ██████  █████ ███ █████  ██████  ████████ ░███    ░░░  ░███████    ██████  ░███  ░███ 
 ░██████████  ███░░███░░███ ░███░░███  ███░░███░░███░░███░░█████████  ░███░░███  ███░░███ ░███  ░███ 
 ░███░░░░░░  ░███ ░███ ░███ ░███ ░███ ░███████  ░███ ░░░  ░░░░░░░░███ ░███ ░███ ░███████  ░███  ░███ 
 ░███        ░███ ░███ ░░███████████  ░███░░░   ░███      ███    ░███ ░███ ░███ ░███░░░   ░███  ░███ 
 █████       ░░██████   ░░████░████   ░░██████  █████    ░░█████████  ████ █████░░██████  █████ █████
░░░░░         ░░░░░░     ░░░░ ░░░░     ░░░░░░  ░░░░░      ░░░░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░ ░░░░░ 
                                                                                                     
                                                                                                     
                                                                                                     
   █████████                          █████ ████                                                     
  ███░░░░░███                        ░░███ ░░███                                                     
 ███     ░░░  ████████   ██████    ███████  ░███   ██████  ████████                                  
░███         ░░███░░███ ░░░░░███  ███░░███  ░███  ███░░███░░███░░███                                 
░███          ░███ ░░░   ███████ ░███ ░███  ░███ ░███████  ░███ ░░░                                  
░░███     ███ ░███      ███░░███ ░███ ░███  ░███ ░███░░░   ░███                                      
 ░░█████████  █████    ░░████████░░████████ █████░░██████  █████                                     
  ░░░░░░░░░  ░░░░░      ░░░░░░░░  ░░░░░░░░ ░░░░░  ░░░░░░  ░░░░░     
"""

class PowerShellCradleTerminal:
    def __init__(self,endpoint_registry,plugin_map: Dict[Tuple[str, str], Type[BaseCradle]], server_config: dict):
        self.endpoint_registry = endpoint_registry
        self.plugin_map        = plugin_map
        self.server_config     = server_config
        self.console           = Console()
        self.session           = PromptSession(
            history=InMemoryHistory(),
            style=PROMPT_STYLE
        )
        self.running           = True

    def run(self):
        self._print_banner()
        while self.running:
            try:
                with patch_stdout():
                    raw  = self.session.prompt(HTML("<ansibrightcyan><b>PowerShell Cradler</b></ansibrightcyan> <ansicyan>></ansicyan>"))
                line = raw.strip()
                if not line:
                    continue
                self._dispatch(line)
            except KeyboardInterrupt:
                self.console.print("\n  [yellow]Use [bold]exit[/bold] to quit.[/yellow]")
            except EOFError:
                break

    def _dispatch(self, line: str):
        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]
        handlers = {
            "help":      self._cmd_help,
            "?":         self._cmd_help,

            "exit":      self._cmd_exit,
            "quit":      self._cmd_exit,
            "q":         self._cmd_exit,

            "create":    self._cmd_create,
            "add":       self._cmd_create,
            "new":       self._cmd_create,

            "chain":     self._cmd_chain,

            "delete":    self._cmd_delete,
            "rm":        self._cmd_delete,

            "enable":    self._cmd_enable,
            "disable":   self._cmd_disable,
            "singleuse": self._cmd_singleuse,
            "multiuse":  self._cmd_multiuse,

            "cradles":   self._cmd_sessions,
            "plugins":   self._cmd_plugins,
            "files":     self._cmd_files,
            "chains":    self._cmd_chains,

            "ls":        self._cmd_list,
            "list":      self._cmd_list,

            "show":      self._cmd_info,
            "info":      self._cmd_info,

            "edit":      self._cmd_edit,
            "config":    self._cmd_config,

            "host":      self._cmd_host,
            "unhost":    self._cmd_unhost
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            self.console.print(
                f"  [red]Unknown command:[/red] [bold]{cmd}[/bold] - type [cyan]help[/cyan] for usage."
            )

    def _print_banner(self):
        self.console.print(f"[bold bright_cyan]{BANNER}[/bold bright_cyan]")
        self.console.print(
            "  [dim]PowerShell Payload Cradle Delivery Framework[/dim]  \n"
        )
        host = self.server_config['host']
        port = self.server_config['port']
        domain  = self.server_config['domain']
        self.console.print(
            f"  [green]•[/green] Server       : [bold]{host}[/bold]:[bold]{port}[/bold] [dim]restart with --host and --port args to change[/dim]\n"
            f"  [green]•[/green] Server URL   : [bold]{domain}[/bold] [dim]Use [cyan]config[/cyan] to change[/dim]\n"
            f"  [green]•[/green] Plugins      : [bold]{len(self.plugin_map)}[/bold] loaded\n"
            f"  [green]•[/green] Obfuscation  : [dim](none | base64 | char |[/dim] [bold]getrandom[/bold][dim])[/dim]\n"
        )
        self.console.print("  Type [cyan]help[/cyan] for available commands.\n")

    def _cmd_help(self, args):
        if not args:
            self._print_general_help()
        else:
            self._print_specific_help(args[0])

    def _print_general_help(self):
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0,1))
        table.add_column("Command", style="bold white", no_wrap=True)
        table.add_column("Description", style="dim white")
        cmds = [
            ("help [<plugin>]",        "General help, or scoped to a specific plugin when specified"),
            ("plugins",                "List available cradle plugins"),
            ("cradles",                "List all active cradle instances and their UIDs/URLs"),
            ("chains",                 "List chains of cradles"),
            ("files",                  "List all locally hosted files and their UIDs/URLs"),
            ("list",                   "List available plugins, active cradles, chains, and files hosted"),
            ("create <plugin>",        "Enter the creation shell for a new cradle"),
            ("chain <plugin1> [...]",  "Enter creation shells to create multiple cradles chained together"),
            ("delete <id|#>",          "Permanently delete a cradle instance"),
            ("edit <id|#>",            "Edit a cradle instance"),
            ("enable <id|#>",          "Re-enable a disabled cradle"),
            ("disable <id|#>",         "Disable a cradle (returns 404 when accessed)"),
            ("singleuse <id|#>",       "Set cradle to single-use (auto-disables after first hit)"),
            ("multiuse <id|#>",        "Set cradle back to multi-use"),
            ("info <id|#>",            "Show details and payload preview for a cradle"),
            ("host <filepath>",        "Add a local file to the hosted files registry"),
            ("unhost <id|#>",          "Remove a file from the hosting registry based on id/index"),
            ("unhost <filepath>",      "Remove a file from the hosting registry based on filepath"),
            ("config",                 "View or modify server configuration"),
            ("exit / quit / q",        "Exit PowerShellCradler")
        ]
        for cmd, desc in cmds:
            table.add_row(cmd, desc)
        self.console.print(Panel(table, title="[bold cyan]Commands[/bold cyan]", border_style="cyan", padding=(1,2)))

    def _print_specific_help(self, plugin_type: str):
        key = plugin_type.lower()
        cls = self.plugin_map.get(key)
        if not cls:
            self.console.print(f"  [red]Plugin not found:[/red] [bold]{plugin_type}[/bold]")
            return
        self._render_plugin_card(cls)

    def _render_plugin_card(self, cls: Type[BaseCradle]):
        lines = Text()
        lines.append("  Type       : ", style="dim"); lines.append("f{cls.TYPE}\n", style="bold white")
        lines.append("  Author     : ", style="dim"); lines.append("f{cls.AUTHOR}\n", style="bold white")
        lines.append(f"\n  {cls.DESCRIPTION}")
        self.console.print(Panel(
            lines,
            title=f"[bold cyan]{cls.TYPE}[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        ))
        if cls.OPTIONS:
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 2))
            table.add_column("Option", style="bold white", no_wrap=True)
            table.add_column("Default", style="yellow")
            table.add_column("Req", style="magenta", no_wrap=True)
            table.add_column("Description", style="dim white")
            for name, spec in cls.OPTIONS.items():
                label    = f"[green]{name}[/green]"
                default  = str(spec.get("default", ""))
                required = "[bold red]yes[/bold red]" if spec.get("required", True) else "no"
                table.add_row(label, default, required, spec.get("description", ""))
            self.console.print(table)

    def _cmd_list(self, args):
        columns = os.get_terminal_size().columns
        self._cmd_plugins(args)
        self.console.print("-" * columns)
        self._cmd_sessions(args)
        self.console.print("-" * columns)
        self._cmd_chains(args)
        self.console.print("-" * columns)
        self._cmd_files(args)


    def _cmd_create(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] create [bold]<plugin>[/bold]")
            if len(args) > 1:
                self.console.print("  [dim]You may have meant to use[/dim] [bold cyan]create <plugin1> [...][/bold cyan]")
            return
        pass

    def _cmd_chain(self, args):
        pass

    def _cmd_delete(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] delete [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.delete(args[0])
        if inst:
            self.console.print(f"  [green]✓[/green] Deleted cradle [bold]#{inst.index}[/bold] ({inst.uid})")
        else:
            self._not_found(args[0])

    def _cmd_enable(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] enable [bold]<id|#>[/bold]")
            return
        pass

    def _cmd_disable(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] disable [bold]<id|#>[/bold]")
            return
        pass

    def _cmd_singleuse(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] singleuse [bold]<id|#>[/bold]")
            return
        pass

    def _cmd_multiuse(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] multiuse [bold]<id|#>[/bold]")
            return
        pass

    def _cmd_sessions(self, args):
        pass

    def _cmd_plugins(self, args):
        pass

    def _cmd_files(self, args):
        files = self.endpoint_registry.list_instances(CradleType.File)
        if not files:
            self.console.print(
                "  [dim]No files hosted. Use [bold]host <filepath>[/bold] to host a file.[/dim]"
            )
            return
        domain = self.server_config['domain']
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 2))
        table.add_column("Index",     style="dim", no_wrap=True)
        table.add_column("UID",       style="dim", no_wrap=True)
        table.add_column("Filename",  style="bold white", no_wrap=True)
        table.add_column("Size",      style="yellow", justify="right", no_wrap=True)
        table.add_column("Status",    no_wrap=True)
        table.add_column("URL",       style="cyan")
        for hf in files:
            size_str   = _fmt_size(self.endpoint_registry.filesize(hf.uid))
            exists     = "[green]online[/green]" if os.path.exists(hf.cradle_context) else "[red]missing[/red]"
            url        = self.endpoint_registry.get_cradle_command(hf.uid)
            table.add_row(str(hf.index), hf.uid, hf.cradle_context, size_str, exists, url)
        self.console.print(Panel(
            table,
            title="[bold cyan]Hosted Files[/bold cyan]",
            border_style="cyan",
            subtitle="[dim]Use [bold]unhost <uid>[/bold] to remove[/dim]"
        ))

    def _cmd_chains(self,args):
        pass

    def  _cmd_info(self, args):
        pass

    def _cmd_edit(self, args):
        pass

    def _cmd_config(self, args):
        pass

    def _cmd_host(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] host [bold]\"<filepath>\"[/bold]")
            if len(args) > 1:
                self.console.print("  [dim]If filepath has spaces, surround with quotation marks[/dim]")
            return

        filepath = args[0]
        if not os.path.isfile(filepath):
            self.console.print(f"  [red]✗[/red] No file matching '[bold]{filepath}[/bold]'")
            return
        
        inst = [x for x in self.endpoint_registry.list_instances(CradleType.File) if x.cradle_context == filepath]
        if inst:
            inst = inst[0]
            self.console.print(f"  [red]✗[/red] File '[bold]{filepath}[/bold]' alread hosted in cradle [bold]{inst.index}[/bold] ([bold]{inst.uid}[bold])")
            return
        
        inst = self.endpoint_registry.create(CradleType.File,filepath,None)
        if inst:
            self.console.print(f"  [green]✓[/green] Cradle [bold]{inst.index}[/bold] ([bold]{inst.uid}[bold]) created for '[bold]{filepath}[/bold]'")
            return
        else:
            self.console.print(f"  [red]✗[/red] Unknown error when creating cradle for '[bold]{filepath}[/bold]'")
            return

    def _cmd_unhost(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]:Usage:[/red] unhost [bold]<id|#>[/bold]")
            return
        uid = args[0]
        inst = self.endpoint_registry.get_by_ref(uid)
        if inst:
            if inst.cradle_type == CradleType.File:
                self.endpoint_registry.delete(uid)
                self.console.print(f"  [green]✓[/green] No longer hosting [bold]{inst.cradle_context}[/bold] ({uid})")
                return
            else:
                self.console.print(f"  [red]✗[/red] Cradle [bold]{uid}[/bold] is not a file. Use [bold]delete {uid}[/bold] instead")
                return
        else:
            self._not_found(uid)
            return

    def _cmd_exit(self, args):
        self.console.print("  [dim]Goodbye.[/dim]\n")
        self.running = False

    # -----------------------------------
    # Helpers
    # -----------------------------------
    def _notification(self, notify_type: str, notify_text: str):
        # Necessary due to notifications showing with prompt + patch_stdout
        print_formatted_text(HTML(f"  - {notify_type}: <ansigray>{notify_text}</ansigray>"))

    def _not_found(self, ref: str):
        self.console.print(f"  [red]✗[/red] No cradle matching [bold]{ref}[/bold]")

def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"