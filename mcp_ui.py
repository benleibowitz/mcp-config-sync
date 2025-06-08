#!/usr/bin/env python3
"""
Beautiful Terminal UI for MCP Configuration Management

This application provides an interactive terminal interface for managing
MCP servers across multiple applications with real-time synchronization.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, Static, DataTable, Input, Select, 
    TextArea, Label, Tree, Collapsible, Switch, Checkbox, ProgressBar,
    ListView, ListItem, OptionList
)
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual import events
from textual.coordinate import Coordinate

from rich.text import Text

from mcp_core import MCPConfigSynchronizer


@dataclass
class MCPServer:
    """Data class representing an MCP server configuration."""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env if self.env else None
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'MCPServer':
        """Create MCPServer from dictionary data."""
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            enabled=True
        )


class ServerFormScreen(ModalScreen):
    """Modal screen for adding/editing MCP servers."""
    
    CSS = """
    ServerFormScreen {
        align: center middle;
    }
    
    .form-container {
        background: $surface;
        border: thick $primary;
        width: 80;
        height: 25;
        padding: 2;
    }
    
    .form-field {
        margin: 1 0;
    }
    
    .form-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
        Binding("tab", "focus_next", "Next Field"),
        Binding("shift+tab", "focus_previous", "Previous Field"),
    ]
    
    def __init__(self, server: Optional[MCPServer] = None, is_edit: bool = False):
        super().__init__()
        self.server = server
        self.is_edit = is_edit
        self.result: Optional[MCPServer] = None
    
    def compose(self) -> ComposeResult:
        title = "Edit MCP Server" if self.is_edit else "Add MCP Server"
        
        with Container(classes="form-container"):
            yield Label(f"{title} - Use TAB to navigate, Ctrl+S to save, ESC to cancel", classes="form-field")
            
            yield Label("Server Name:", classes="form-field")
            yield Input(
                value=self.server.name if self.server else "",
                placeholder="e.g., filesystem, database, api",
                id="name_input",
                classes="form-field"
            )
            
            yield Label("Command:", classes="form-field")
            yield Input(
                value=self.server.command if self.server else "",
                placeholder="e.g., python, node, /path/to/executable",
                id="command_input",
                classes="form-field"
            )
            
            yield Label("Arguments (one per line):", classes="form-field")
            yield TextArea(
                text="\n".join(self.server.args) if self.server else "",
                id="args_input",
                classes="form-field"
            )
            
            yield Label("Environment Variables (JSON format):", classes="form-field")
            yield TextArea(
                text=json.dumps(self.server.env, indent=2) if self.server and self.server.env else "{}",
                id="env_input",
                classes="form-field"
            )
            
            with Horizontal(classes="form-buttons"):
                yield Button("Save (Ctrl+S)", id="save_btn", variant="primary")
                yield Button("Cancel (Esc)", id="cancel_btn")
    
    def on_mount(self) -> None:
        """Set initial focus when screen mounts."""
        self.query_one("#name_input").focus()
    
    def action_save(self) -> None:
        """Save action triggered by Ctrl+S."""
        self._save_server()
    
    def action_cancel(self) -> None:
        """Cancel action triggered by ESC."""
        self.dismiss(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self._save_server()
        elif event.button.id == "cancel_btn":
            self.dismiss(None)
    
    def _save_server(self) -> None:
        """Validate and save the server configuration."""
        try:
            name = self.query_one("#name_input", Input).value.strip()
            command = self.query_one("#command_input", Input).value.strip()
            args_text = self.query_one("#args_input", TextArea).text.strip()
            env_text = self.query_one("#env_input", TextArea).text.strip()
            
            if not name or not command:
                self.notify("Name and command are required", severity="error")
                return
            
            args = [arg.strip() for arg in args_text.split('\n') if arg.strip()]
            
            try:
                env = json.loads(env_text) if env_text else {}
                if not isinstance(env, dict):
                    raise ValueError("Environment must be a JSON object")
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON in environment variables: {e}", severity="error")
                return
            
            server = MCPServer(
                name=name,
                command=command,
                args=args,
                env=env
            )
            
            self.dismiss(server)
            
        except Exception as e:
            self.notify(f"Error saving server: {e}", severity="error")


class SyncScreen(ModalScreen):
    """Modal screen for managing synchronization across applications."""
    
    CSS = """
    SyncScreen {
        align: center middle;
    }
    
    .sync-container {
        background: $surface;
        border: thick $primary;
        width: 90;
        height: 30;
        padding: 2;
    }
    
    .sync-options {
        height: 12;
        margin: 1 0;
    }
    
    .sync-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    
    .option-list {
        border: solid $accent;
        height: 8;
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("enter", "sync", "Sync"),
        Binding("escape", "cancel", "Cancel"),
        Binding("tab", "focus_next", "Next"),
        Binding("shift+tab", "focus_previous", "Previous"),
        Binding("space", "toggle_selection", "Toggle"),
    ]
    
    def __init__(self, synchronizer: MCPConfigSynchronizer, available_servers: Dict[str, MCPServer]):
        super().__init__()
        self.synchronizer = synchronizer
        self.available_servers = available_servers
        self.selected_servers = set(available_servers.keys())
        self.selected_apps = set(synchronizer.CONFIG_FILES.keys())
        self.current_focus = "servers"
    
    def compose(self) -> ComposeResult:
        with Container(classes="sync-container"):
            yield Label("🔄 Synchronize MCP Servers", id="sync-title")
            yield Label("Use ↑↓ to navigate, SPACE to toggle, TAB to switch sections", id="sync-help")
            
            yield Label("📦 Select servers to sync (SPACE to toggle):", classes="sync-options")
            
            server_options = [(name, name, name in self.selected_servers) for name in self.available_servers.keys()]
            yield OptionList(
                *server_options,
                id="server_list",
                classes="option-list"
            )
            
            yield Label("📱 Select target applications (SPACE to toggle):", classes="sync-options")
            
            app_options = [(name, name, name in self.selected_apps) for name in self.synchronizer.CONFIG_FILES.keys()]
            yield OptionList(
                *app_options,
                id="app_list",
                classes="option-list"
            )
            
            with Horizontal(classes="sync-buttons"):
                yield Button("Sync (Enter)", id="sync_btn", variant="primary")
                yield Button("Cancel (Esc)", id="cancel_btn")
    
    def on_mount(self) -> None:
        """Set initial focus when screen mounts."""
        self.query_one("#server_list").focus()
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection/deselection."""
        option_list = event.option_list
        option_id = event.option.id
        
        if option_list.id == "server_list":
            if option_id in self.selected_servers:
                self.selected_servers.discard(option_id)
                option_list.remove_option_at(event.option_index)
                option_list.add_option((option_id, option_id, False), event.option_index)
            else:
                self.selected_servers.add(option_id)
                option_list.remove_option_at(event.option_index)
                option_list.add_option((option_id, option_id, True), event.option_index)
        elif option_list.id == "app_list":
            if option_id in self.selected_apps:
                self.selected_apps.discard(option_id)
                option_list.remove_option_at(event.option_index)
                option_list.add_option((option_id, option_id, False), event.option_index)
            else:
                self.selected_apps.add(option_id)
                option_list.remove_option_at(event.option_index)
                option_list.add_option((option_id, option_id, True), event.option_index)
    
    def action_sync(self) -> None:
        """Perform sync action."""
        self._perform_sync()
    
    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss(None)
    
    def action_toggle_selection(self) -> None:
        """Toggle selection of current option."""
        focused = self.focused
        if isinstance(focused, OptionList):
            if focused.highlighted is not None:
                # Simulate selection
                option = focused.get_option_at_index(focused.highlighted)
                if option:
                    event = OptionList.OptionSelected(focused, option, focused.highlighted)
                    self.on_option_list_option_selected(event)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sync_btn":
            self._perform_sync()
        elif event.button.id == "cancel_btn":
            self.dismiss(None)
    
    def _perform_sync(self) -> None:
        """Perform the synchronization operation."""
        if not self.selected_servers:
            self.notify("No servers selected for sync", severity="warning")
            return
        
        if not self.selected_apps:
            self.notify("No applications selected for sync", severity="warning")
            return
        
        # Build config with selected servers
        sync_config = {
            "servers": {
                name: self.available_servers[name].to_dict()
                for name in self.selected_servers
            }
        }
        
        # Update synchronizer config
        self.synchronizer.config = sync_config
        
        # Perform sync
        sync_results = self.synchronizer.update_configs()
        
        # Show results
        success_count = sum(1 for result in sync_results.values() if result.get('success', False))
        total_count = len(self.selected_apps)
        
        self.notify(f"Sync completed: {success_count}/{total_count} apps updated successfully")
        self.dismiss(sync_results)


class MCPManagerApp(App):
    """Main MCP Configuration Manager Application."""
    
    CSS = """
    MCPManagerApp {
        background: $background;
    }
    
    .sidebar {
        dock: left;
        width: 30;
        background: $surface;
        border-right: solid $primary;
    }
    
    .main-content {
        background: $background;
        padding: 1;
    }
    
    .app-selector {
        height: 8;
        margin: 1 0;
        border: solid $accent;
    }
    
    .server-list {
        border: solid $accent;
        margin: 1 0;
    }
    
    #server_table {
        background: $surface;
    }
    
    #server_table > .datatable--cursor {
        background: $primary;
        color: $text;
    }
    
    .action-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    
    .status-bar {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: solid $primary;
    }
    
    .app-status {
        background: $surface;
        border: solid $accent;
        height: 15;
        margin: 1 0;
        padding: 1;
    }
    
    #app_status_display {
        text-style: none;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_server", "Add Server"),
        Binding("e", "edit_server", "Edit Server"),
        Binding("d", "delete_server", "Delete Server"),
        Binding("s", "sync_configs", "Sync Configs"),
        Binding("r", "refresh", "Refresh"),
        Binding("1", "sync_all", "Sync All"),
        Binding("tab", "focus_next", "Next"),
        Binding("shift+tab", "focus_previous", "Previous"),
        Binding("up,down,left,right", "", "Navigate"),
    ]
    
    current_app = reactive("Claude")
    
    def __init__(self):
        super().__init__()
        self.synchronizer = MCPConfigSynchronizer()
        self.current_servers: Dict[str, MCPServer] = {}
        self.app_configs: Dict[str, Dict] = {}
        self.selected_server: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header()
        
        with Horizontal():
            # Sidebar
            with Vertical(classes="sidebar"):
                yield Label("📱 Applications (↑↓ to select, Enter to switch)", classes="sidebar-title")
                
                # Application selector using ListView for keyboard navigation
                yield ListView(
                    *[ListItem(Label(app), name=app) for app in self.synchronizer.CONFIG_FILES.keys()],
                    id="app_list",
                    classes="app-selector"
                )
                
                yield Label("🔧 MCP Servers (↑↓ to navigate, Enter to select)", classes="sidebar-title")
                yield Static("No server selected", id="selected_server_display", classes="form-field")
                
                # Server list
                yield DataTable(
                    id="server_table",
                    classes="server-list",
                    show_header=True,
                    zebra_stripes=True
                )
                
                # Action buttons with keyboard shortcuts shown
                with Horizontal(classes="action-buttons"):
                    yield Button("Add (A)", id="add_btn", variant="primary")
                    yield Button("Edit (E)", id="edit_btn", variant="default")
                    yield Button("Delete (D)", id="delete_btn", variant="error")
            
            # Main content area
            with Vertical(classes="main-content"):
                yield Label("📊 Application Status", id="main-title")
                
                # Application status display
                with ScrollableContainer(classes="app-status"):
                    yield Static("", id="app_status_display")
                
                # Sync controls with keyboard shortcuts
                with Horizontal(classes="action-buttons"):
                    yield Button("🔄 Sync All (1)", id="sync_all_btn", variant="primary")
                    yield Button("⚙️ Sync Selected (S)", id="sync_selected_btn", variant="default")
                    yield Button("🔍 Refresh (R)", id="refresh_btn", variant="default")
        
        # Status bar
        with Container(classes="status-bar"):
            yield Static("Ready", id="status_text")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        self.refresh_data()
        # Set initial focus to app list
        self.query_one("#app_list").focus()
        # Set initial selection in ListView
        app_list = self.query_one("#app_list", ListView)
        app_list.index = 0  # Select Claude (first item)
    
    def refresh_data(self) -> None:
        """Refresh all data from configuration files."""
        self.load_app_configs()
        self.load_current_servers()
        self.update_server_table()
        self.update_app_status()
    
    def load_app_configs(self) -> None:
        """Load configurations from all application files."""
        self.app_configs = {}
        for app_name, config_path in self.synchronizer.CONFIG_FILES.items():
            if config_path.exists():
                config = self.synchronizer.load_existing_config(config_path)
                if config is not None:
                    self.app_configs[app_name] = config
                    
        self.update_status(f"Loaded configs from {len(self.app_configs)} applications")
    
    def load_current_servers(self) -> None:
        """Load MCP servers for the currently selected application."""
        self.current_servers = {}
        
        if self.current_app in self.app_configs:
            config = self.app_configs[self.current_app]
            handler = self.synchronizer.detect_config_format(config)
            mcp_config = handler.extract_mcp_config(config)
            
            servers = mcp_config.get('servers', {})
            for name, server_data in servers.items():
                self.current_servers[name] = MCPServer.from_dict(name, server_data)
    
    def update_server_table(self) -> None:
        """Update the server table with current server data."""
        table = self.query_one("#server_table", DataTable)
        table.clear(columns=True)
        
        # Add columns
        table.add_column("Name", key="name")
        table.add_column("Command", key="command")
        table.add_column("Args", key="args")
        
        # Add rows and store mapping
        for server in self.current_servers.values():
            args_display = " ".join(server.args[:2]) + ("..." if len(server.args) > 2 else "")
            table.add_row(
                server.name,
                server.command[:20] + ("..." if len(server.command) > 20 else ""),
                args_display,
                key=server.name
            )
        
        # Clear selection when table is updated
        self.selected_server = None
        self._update_selected_server_display()
    
    def update_app_status(self) -> None:
        """Update the application status display."""
        # Validate configurations
        all_in_sync, validation_results = self.synchronizer.validate_configs()
        
        # Build status text using plain text formatting
        status_lines = ["📊 Application Status\n" + "=" * 50 + "\n"]
        
        for app_name, config_path in self.synchronizer.CONFIG_FILES.items():
            if config_path.exists():
                validation = validation_results.get(app_name, {})
                in_sync = validation.get('in_sync', False)
                format_name = validation.get('format', 'Unknown')
                
                # Count servers
                if app_name in self.app_configs:
                    config = self.app_configs[app_name]
                    handler = self.synchronizer.detect_config_format(config)
                    mcp_config = handler.extract_mcp_config(config)
                    server_count = len(mcp_config.get('servers', {}))
                else:
                    server_count = 0
                
                status_icon = "✅" if in_sync else "⚠️"
                status_text = "Synced" if in_sync else "Out of sync"
                
                status_lines.append(
                    f"📱 {app_name:<15} {status_icon} {status_text:<12} "
                    f"Servers: {server_count:<3} Format: {format_name}"
                )
            else:
                status_lines.append(
                    f"📱 {app_name:<15} ❌ Missing      "
                    f"Servers: 0   Format: —"
                )
        
        # Add summary
        total_apps = len(self.synchronizer.CONFIG_FILES)
        synced_apps = sum(1 for v in validation_results.values() if v.get('in_sync', False))
        
        status_lines.extend([
            "\n" + "-" * 50,
            f"Summary: {synced_apps}/{total_apps} applications synchronized"
        ])
        
        status_display = self.query_one("#app_status_display", Static)
        status_display.update("\n".join(status_lines))
    
    def update_status(self, message: str) -> None:
        """Update the status bar with a message."""
        status_text = self.query_one("#status_text", Static)
        status_text.update(message)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle application selection changes."""
        if event.list_view.id == "app_list":
            self.current_app = event.item.name
            self.load_current_servers()
            self.update_server_table()
            self.update_status(f"Switched to {self.current_app}")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle server selection in the table."""
        if event.data_table.id == "server_table":
            self._update_selected_server_from_table(event.data_table, event.cursor_row)
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle server highlighting in the table."""
        if event.data_table.id == "server_table":
            self._update_selected_server_from_table(event.data_table, event.cursor_row)
    
    def _update_selected_server_from_table(self, table: DataTable, cursor_row: int) -> None:
        """Update selected server from table cursor position."""
        try:
            # Get the row key which corresponds to the server name
            row_key = table.get_row_key_at(cursor_row)
            if row_key:
                self.selected_server = str(row_key)
                self._update_selected_server_display()
                return
            
            # Fallback: get the first column value (server name)
            row_data = table.get_row_at(cursor_row)
            if row_data and len(row_data) > 0:
                self.selected_server = str(row_data[0])
                self._update_selected_server_display()
                return
                
        except Exception as e:
            pass
        
        # If all else fails
        self.selected_server = None
        self._update_selected_server_display()
    
    def _update_selected_server_display(self) -> None:
        """Update the selected server display and status."""
        if self.selected_server:
            message = f"✅ Selected: {self.selected_server}"
            self.update_status(f"Selected server: {self.selected_server}")
        else:
            message = "No server selected"
            self.update_status("No server selected")
        
        try:
            selected_display = self.query_one("#selected_server_display", Static)
            selected_display.update(message)
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add_btn":
            self.action_add_server()
        elif event.button.id == "edit_btn":
            self.action_edit_server()
        elif event.button.id == "delete_btn":
            self.action_delete_server()
        elif event.button.id == "sync_all_btn":
            self.action_sync_all()
        elif event.button.id == "sync_selected_btn":
            self.action_sync_configs()
        elif event.button.id == "refresh_btn":
            self.action_refresh()
    
    def action_add_server(self) -> None:
        """Add a new MCP server."""
        def handle_result(server: Optional[MCPServer]) -> None:
            if server:
                self.current_servers[server.name] = server
                self.save_current_app_config()
                self.update_server_table()
                self.update_status(f"Added server: {server.name}")
        
        self.push_screen(ServerFormScreen(), handle_result)
    
    def action_edit_server(self) -> None:
        """Edit the selected MCP server."""
        if not self.selected_server or self.selected_server not in self.current_servers:
            self.notify("No server selected", severity="warning")
            return
        
        server = self.current_servers[self.selected_server]
        
        def handle_result(updated_server: Optional[MCPServer]) -> None:
            if updated_server:
                # Remove old server if name changed
                if updated_server.name != server.name:
                    del self.current_servers[server.name]
                
                self.current_servers[updated_server.name] = updated_server
                self.save_current_app_config()
                self.update_server_table()
                self.update_status(f"Updated server: {updated_server.name}")
        
        self.push_screen(ServerFormScreen(server, is_edit=True), handle_result)
    
    def action_delete_server(self) -> None:
        """Delete the selected MCP server."""
        if not self.selected_server or self.selected_server not in self.current_servers:
            self.notify("No server selected", severity="warning")
            return
        
        del self.current_servers[self.selected_server]
        self.save_current_app_config()
        self.update_server_table()
        self.update_status(f"Deleted server: {self.selected_server}")
        self.selected_server = None
    
    def save_current_app_config(self) -> None:
        """Save the current servers back to the application's config file."""
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
        
        # Update cached config
        self.app_configs[self.current_app] = updated_config
    
    def action_sync_all(self) -> None:
        """Sync the current application's servers to all other applications."""
        if not self.current_servers:
            self.notify("No servers to sync", severity="warning")
            return
        
        # Build config
        sync_config = {
            "servers": {name: server.to_dict() for name, server in self.current_servers.items()}
        }
        
        # Update synchronizer and sync
        self.synchronizer.config = sync_config
        sync_results = self.synchronizer.update_configs()
        
        # Show results
        success_count = sum(1 for result in sync_results.values() if result.get('success', False))
        total_count = len(sync_results)
        
        self.notify(f"Sync completed: {success_count}/{total_count} apps updated")
        self.refresh_data()
    
    def action_sync_configs(self) -> None:
        """Open the sync configuration screen."""
        def handle_result(sync_results: Optional[Dict]) -> None:
            if sync_results:
                self.refresh_data()
        
        self.push_screen(SyncScreen(self.synchronizer, self.current_servers), handle_result)
    
    def action_refresh(self) -> None:
        """Refresh all data."""
        self.refresh_data()
        self.update_status("Data refreshed")


def main():
    """Main entry point for the MCP Manager UI."""
    app = MCPManagerApp()
    app.run()


if __name__ == "__main__":
    main()