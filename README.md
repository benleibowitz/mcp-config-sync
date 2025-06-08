# MCP Configuration Manager

A comprehensive toolkit for managing Model Context Protocol (MCP) server configurations across multiple applications, featuring both command-line tools and an intuitive terminal user interface.

## 🚀 Features

### Core Functionality
- **Multi-Format Support**: Handles different MCP configuration formats across applications
- **Real-Time Sync**: Automatic file watching with instant synchronization
- **Format Detection**: Automatically detects and converts between configuration formats
- **Conflict Resolution**: Intelligent handling of simultaneous changes with debouncing
- **Comprehensive Coverage**: Supports 6+ applications with different MCP implementations
- **Preservation**: Maintains application-specific settings while syncing MCP configs
- **🛡️ Safety Protection**: Prevents accidental loss of MCP servers with confirmation prompts

### User Interfaces
- **🖥️ Terminal UI**: Beautiful arrow key navigation interface for interactive management
- **⚡ Command Line**: Powerful CLI tools for automation and scripting
- **📊 Server Overview**: Comprehensive view of all MCP servers across applications
- **🎯 Granular Control**: Select specific servers and target applications for syncing

## 📱 Supported Applications

| Application | Configuration Format | File Location |
|-------------|---------------------|---------------|
| **Claude Desktop** | `mcpServers` | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **VSCode** | `mcp.servers` | `~/Library/Application Support/Code/User/settings.json` |
| **Cursor** | `mcp.*` | `~/.cursor/mcp.json` |
| **Windsurf** | `mcp.*` | `~/.codeium/windsurf/mcp_config.json` |
| **Roocode (VSCode)** | `mcp.*` | `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| **Roocode (Windsurf)** | `mcp.*` | `~/Library/Application Support/Windsurf - Next/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` |

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/benleibowitz/mcp-config-sync.git
cd mcp-config-sync
```

2. Setup virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📖 Usage

### 🖥️ Terminal User Interface (Recommended)

**MCP Configuration Manager** - Interactive terminal interface with arrow key navigation:
```bash
source venv/bin/activate && python3 mcp_config_manager.py
```

**Features:**
- **MCP Server Overview**: See all servers across all applications at startup
- **JSON Input**: Paste server configurations directly from READMEs
- **Add/Edit Servers**: Unified interface for server management
- **Granular Sync**: Select specific servers and target applications
- **Real-time Status**: Live sync status and validation across apps

**Demo Interfaces:**
```bash
# Safe demo with sample data (no real config changes)
source venv/bin/activate && python3 demo_ui.py

# Clean menu-driven interface
source venv/bin/activate && python3 simple_ui.py

# Arrow key navigation demo
source venv/bin/activate && python3 arrow_demo.py
```

### ⚡ Command Line Interface

**One-Time Synchronization:**
```bash
# Apply default configuration to all applications
source venv/bin/activate && python3 mcp_sync.py

# Sync from existing application (use as source of truth)
source venv/bin/activate && python3 mcp_sync.py --source Claude
source venv/bin/activate && python3 mcp_sync.py --source VSCode
source venv/bin/activate && python3 mcp_sync.py --source Cursor
```

**🤖 Automatic Real-Time Sync:**
```bash
# Continuous daemon mode (watches all apps)
source venv/bin/activate && python3 mcp_sync.py --daemon

# Watch specific applications
source venv/bin/activate && python3 mcp_sync.py --daemon --watch Claude,VSCode,Cursor

# One-time watch with timeout
source venv/bin/activate && python3 mcp_sync.py --watch-once --timeout 30

# Custom debounce delay (prevents rapid successive syncs)
source venv/bin/activate && python3 mcp_sync.py --daemon --debounce 5.0
```

**🛡️ Safety Features:**
```bash
# Interactive confirmation (default behavior)
source venv/bin/activate && python3 mcp_sync.py --source empty_config.json

# Skip confirmation for automation
source venv/bin/activate && python3 mcp_sync.py --source empty_config.json --force
```

**Advanced Options:**
```bash
# Custom file path as source
source venv/bin/activate && python3 mcp_sync.py --source /path/to/custom/config.json

# View available applications
source venv/bin/activate && python3 mcp_sync.py --help
```

## 🎯 Server Configuration Formats

The terminal UI supports **three different JSON input formats** you might find in MCP server documentation:

### Format 1: Complete Configuration
```json
{
  "github": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "mcp/github"],
    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"}
  }
}
```

### Format 2: Server Config Only
```json
{
  "command": "uvx",
  "args": ["terminal_controller"]
}
```
*(Will prompt for server name)*

### Format 3: Partial from README
```json
"terminal-controller": {
  "command": "uvx",
  "args": ["terminal_controller"]
}
```
*(Auto-detects server name)*

**Simply copy/paste any of these formats directly from documentation!**

## 🏗️ How It Works

### Configuration Format Handling

The tool intelligently detects and converts between different MCP configuration formats:

1. **Claude Desktop Format**:
   ```json
   {
     "mcpServers": {
       "server-name": { "command": "...", "args": [...] }
     }
   }
   ```

2. **VSCode Format**:
   ```json
   {
     "other-settings": "...",
     "mcp": {
       "inputs": [],
       "servers": {
         "server-name": { "command": "...", "args": [...] }
       }
     }
   }
   ```

3. **Standard MCP Format**:
   ```json
   {
     "mcp": {
       "server_endpoint": "...",
       "servers": { ... }
     }
   }
   ```

### Automatic Sync Process

1. **File Monitoring**: Watches configuration file directories
2. **Change Detection**: Identifies which application's config changed
3. **Format Recognition**: Determines source configuration format
4. **Debounced Sync**: Waits for edits to complete (2-second default)
5. **Cross-Format Conversion**: Converts to each app's expected format
6. **Conflict Avoidance**: Prevents sync loops from self-triggered changes

## 🛠️ Enhanced Features & Architecture

### 🎨 Terminal User Interface
- **MCP Configuration Manager**: Beautiful arrow key navigation interface
- **JSON Input Support**: Paste configurations directly from documentation
- **Server Overview**: Comprehensive view of all servers across applications
- **Granular Control**: Select specific servers and target applications
- **Real-time Validation**: Live sync status and error reporting

### 🔥 Core Engine Features
- **Real-time file watching** with automatic synchronization
- **Multi-format configuration handling** (4+ different formats)
- **Intelligent conflict resolution** and debouncing
- **Daemon mode** for continuous monitoring
- **VSCode settings.json support** with format detection

### 🧠 Smart Architecture
- **Format-specific handlers** for clean separation of concerns
- **Automatic format detection** and normalization
- **Extensible design** for easy addition of new applications
- **Robust error handling** and comprehensive logging

### 🎯 User Experience
- **Multiple interfaces**: Terminal UI, CLI, and demo modes
- **Flexible JSON input**: Supports various documentation formats
- **Settings preservation** (maintains app-specific configurations)
- **Cross-platform compatibility** (macOS/Linux/Windows)

### 🔒 Safety & Reliability
- **Destructive operation protection** with user confirmation prompts
- **Graceful error handling** for missing/corrupted files
- **Signal handling** for clean daemon shutdown
- **Thread-safe operations** for concurrent file access
- **Format-aware validation** with detailed reporting

## 📋 Requirements

- **Python 3.7+**
- Dependencies listed in `requirements.txt`
- **macOS/Linux/Windows** (cross-platform)

## 🚦 Exit Codes

- `0`: Success
- `1`: Synchronization failed or validation errors

## 📄 License

MIT License
