#!/usr/bin/env python3
"""
MCP Configuration Manager - Arrow Key Navigation Terminal UI

A clean interface that combines menu-driven simplicity with arrow key navigation
for managing Model Context Protocol (MCP) server configurations across multiple applications.
"""

import json
import os
import sys
import termios
import tty
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.align import Align

from mcp_core import MCPConfigSynchronizer


@dataclass
class MCPServer:
    """Data class representing an MCP server configuration."""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        result = {"command": self.command}
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'MCPServer':
        """Create MCPServer from dictionary data."""
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {})
        )


class MCPConfigurationManager:
    """MCP Configuration Manager with arrow key navigation for managing MCP server configurations."""
    
    def __init__(self):
        self.console = Console()
        self.synchronizer = MCPConfigSynchronizer()
        self.current_app = "Claude"
        self.current_servers: Dict[str, MCPServer] = {}
        self.running = True
        
        # Menu options
        self.main_menu_options = [
            "MCP Server Overview",
            "Switch Application",
            "Add or Edit MCP Server", 
            "Delete Server",
            "Sync MCP Configs",
            "Show App Status",
            "Refresh Data",
            "Quit"
        ]
        self.current_selection = 0
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_key(self):
        """Get a single keypress from the user."""
        if os.name == 'nt':  # Windows
            import msvcrt
            key = msvcrt.getch()
            if key == b'\xe0':  # Arrow key prefix on Windows
                key = msvcrt.getch()
                if key == b'H': return 'up'
                elif key == b'P': return 'down'
                elif key == b'K': return 'left'
                elif key == b'M': return 'right'
            elif key == b'\r': return 'enter'
            elif key == b'\x1b': return 'escape'
            elif key == b'q' or key == b'Q': return 'quit'
            return key.decode('utf-8', errors='ignore')
        else:  # Unix/Linux/Mac
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                key = sys.stdin.read(1)
                if key == '\x1b':  # ESC sequence
                    key += sys.stdin.read(2)
                    if key == '\x1b[A': return 'up'
                    elif key == '\x1b[B': return 'down'
                    elif key == '\x1b[C': return 'right'
                    elif key == '\x1b[D': return 'left'
                    else: return 'escape'
                elif key == '\r' or key == '\n': return 'enter'
                elif key == '\x03': return 'ctrl_c'
                elif key == 'q' or key == 'Q': return 'quit'
                return key
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def show_header(self):
        """Display the application header."""
        header_text = Text("🔧 MCP Configuration Manager", style="bold blue")
        header_panel = Panel(
            Align.center(header_text),
            title="MCP Configuration Manager",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(header_panel)
        self.console.print()
    
    def show_current_app_info(self):
        """Display current application and server count."""
        server_count = len(self.current_servers)
        info_text = f"📱 Current App: [bold cyan]{self.current_app}[/bold cyan]  |  🔧 Servers: [bold yellow]{server_count}[/bold yellow]"
        
        info_panel = Panel(
            info_text,
            border_style="green",
            padding=(0, 2)
        )
        self.console.print(info_panel)
        self.console.print()
    
    def show_servers_table(self):
        """Display current servers in a table."""
        if not self.current_servers:
            self.console.print("[dim]No servers configured for this application.[/dim]")
            self.console.print()
            return
        
        table = Table(
            title=f"MCP Servers for {self.current_app}",
            box=box.ROUNDED,
            title_style="bold magenta"
        )
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Command", style="white")
        table.add_column("Arguments", style="yellow")
        table.add_column("Environment", style="green")
        
        for server in self.current_servers.values():
            args_display = " ".join(server.args) if server.args else "—"
            env_display = f"{len(server.env)} vars" if server.env else "—"
            
            table.add_row(
                server.name,
                server.command,
                args_display[:30] + ("..." if len(args_display) > 30 else ""),
                env_display
            )
        
        self.console.print(table)
        self.console.print()
    
    def show_main_menu(self):
        """Display the main menu with arrow key navigation."""
        self.console.print("[bold white]Main Menu (↑↓ to navigate, Enter to select, Q to quit):[/bold white]")
        self.console.print()
        
        for i, option in enumerate(self.main_menu_options):
            if i == self.current_selection:
                # Highlighted option
                if option == "Quit":
                    style = "bold red on white"
                    pointer = "👉"
                else:
                    style = "bold blue on white"
                    pointer = "👉"
                self.console.print(f"{pointer} [color(240)]{i+1}.[/color(240)] [{style}]{option}[/{style}]")
            else:
                # Regular option
                if option == "Quit":
                    style = "red"
                else:
                    style = "white"
                self.console.print(f"   [color(240)]{i+1}.[/color(240)] [{style}]{option}[/{style}]")
        
        self.console.print()
        self.console.print("[dim]Use ↑↓ arrows to navigate, Enter to select, Q to quit[/dim]")
    
    def navigate_menu(self):
        """Handle arrow key navigation for the main menu."""
        while True:
            self.clear_screen()
            self.show_header()
            self.show_current_app_info()
            self.show_servers_table()
            self.show_main_menu()
            
            try:
                key = self.get_key()
                
                if key == 'up':
                    self.current_selection = (self.current_selection - 1) % len(self.main_menu_options)
                elif key == 'down':
                    self.current_selection = (self.current_selection + 1) % len(self.main_menu_options)
                elif key == 'enter':
                    return self.current_selection
                elif key == 'quit' or key == 'escape':
                    return len(self.main_menu_options) - 1  # Quit option
                elif key == 'ctrl_c':
                    raise KeyboardInterrupt
                elif key.isdigit():
                    # Allow direct number selection
                    num = int(key) - 1
                    if 0 <= num < len(self.main_menu_options):
                        self.current_selection = num
                        return self.current_selection
                        
            except KeyboardInterrupt:
                return len(self.main_menu_options) - 1  # Quit
    
    def arrow_select_from_list(self, items: List[str], title: str, allow_cancel: bool = True) -> Optional[int]:
        """Generic arrow key selection from a list."""
        if not items:
            return None
            
        selection = 0
        
        while True:
            self.clear_screen()
            self.show_header()
            
            self.console.print(f"[bold blue]{title}[/bold blue]")
            self.console.print()
            
            for i, item in enumerate(items):
                if i == selection:
                    self.console.print(f"👉 [{i+1}] [bold blue on white]{item}[/bold blue on white]")
                else:
                    self.console.print(f"   [{i+1}] {item}")
            
            if allow_cancel:
                self.console.print()
                self.console.print("[dim]↑↓ to navigate, Enter to select, Esc to cancel[/dim]")
            else:
                self.console.print()
                self.console.print("[dim]↑↓ to navigate, Enter to select[/dim]")
            
            try:
                key = self.get_key()
                
                if key == 'up':
                    selection = (selection - 1) % len(items)
                elif key == 'down':
                    selection = (selection + 1) % len(items)
                elif key == 'enter':
                    return selection
                elif key == 'escape' and allow_cancel:
                    return None
                elif key == 'ctrl_c':
                    raise KeyboardInterrupt
                elif key.isdigit():
                    num = int(key) - 1
                    if 0 <= num < len(items):
                        return num
                        
            except KeyboardInterrupt:
                if allow_cancel:
                    return None
                raise
    
    def load_current_servers(self):
        """Load servers for the currently selected application."""
        self.current_servers = {}
        
        config_path = self.synchronizer.CONFIG_FILES[self.current_app]
        if not config_path.exists():
            return
        
        config = self.synchronizer.load_existing_config(config_path)
        if not config:
            return
        
        handler = self.synchronizer.detect_config_format(config)
        mcp_config = handler.extract_mcp_config(config)
        
        servers = mcp_config.get('servers', {})
        for name, server_data in servers.items():
            self.current_servers[name] = MCPServer.from_dict(name, server_data)
    
    def save_current_servers(self):
        """Save current servers back to the application's config file."""
        config_path = self.synchronizer.CONFIG_FILES[self.current_app]
        
        # Load existing config
        existing_config = self.synchronizer.load_existing_config(config_path) or {}
        
        # Get appropriate handler
        handler = self.synchronizer.get_app_handler(self.current_app)
        
        # Build MCP config
        mcp_config = {
            "servers": {name: server.to_dict() for name, server in self.current_servers.items()}
        }
        
        # Merge with existing config
        updated_config = handler.merge_mcp_config(existing_config, mcp_config)
        
        # Save to file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(updated_config, f, indent=2)
    
    def switch_application(self):
        """Switch to a different application using arrow navigation."""
        apps = list(self.synchronizer.CONFIG_FILES.keys())
        current_index = apps.index(self.current_app) if self.current_app in apps else 0
        
        # Show current selection first
        for i, app in enumerate(apps):
            if i == current_index:
                break
        
        selection = self.arrow_select_from_list(
            apps, 
            "📱 Select Application",
            allow_cancel=True
        )
        
        if selection is not None and selection != current_index:
            self.current_app = apps[selection]
            self.load_current_servers()
            
            self.clear_screen()
            self.show_header()
            self.console.print(f"✅ Switched to [bold cyan]{self.current_app}[/bold cyan]")
            self.console.print()
            input("Press Enter to continue...")
    
    def add_or_edit_server(self):
        """Add a new MCP server or edit existing one."""
        self.clear_screen()
        self.show_header()
        self.console.print("[bold green]Add or Edit MCP Server[/bold green]")
        self.console.print()
        self.console.print(f"📱 Current Application: [bold cyan]{self.current_app}[/bold cyan]")
        self.console.print()
        
        # Show existing servers if any
        if self.current_servers:
            self.console.print("[bold white]Existing servers:[/bold white]")
            server_list = list(self.current_servers.keys())
            for i, server_name in enumerate(server_list, 1):
                self.console.print(f"  {i}. [cyan]{server_name}[/cyan]")
            self.console.print()
            
            # Ask if they want to edit existing or add new
            self.console.print("[bold white]Choose action:[/bold white]")
            self.console.print("1. Add new server")
            self.console.print("2. Edit existing server")
            self.console.print()
            
            action = Prompt.ask("Action", choices=["1", "2"], default="1")
            
            if action == "2":
                # Edit existing server
                self.edit_server()
                return
        
        # Add new server with JSON input
        self.clear_screen()
        self.show_header()
        self.console.print("[bold green]Add New MCP Server[/bold green]")
        self.console.print()
        self.console.print(f"📱 Adding to: [bold cyan]{self.current_app}[/bold cyan]")
        self.console.print()
        self.console.print("[dim]Example formats:[/dim]")
        self.console.print('[dim]{"server_name": {"command": "docker", "args": ["run", "-i"], "env": {"TOKEN": "value"}}}[/dim]')
        self.console.print('[dim]"terminal-controller": {"command": "uvx", "args": ["terminal_controller"]}[/dim]')
        self.console.print()
        self.console.print("[yellow]Paste your JSON configuration below. Press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows) when done:[/yellow]")
        self.console.print()
        
        # Read multi-line input
        json_lines = []
        try:
            while True:
                try:
                    line = input()
                    json_lines.append(line)
                except EOFError:
                    break
        except KeyboardInterrupt:
            self.console.print("[red]Operation cancelled[/red]")
            input("Press Enter to continue...")
            return
        
        json_input = '\n'.join(json_lines).strip()
        
        if not json_input:
            self.console.print("[yellow]No JSON input provided[/yellow]")
            input("Press Enter to continue...")
            return
        
        try:
            # Try to parse as JSON - if it fails, maybe it's a partial config
            if not json_input.startswith('{'):
                json_input = '{' + json_input + '}'
            
            server_data = json.loads(json_input)
            if not isinstance(server_data, dict):
                raise ValueError("Must be a JSON object")
            
            # Handle three formats:
            # 1. {"server_name": {"command": "...", "args": [...], "env": {...}}}
            # 2. {"command": "...", "args": [...], "env": {...}}
            # 3. "server_name": {"command": "...", "args": [...]} (partial from README)
            
            if len(server_data) == 1:
                key = list(server_data.keys())[0]
                value = server_data[key]
                
                if isinstance(value, dict) and 'command' in value:
                    # Format 1 or 3: {"server_name": {config}}
                    server_name = key
                    config = value
                elif 'command' in server_data:
                    # Format 2: just the config object
                    server_name = Prompt.ask("Server name")
                    config = server_data
                else:
                    raise ValueError("Invalid server configuration format")
            elif 'command' in server_data:
                # Format 2: {"command": "...", "args": [...], "env": {...}}
                server_name = Prompt.ask("Server name")
                config = server_data
            else:
                raise ValueError("Could not detect server configuration format")
            
            if not server_name or server_name in self.current_servers:
                self.console.print("[red]Invalid or duplicate server name[/red]")
                input("Press Enter to continue...")
                return
            
            command = config.get('command', '')
            if not command:
                self.console.print("[red]Command is required in JSON config[/red]")
                input("Press Enter to continue...")
                return
            
            args = config.get('args', [])
            env = config.get('env', {})
            
            if not isinstance(args, list):
                self.console.print("[red]Arguments must be a list[/red]")
                input("Press Enter to continue...")
                return
            
            if not isinstance(env, dict):
                self.console.print("[red]Environment must be an object[/red]")
                input("Press Enter to continue...")
                return
            
            # Create and save server
            server = MCPServer(name=server_name, command=command, args=args, env=env)
            self.current_servers[server_name] = server
            self.save_current_servers()
            
            self.console.print(f"✅ Server '[bold cyan]{server_name}[/bold cyan]' added successfully")
            
        except json.JSONDecodeError as e:
            self.console.print(f"[red]Invalid JSON format: {e}[/red]")
            input("Press Enter to continue...")
            return
        except ValueError as e:
            self.console.print(f"[red]Invalid configuration: {e}[/red]")
            input("Press Enter to continue...")
            return
        except KeyboardInterrupt:
            self.console.print("[red]Operation cancelled[/red]")
        
        self.console.print()
        input("Press Enter to continue...")
    
    def edit_server(self):
        """Edit an existing MCP server using arrow navigation."""
        if not self.current_servers:
            self.clear_screen()
            self.show_header()
            self.console.print("[yellow]No servers available to edit[/yellow]")
            input("Press Enter to continue...")
            return
        
        servers = list(self.current_servers.keys())
        selection = self.arrow_select_from_list(
            servers,
            "🔧 Select Server to Edit",
            allow_cancel=True
        )
        
        if selection is None:
            return
        
        server_name = servers[selection]
        server = self.current_servers[server_name]
        
        self.clear_screen()
        self.show_header()
        self.console.print(f"[bold yellow]Edit Server: {server_name}[/bold yellow]")
        self.console.print()
        
        try:
            # Edit fields
            new_command = Prompt.ask("Command", default=server.command)
            
            args_default = " ".join(server.args)
            new_args_input = Prompt.ask("Arguments (space-separated)", default=args_default)
            new_args = new_args_input.split() if new_args_input else []
            
            env_default = json.dumps(server.env, indent=2) if server.env else "{}"
            new_env_input = Prompt.ask("Environment variables (JSON)", default=env_default)
            
            try:
                new_env = json.loads(new_env_input) if new_env_input else {}
                if not isinstance(new_env, dict):
                    raise ValueError("Must be a JSON object")
            except json.JSONDecodeError:
                self.console.print("[red]Invalid JSON format for environment variables[/red]")
                input("Press Enter to continue...")
                return
            
            # Update server
            server.command = new_command
            server.args = new_args
            server.env = new_env
            
            self.save_current_servers()
            self.console.print(f"✅ Server '[bold cyan]{server_name}[/bold cyan]' updated successfully")
            
        except KeyboardInterrupt:
            self.console.print("[red]Operation cancelled[/red]")
        
        self.console.print()
        input("Press Enter to continue...")
    
    def delete_server(self):
        """Delete an existing MCP server using arrow navigation."""
        if not self.current_servers:
            self.clear_screen()
            self.show_header()
            self.console.print("[yellow]No servers available to delete[/yellow]")
            input("Press Enter to continue...")
            return
        
        servers = list(self.current_servers.keys())
        selection = self.arrow_select_from_list(
            servers,
            "🗑️  Select Server to Delete",
            allow_cancel=True
        )
        
        if selection is None:
            return
        
        server_name = servers[selection]
        
        self.clear_screen()
        self.show_header()
        if Confirm.ask(f"Are you sure you want to delete '[bold red]{server_name}[/bold red]'?"):
            del self.current_servers[server_name]
            self.save_current_servers()
            self.console.print(f"✅ Server '[bold red]{server_name}[/bold red]' deleted successfully")
        else:
            self.console.print("[yellow]Deletion cancelled[/yellow]")
        
        self.console.print()
        input("Press Enter to continue...")
    
    def sync_mcp_configs(self):
        """Sync selected MCP servers to selected applications using arrow navigation."""
        if not self.current_servers:
            self.clear_screen()
            self.show_header()
            self.console.print("[yellow]No servers to sync[/yellow]")
            input("Press Enter to continue...")
            return
        
        # First, select which servers to sync
        self.clear_screen()
        self.show_header()
        self.console.print(f"[bold blue]Select MCP Servers to Sync[/bold blue]")
        self.console.print()
        self.console.print(f"Source: [bold cyan]{self.current_app}[/bold cyan]")
        self.console.print()
        
        server_names = list(self.current_servers.keys())
        selected_servers = []
        
        # Use checkboxes for server selection
        for server_name in server_names:
            self.clear_screen()
            self.show_header()
            self.console.print(f"[bold blue]Select MCP Servers to Sync[/bold blue]")
            self.console.print()
            self.console.print(f"Source: [bold cyan]{self.current_app}[/bold cyan]")
            self.console.print()
            
            # Show already selected servers
            if selected_servers:
                self.console.print("[bold green]Selected servers:[/bold green]")
                for selected in selected_servers:
                    self.console.print(f"  ✅ [green]{selected}[/green]")
                self.console.print()
            
            if Confirm.ask(f"Include [bold yellow]{server_name}[/bold yellow]?", default=True):
                selected_servers.append(server_name)
        
        if not selected_servers:
            self.clear_screen()
            self.show_header()
            self.console.print("[yellow]No servers selected for sync[/yellow]")
            input("Press Enter to continue...")
            return
        
        # Confirm selected servers
        self.clear_screen()
        self.show_header()
        self.console.print(f"[bold blue]Confirm Selected Servers[/bold blue]")
        self.console.print()
        self.console.print(f"Source: [bold cyan]{self.current_app}[/bold cyan]")
        self.console.print()
        self.console.print("[bold white]Servers to sync:[/bold white]")
        for i, server_name in enumerate(selected_servers, 1):
            self.console.print(f"  {i}. [green]{server_name}[/green]")
        self.console.print()
        
        if not Confirm.ask(f"Use these [bold yellow]{len(selected_servers)}[/bold yellow] servers from [bold cyan]{self.current_app}[/bold cyan] as the source?", default=True):
            self.console.print("[yellow]Sync cancelled[/yellow]")
            self.console.print()
            input("Press Enter to continue...")
            return
        
        # Get other apps (excluding current app)
        apps = [app for app in self.synchronizer.CONFIG_FILES.keys() if app != self.current_app]
        selected_apps = []
        
        # Use arrow navigation for each app
        for app in apps:
            self.clear_screen()
            self.show_header()
            self.console.print(f"[bold blue]Select Target Applications[/bold blue]")
            self.console.print()
            self.console.print(f"Source: [bold cyan]{self.current_app}[/bold cyan] → Target: [bold yellow]{app}[/bold yellow]")
            self.console.print(f"Servers: [bold white]{', '.join(selected_servers)}[/bold white]")
            self.console.print()
            
            if Confirm.ask(f"Sync to [bold yellow]{app}[/bold yellow]?", default=True):
                selected_apps.append(app)
        
        if not selected_apps:
            self.clear_screen()
            self.show_header()
            self.console.print("[yellow]No applications selected for sync[/yellow]")
            input("Press Enter to continue...")
            return
        
        # Final confirmation
        self.clear_screen()
        self.show_header()
        self.console.print(f"[bold magenta]Sync Confirmation[/bold magenta]")
        self.console.print()
        self.console.print(f"Source: [bold cyan]{self.current_app}[/bold cyan]")
        self.console.print(f"Servers: [bold white]{', '.join(selected_servers)}[/bold white] ([bold yellow]{len(selected_servers)}[/bold yellow] servers)")
        self.console.print(f"Targets: [bold yellow]{', '.join(selected_apps)}[/bold yellow] ([bold yellow]{len(selected_apps)}[/bold yellow] apps)")
        self.console.print()
        
        if not Confirm.ask(f"Proceed with syncing [bold yellow]{len(selected_servers)}[/bold yellow] servers to [bold yellow]{len(selected_apps)}[/bold yellow] applications?", default=True):
            self.console.print("[yellow]Sync cancelled[/yellow]")
            self.console.print()
            input("Press Enter to continue...")
            return
        
        self.console.print(f"[bold blue]Syncing {len(selected_servers)} servers to {len(selected_apps)} applications...[/bold blue]")
        
        # Build config with only selected servers
        selected_server_data = {name: self.current_servers[name] for name in selected_servers}
        sync_config = {
            "servers": {name: server.to_dict() for name, server in selected_server_data.items()}
        }
        
        self.synchronizer.config = sync_config
        sync_results = self.synchronizer.update_configs()
        
        # Count results for selected apps only
        success_count = sum(1 for app in selected_apps if sync_results.get(app, {}).get('success', False))
        
        if success_count == len(selected_apps):
            self.console.print(f"✅ [bold green]Sync completed: {len(selected_servers)} servers synced to {success_count}/{len(selected_apps)} apps[/bold green]")
        else:
            self.console.print(f"⚠️ [bold yellow]Partial sync: {len(selected_servers)} servers synced to {success_count}/{len(selected_apps)} apps[/bold yellow]")
        
        self.console.print()
        input("Press Enter to continue...")
    
    def show_app_status(self):
        """Show sync status for all applications."""
        self.clear_screen()
        self.show_header()
        
        all_in_sync, validation_results = self.synchronizer.validate_configs()
        
        table = Table(
            title="📊 Application Status",
            box=box.ROUNDED,
            show_header=True,
            title_style="bold blue"
        )
        table.add_column("Application", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Servers", justify="right")
        table.add_column("Format", style="dim")
        
        for app_name, config_path in self.synchronizer.CONFIG_FILES.items():
            if config_path.exists():
                validation = validation_results.get(app_name, {})
                in_sync = validation.get('in_sync', False)
                format_name = validation.get('format', 'Unknown')
                
                # Count servers
                config = self.synchronizer.load_existing_config(config_path)
                if config:
                    handler = self.synchronizer.detect_config_format(config)
                    mcp_config = handler.extract_mcp_config(config)
                    server_count = len(mcp_config.get('servers', {}))
                else:
                    server_count = 0
                
                status = "✅ Synced" if in_sync else "⚠️ Out of sync"
                table.add_row(app_name, status, str(server_count), format_name)
            else:
                table.add_row(app_name, "❌ Missing", "0", "—")
        
        self.console.print(table)
        self.console.print()
        input("Press Enter to continue...")
    
    def show_server_overview(self):
        """Show all MCP servers across all applications."""
        self.clear_screen()
        self.show_header()
        
        self.console.print("[bold blue]🔍 MCP Server Overview - All Applications[/bold blue]")
        self.console.print()
        
        # Create a comprehensive table
        table = Table(
            title="MCP Servers Across All Applications",
            box=box.ROUNDED,
            show_header=True,
            title_style="bold magenta"
        )
        table.add_column("Application", style="cyan", no_wrap=True)
        table.add_column("Server Name", style="green", no_wrap=True)
        table.add_column("Command", style="white")
        table.add_column("Arguments", style="yellow")
        table.add_column("Environment", style="blue")
        table.add_column("Status", justify="center")
        
        total_servers = 0
        apps_with_servers = 0
        
        for app_name, config_path in self.synchronizer.CONFIG_FILES.items():
            if config_path.exists():
                config = self.synchronizer.load_existing_config(config_path)
                if config:
                    handler = self.synchronizer.detect_config_format(config)
                    mcp_config = handler.extract_mcp_config(config)
                    servers = mcp_config.get('servers', {})
                    
                    if servers:
                        apps_with_servers += 1
                        for server_name, server_data in servers.items():
                            total_servers += 1
                            
                            command = server_data.get('command', '')
                            args = server_data.get('args', [])
                            env = server_data.get('env', {})
                            
                            args_display = " ".join(args) if args else "—"
                            if len(args_display) > 25:
                                args_display = args_display[:22] + "..."
                            
                            env_display = f"{len(env)} vars" if env else "—"
                            
                            # Determine status
                            status = "✅ Active"
                            
                            table.add_row(
                                app_name,
                                server_name,
                                command[:30] + ("..." if len(command) > 30 else ""),
                                args_display,
                                env_display,
                                status
                            )
                    else:
                        table.add_row(app_name, "—", "No servers configured", "—", "—", "⚪ Empty")
                else:
                    table.add_row(app_name, "—", "Invalid config", "—", "—", "❌ Error")
            else:
                table.add_row(app_name, "—", "Config file missing", "—", "—", "⭕ Missing")
        
        self.console.print(table)
        self.console.print()
        
        # Summary information
        total_apps = len(self.synchronizer.CONFIG_FILES)
        summary_text = f"📊 Summary: [bold yellow]{total_servers}[/bold yellow] servers across [bold cyan]{apps_with_servers}[/bold cyan] of [bold white]{total_apps}[/bold white] applications"
        summary_panel = Panel(
            summary_text,
            border_style="green",
            padding=(0, 2)
        )
        self.console.print(summary_panel)
        self.console.print()
        
        # Sync status check
        all_in_sync, validation_results = self.synchronizer.validate_configs()
        if all_in_sync:
            self.console.print("✅ [bold green]All applications are synchronized[/bold green]")
        else:
            out_of_sync_apps = [app for app, result in validation_results.items() if not result.get('in_sync', False)]
            self.console.print(f"⚠️ [bold yellow]{len(out_of_sync_apps)} applications are out of sync: {', '.join(out_of_sync_apps)}[/bold yellow]")
        
        self.console.print()
        input("Press Enter to continue...")

    def refresh_data(self):
        """Refresh all data."""
        self.clear_screen()
        self.show_header()
        self.console.print("[bold white]Refreshing data...[/bold white]")
        self.load_current_servers()
        self.console.print("✅ [bold green]Data refreshed[/bold green]")
        self.console.print()
        input("Press Enter to continue...")
    
    def run(self):
        """Run the main application loop."""
        # Initial data load
        self.load_current_servers()
        
        # Show overview immediately to orient the user
        self.show_server_overview()
        
        while self.running:
            choice = self.navigate_menu()
            
            if choice == 0:  # MCP Server Overview
                self.show_server_overview()
            elif choice == 1:  # Switch Application
                self.switch_application()
            elif choice == 2:  # Add or Edit MCP Server
                self.add_or_edit_server()
            elif choice == 3:  # Delete Server
                self.delete_server()
            elif choice == 4:  # Sync MCP Configs
                self.sync_mcp_configs()
            elif choice == 5:  # Show App Status
                self.show_app_status()
            elif choice == 6:  # Refresh Data
                self.refresh_data()
            elif choice == 7:  # Quit
                self.running = False
        
        self.clear_screen()
        self.console.print("[bold blue]Thank you for using MCP Configuration Manager![/bold blue]")


def main():
    """Main entry point for the MCP Configuration Manager."""
    try:
        ui = MCPConfigurationManager()
        ui.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")


if __name__ == "__main__":
    main()