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
from prompt_toolkit.completion import Completer, Completion, NestedCompleter, PathCompleter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from plugins._base import BaseCradlePlugin
from core.models import CradleType
from core.endpoint_registry import CradleInstance

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
    def __init__(self,endpoint_registry,plugin_map: Dict[Tuple[str, str], Type[BaseCradlePlugin]], server_config: dict):
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
            completer_plugin = PluginNameCompleter(self.plugin_map)
            completer_uid = UIDCompleter(self.endpoint_registry)
            completer = NestedCompleter.from_nested_dict({
                'help': completer_plugin,
                'create': completer_plugin,
                'chain': completer_plugin,
                'delete': completer_uid,
                'edit': completer_uid,
                'enable': completer_uid,
                'disable': completer_uid,
                'singleuse': completer_uid,
                'multiuse': completer_uid,
                'info': completer_uid,
                'host': PathCompleter(),
                'unhost': completer_uid,
                'plugins': None,
                'cradles': None,
                'chains': None,
                'files': None,
                'list': None,
                'config': None,
                'exit': None,
                'quit': None
            })
            try:
                with patch_stdout():
                    raw  = self.session.prompt(
                        HTML("<ansibrightcyan><b>PowerShell Cradler</b></ansibrightcyan> <ansicyan>></ansicyan> "),
                        completer=completer,
                        complete_while_typing=True
                    )
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

            "cradles":   self._cmd_cradles,
            "plugins":   self._cmd_plugins,
            "files":     self._cmd_files,
            "chains":    self._cmd_chains,

            "ls":        self._cmd_list,
            "list":      self._cmd_list,

            "show":      self._cmd_info,
            "info":      self._cmd_info,

            "edit":      self._cmd_edit,
            "options":   self._cmd_edit,
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
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0,1), show_lines=True)
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

    def _render_plugin_card(self, cls: Type[BaseCradlePlugin]):
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
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
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
        self._cmd_cradles(args)
        self.console.print("-" * columns)
        self._cmd_chains(args)
        self.console.print("-" * columns)
        self._cmd_files(args)


    def _cmd_create(self, args, show_cradle_cmd=True) -> Optional[CradleInstance]:
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] create [bold]<plugin>[/bold]")
            if len(args) > 1:
                self.console.print("  [dim]You may have meant to use[/dim] [bold cyan]create <plugin1> [...][/bold cyan]")
            return
        plugin_type = args[0].lower()
        cls = self.plugin_map.get(plugin_type,None)
        if not cls:
            self.console.print(
                f"  [red]Plugin not found:[/red] [bold]{plugin_type}[/bold]\n"
                f"  Use [/cyan]ls[/cyan] to view available plugins.\n"
            )
            return
        self.console.print(
            f"\n  [bold cyan]Initializing[/bold cyan] [bold]{plugin_type}[/bold]\n"
            f"  [dim]{cls.DESCRIPTION}\n"
        )
        try:
            inst = self.endpoint_registry.create(CradleType.Plugin, plugin_type, {})
        except Exception as exc:
            self.console.print(f"  [red]Error creating plugin {plugin_type}:[/red] {exc}")
            return
        
        # Only enable after options have been edited
        inst.enabled = False
        self._edit_plugin_shell(inst)
        inst.enabled = True

        if show_cradle_cmd:
            # Show Created box
            url = f"http://{self.server_config['domain']}/{inst.uid}"

            lines = Text()
            lines.append("\n")
            lines.append("  Index     : ", style="dim"); lines.append(f"#{inst.index}\n", style="bold white")
            lines.append("  UID       : ", style="dim"); lines.append(f"{inst.uid}\n", style="bold white")
            lines.append("  Type      : ", style="dim"); lines.append(f"Plugin {plugin_type}\n", style="bold cyan")
            lines.append("  Cradle    : ", style="dim"); lines.append(f"{url}\n", style="cyan")
            lines.append("  Mode      : ", style="dim"); lines.append("single-use\n" if inst.single_use else "multi-use\n", style="white")
            self.console.print(Panel(
                lines,
                title="[bold green]✓ Cradle Created and Enabled[/bold green]",
                border_style="green",
                padding=(0, 2)
            ))
            cmd = self.endpoint_registry.get_cradle_command(inst.uid)
            if cmd:
                self.console.print(Panel(
                    f"[bold white]{cmd}[/bold white]",
                    title="[bold cyan]Cradle Command[/bold cyan]",
                    subtitle="[dim]Run this on the target[/dim]",
                    border_style="bright_cyan",
                    padding=(1, 2)
                ))
        return inst


    def _cmd_chain(self, args):
        if not args:
            self.console.print("  [red]Usage:[/red] chain [bold]<plugin1>[/bold] [bold]<plugin2>[/bold] <...>")
            return
        invalid_plugins = []
        valid_plugins = []
        for plugin in args:
            plugin = plugin.lower()
            if plugin not in self.plugin_map.keys():
                invalid_plugins.append(plugin)
            else:
                valid_plugins.append(plugin)
        if invalid_plugins:
            for plugin in invalid_plugins:
                self.console.print(f"  [red]✗[/red] Invalid plugin: {plugin}")
            return
        instances = []
        for plugin in valid_plugins:
            inst = self._cmd_create([plugin],False)
            instances.append(inst)
        for index, inst in enumerate(instances[:-1]):
            inst.options["NEXT_CRADLE"] = instances[index+1].index
        inst = instances[0]
        self.console.print("  [green]✓[/green] {len(instances)} cradles created and linked together")
        cmd = self.endpoint_registry.get_cradle_command(inst.uid)
        if cmd:
            self.console.print(Panel(
                f"[bold white]{cmd}[/bold white]",
                title="[bold cyan]Starting Cradle Command[/bold cyan]",
                subtitle="[dim]Run this on the target[/dim]",
                border_style="bright_cyan",
                padding=(1, 2)
            ))

    def _cmd_delete(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] delete [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.delete(args[0])
        if inst:
            self.console.print(f"  [green]✓[/green] Deleted cradle [bold]#{inst.index}[/bold] ({inst.uid})")
        else:
            self._not_found(args[0])

    def _cmd_enable(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] enable [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.enable(args[0])
        if inst:
            self.console.print(f"  [green]✓[/green] Cradle [bold]#{inst.index}[/bold] ({inst.uid}) enabled")
        else:
            self._not_found(args[0])

    def _cmd_disable(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] disable [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.disable(args[0])
        if inst:
            self.console.print(f"  [yellow]-[/yellow] Cradle [bold]#{inst.index}[/bold] ({inst.uid}) disabled")
        else:
            self._not_found(args[0])

    def _cmd_singleuse(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] singleuse [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.set_single_use(args[0])
        if inst:
            self.console.print(f"  [yellow]-[/yellow] Cradle [bold]#{inst.index}[/bold] ({inst.uid}) set to [bold]single-use[/bold]")
        else:
            self._not_found(args[0])

    def _cmd_multiuse(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] multiuse [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.set_multi_use(args[0])
        if inst:
            self.console.print(f"  [green]✓[/green] Cradle [bold]#{inst.index}[/bold] ({inst.uid}) set to [bold]multi-use[/bold]")
        else:
            self._not_found(args[0])

    def _cmd_cradles(self, args):
        instances = self.endpoint_registry.list_all_instances()
        if not instances:
            self.console.print("  [dim]No cradle instances yet. Use [bold]create[/bold] to make one.[/dim]")
            return
        domain = self.server_config['domain']
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
        table.add_column("#",         style="bold white", justify="right", no_wrap=True)
        table.add_column("UID",       style="dim", no_wrap=True)
        table.add_column("Type",      style="bold cyan", no_wrap=True)
        table.add_column("Context",   style="white", no_wrap=True)
        table.add_column("Status",    no_wrap=True)
        table.add_column("Use",       no_wrap=True)
        table.add_column("Uses",      justify="right", no_wrap=True)
        table.add_column("URL",       style="dim")
        for inst in instances:
            if not inst.enabled:
                status = "[red]disabled[/red]"
            elif inst.single_use and inst.used_count > 1:
                status = "[yellow]spent[/yellow]"
            else:
                status = "[green]active[/green]"
            use_mode = "[yellow]single[/yellow]" if inst.single_use else "[green]multi[/green]"
            url = f"http://{domain}/{inst.uid}"
            table.add_row(
                str(inst.index), inst.uid, CradleType(inst.cradle_type).name,
                inst.cradle_context, status, use_mode, str(inst.used_count),
                url
            )
        self.console.print(Panel(
            table,
            title="[bold cyan]Cradle Instances[/bold cyan]",
            border_style="cyan"
        ))

    def _cmd_plugins(self, args):
        if not self.plugin_map:
            self.console.print("  [yellow]No plugins loaded.[/yellow]")
            return
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
        table.add_column("Name", style="bold cyan", no_wrap=True)
        table.add_column("Author", style="dim", no_wrap=True)
        table.add_column("Description", style="dim white")
        for name, cls in sorted(self.plugin_map.items()):
            table.add_row(name, cls.AUTHOR, cls.DESCRIPTION)
        self.console.print(Panel(
            table,
            title="[bold cyan]Available Plugins[/bold cyan]",
            border_style="cyan"
        ))

    def _cmd_files(self, args):
        files = self.endpoint_registry.list_instances(CradleType.File)
        if not files:
            self.console.print(
                "  [dim]No files hosted. Use [bold]host <filepath>[/bold] to host a file.[/dim]"
            )
            return
        domain = self.server_config['domain']
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
        table.add_column("#",         style="bold white", justify="right", no_wrap=True)
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
        instances_with_next = []
        instances = self.endpoint_registry.list_instances(CradleType.Plugin)
        if not instances:
            self.console.print("  [dim]No plugin cradle instances yet. Use [bold]create[/bold] to make one.[/dim]")
            return
        for inst in instances:
            next_inst = self.endpoint_registry.get_by_ref(inst.options.get("NEXT_CRADLE",0))
            if next_inst:
                instances_with_next.append(next_inst)
        if not instances_with_next:
            self.console.print("  [dim]No chains exist yet. Use [bold]chain[/bold] to make one or manually set the NEXT option of an existing cradle.[/dim]")
            return
        chain_starts = []
        for inst in instances:
            next_inst = self.endpoint_registry.get_by_ref(inst.options.get("NEXT_CRADLE",0))
            if next_inst and inst not in instances_with_next:
                chain_starts.append(inst)
        if not chain_starts:
            self.console.print("  [dim red]Chains exist, but they are all circular references with no start points.[/dim red]")
            return
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
        table.add_column("#",          style="bold white", justify="right", no_wrap=True)
        table.add_column("First URL",  style="dim", no_wrap=True)
        table.add_column("Chain",      style="white")
        chain_ctr = 0
        chain_links = []
        for inst in chain_starts:
            chain_ctr += 1
            url = f"http://{self.server_config['domain']}/{inst.uid}"
            chain_links.append(inst)
            next_inst = inst
            while len(chain_links) < 11:
                next_inst = self.endpoint_registry.get_by_ref(next_inst.options.get("NEXT_CRADLE",0))
                if not next_inst:
                    break
                chain_links.append(next_inst)
            chain_text = " → ".join([f"{x.index}({x.cradle_context})" for x in chain_links[:10]])
            if len(chain_links) >= 10:
                chain_text += " → [...]"
            table.add_row(
                str(chain_ctr),
                url,
                chain_text
            )
        self.console.print(Panel(
            table,
            title="[bold cyan]Cradle Chains[/bold cyan]",
            border_style="cyan"
        ))
            

    def  _cmd_info(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] info [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.get_by_ref(args[0])
        if not inst:
            self._not_found(args[0])
        url = f"http://{self.server_config['domain']}/{inst.uid}"
        if not inst.enabled:
            status_str = "[red]disabled[/red]"
        elif inst.single_use and inst.used_count > 0:
            status_str = "[yellow]spent[/yellow]"
        else:
            status_str = "[green]enabled[/green]"
        use_str = "[yellow]single-use[/yellow]" if inst.single_use else "[green]multi-use[/green]"
        created = datetime.fromisoformat(inst.created_at).strftime("%Y-%m-%d %H:%M:%S")

        meta = Text()
        meta.append("  Index     : ", style="dim"); meta.append(f"#{inst.index}\n", style="bold white")
        meta.append("  UID       : ", style="dim"); meta.append(f"{inst.uid}\n", style="bold white")
        meta.append("  Type      : ", style="dim"); meta.append(f"{inst.cradle_type.name}\n", style="bold cyan")
        meta.append("  Context   : ", style="dim"); meta.append(f"{inst.cradle_context}\n", style="cyan")
        meta.append("  Status    : ", style="dim"); meta.append(f"{status_str}\n")
        meta.append("  Use mode  : ", style="dim"); meta.append(f"{use_str}\n")
        meta.append("  Use count : ", style="dim"); meta.append(f"{int(inst.used_count)}\n")
        meta.append("  Created   : ", style="dim"); meta.append(f"{created}\n", style="dim white")

        if inst.options:
            meta.append("\n  Options:\n", style="bold dim")
            cls = self.plugin_map[inst.cradle_context]
            plugin_inst = cls(self.endpoint_registry)
            for k, v in plugin_inst.get_options_with_defaults(inst).items():
                meta.append(f"      {k} : ", style="dim"); meta.append(f"{v}\n", style="white")

        self.console.print(Panel(
            meta,
            title=f"[bold cyan]Cradle #{inst.index} ({inst.uid})[/bold cyan]",
            border_style="cyan",
            padding=(0, 2)
        ))

        cmd = self.endpoint_registry.get_cradle_command(inst)
        if cmd:
            self.console.print(Panel(
                f"[bold white]{cmd}[/bold white]",
                title="[bold cyan] Cradle Command[/bold cyan]",
                subtitle="[dim]Run this on the target[/dim]",
                border_style="bright_cyan",
                padding=(1, 2)
            ))
        
        if inst.enabled and not (inst.single_use and inst.used_count > 0):
            _, payload, _ = self.endpoint_registry.generate_payload(inst.uid)
            if payload:
                self.console.print(Panel(
                    f"[dim]{payload}[/dim]",
                    title=f"[bold cyan]Host Payload Preview[/bold cyan]",
                    subtitle=f"[dim]GET {url}[/dim]",
                    border_style="dim cyan",
                    padding=(1, 2)
                ))

    def _cmd_edit(self, args):
        if not args or len(args) > 1:
            self.console.print("  [red]Usage:[/red] edit [bold]<id|#>[/bold]")
            return
        inst = self.endpoint_registry.get_by_ref(args[0])
        if inst:
            self._edit_plugin_shell(inst)
        else:
            self._not_found(args[0])


    def _cmd_config(self, args):
        if not args:
            self.console.print(
                f"\n  [dim]host[/dim]    [bold]{self.server_config['host']}[/bold]\n"
                f"  [dim]port[/dim]    [bold]{self.server_config['port']}[/bold]\n"
                f"  [dim]domain[/dim]  [bold]{self.server_config['domain']}[/bold]\n\n"
                f"  [dim]Use [bold]config domain <value>[/bold] to change the domain.\n"
                f"  [dim]To change host/port, restart with [bold]--host <host>[/bold] and [bold]--port <port>[/bold] parameters."
            )
            return
        if len(args) < 2:
            self.console.print("  [red]Usage:[/red] config [bold]domain[/bold] [bold]<value>[/bold]")
            return
        key, val = args[0].lower(), args[1]
        if key == "host":
            self.console.print("  [red]✗[/red] To change the host, restart with [bold]--host <host>[/bold] parameter.")
            return
        elif key == "port":
            self.console.print("  [red]✗[/red] To change the port, restart with [bold]--port <port>[/bold] parameter.")
            return
        elif key == "domain":
            self.server_config['domain'] = val
            self.console.print(f"  [green]✓[/green] domain => [bold]{val}[/bold]")
        else:
            self.console.print(f"  [red]Unknown config key:[/red] [bold]{key}[/bold]")

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
            self.console.print("  [red]Usage:[/red] unhost [bold]<id|#>[/bold]")
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

    def _edit_plugin_shell(self, inst):
        if inst:
            if not inst.cradle_type == CradleType.Plugin:
                self.console.print(" [red]Only plugin endpoint cradles can be edited.[/red]")
                return
            cls = self.plugin_map[inst.cradle_context]
            plugin_inst = cls(self.endpoint_registry)
            self._render_plugin_card(cls)
            current_opts = plugin_inst.get_options_with_defaults(inst)
            self._print_current_options(cls,current_opts)
            self.console.print(
                "\n  [dim]Commands: [bold]set <OPTION> <value>[/bold]  |  "
                "[bold]unset <OPTION>[/bold]  |  [bold]options[/bold]  |  "
                "[bold]save[/bold]  |  [bold]cancel[/bold][/dim]\n"
            )
            sub_session = PromptSession(
                history=InMemoryHistory(),
                style=PROMPT_STYLE
            )
            completer_options = OptionsCompleter(plugin_inst,current_opts)
            completer = NestedCompleter.from_nested_dict({
                'set': completer_options,
                'unset': completer_options,
                'options': None,
                'save': None,
                'cancel': None
            })
            while True:
                try:
                    with patch_stdout():
                        raw = sub_session.prompt(
                            HTML(
                                f"<ansibrightcyan><b>PowerShell Cradler</b></ansibrightcyan>"
                                f" / <ansiyellow>{inst.cradle_context}</ansiyellow>"
                                f" <ansicyan>></ansicyan> "
                            ),
                            completer=completer,
                            complete_while_typing=True
                        )
                        line = raw.strip()
                except (KeyboardInterrupt, EOFError):
                    self.console.print("\n  [yellow]Aborted.[/yellow]")
                    return
                
                if not line:
                    continue
                try:
                    parts = shlex.split(line)
                except ValueError:
                    parts = line.split()
                sub_cmd = parts[0].lower() if parts else ""

                if sub_cmd in ("back", "exit", "q", "cancel"):
                    self.console.print("  [dim]Cancelled.[/dim]")
                    return
                
                elif sub_cmd == "set":
                    if len(parts) < 3:
                        self.console.print("  [red]Usage:[/red] set [bold]<OPTION>[/bold] [bold]<value>[/bold]")
                        continue
                    opt_name = parts[1].upper()
                    opt_val  = " ".join(parts[2:])
                    if opt_name not in cls.OPTIONS:
                        self.console.print(f"  [red]Unknown option:[/red] [bold]{opt_name}[/bold]")
                        continue
                    errors = plugin_inst.validate(inst, current_opts)
                    if errors:
                        for e in errors:
                            self.console.print(f"  [red]✗[/red] {e}")
                        continue
                    else:
                        self.console.print(f"  [green]✓[/green] [bold]{opt_name}[/bold] => [cyan]{opt_val}[/cyan]")
                        current_opts[opt_name] = opt_val

                elif sub_cmd == "unset":
                    if len(parts) < 2:
                        self.console.print("  [red]Usage:[/red] unset [bold]<OPTION>[/bold]")
                        continue
                    opt_name = parts[1].upper()
                    current_opts.pop(opt_name,None)
                    self.console.print(f"  [yellow]-[/yellow] [bold]{opt_name}[/bold] restored to defauilt value")

                elif sub_cmd == "save":
                    errors = plugin_inst.validate(inst, current_opts)
                    if errors:
                        for e in errors:
                            self.console.print(f"  [red]✗[/red] {e}")
                        continue
                    else:
                        inst.options = current_opts
                        self.endpoint_registry._save()
                        self.console.print(f"  [green]✓[/green] Changes saved to cradle {inst.index}({inst.uid})")
                        return

                elif sub_cmd == "options":
                    self._print_current_options(cls, current_opts)

                else:
                    self.console.print(f"  [red]Unknown command:[/red] [bold]{sub_cmd}[/bold]")


    def _render_plugin_card(self, cls: Type[BaseCradlePlugin]):
        lines = Text()
        lines.append("  Name     : ", style="dim"); lines.append(f"{cls.NAME}\n", style="bold white")
        lines.append("  Author   : ", style="dim"); lines.append(f"{cls.AUTHOR}\n", style="white")
        lines.append(F"\n  {cls.DESCRIPTION}")
        self.console.print(Panel(
            lines,
            title=f"[bold cyan]{cls.NAME}[/bold cyan]",
            border_style="cyan",
            padding=(0, 2)
        ))

    def _print_current_options(self, cls: Type[BaseCradlePlugin], opts: dict[str,any]):
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 2), show_lines=True)
        table.add_column("Option",        style="bold white", no_wrap=True)
        table.add_column("Value",         style="cyan")
        table.add_column("Req",           style="magenta", no_wrap=True)
        table.add_column("Restricted To", style="dim white")
        table.add_column("Description",   style="dim white")
        for name, spec in opts.items():
            label        = f"[green]{name}[/green]"
            val          = str(spec)
            required     = "[bold red]yes[/bold red]" if cls.OPTIONS.get(name,{}).get("required", False) else "no"
            restrictions = "[dim]no value restrictions[/dim]" if not cls.OPTIONS.get(name,{}).get("restricted_to", None) else "\n".join(cls.OPTIONS.get(name,{}).get("restricted_to",[]))
            table.add_row(label, val, required, restrictions, cls.OPTIONS.get(name,{}).get("description", ""))
        self.console.print(table)

def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

class UIDCompleter(Completer):
    def __init__(self, endpoint_registry):
        super().__init__()
        self.endpoint_registry=endpoint_registry

    def get_completions(self, document, complete_event):
        word = str(document.get_word_before_cursor())
        for inst in self.endpoint_registry.list_all_instances():
            if inst.uid.lower().startswith(word.lower()):
                yield Completion(
                    inst.uid,
                    start_position=-len(word),
                    style="fg:grey",
                    selected_style="fg:white bg:grey"
                )

class PluginNameCompleter(Completer):
    def __init__(self, plugin_map):
        super().__init__()
        self.plugin_map=plugin_map

    def get_completions(self, document, complete_event):
        word = str(document.get_word_before_cursor())
        for plugin in self.plugin_map.keys():
            if plugin.lower().startswith(word.lower()):
                yield Completion(
                    plugin,
                    start_position=-len(word),
                    style="fg:grey",
                    selected_style="fg:white bg:grey"
                )

class OptionsCompleter(Completer):
    def __init__(self, plugin_cls, options):
        super().__init__()
        self.plugin_cls=plugin_cls
        self.options=options

    def get_completions(self, document, complete_event):
        pos = len(document.text_before_cursor.split())
        word = str(document.get_word_before_cursor())

        if pos == 1:
            for option in self.options.keys():
                if option.lower().startswith(word.lower()):
                    yield Completion(
                        option,
                        start_position=-len(word),
                        style="fg:grey",
                        selected_style="fg:white bg:grey"
                    )
        elif pos == 2:
            option = document.text_before_cursor.split()[0]
            restrictions = self.plugin_cls.OPTIONS.get(option,{}).get("restricted_to",[])
            if restrictions:
                for restriction in restrictions:
                    if restriction.lower().startswith(word.lower()):
                        yield Completion(
                            restriction,
                            start_position=-len(word),
                            style="fg:grey",
                            selected_style="fg:white bg:grey"
                        )