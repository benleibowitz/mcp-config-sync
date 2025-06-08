# MCP Configuration Manager

A comprehensive terminal interface for managing Model Context Protocol (MCP) server configurations across multiple applications, featuring intuitive arrow key navigation, flexible JSON input, and granular sync control.

## Quick Start
1. Clone the repository:
```bash
git clone https://github.com/benleibowitz/mcp-configuration-manager.git
cd mcp-configuration-manager
```

2) Setup a Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3) Install the required packages
```bash
pip install -r requirements.txt
```

4) Run the MCP Configuration Manager
```bash
./mcp_config_manager.py
```

## 🚀 Features

### 🎯 Primary Terminal Interface
- **📊 Server Overview**: Comprehensive view of all MCP servers across all applications at startup
- **🔧 JSON Input**: Paste configurations directly from documentation (handles 3 different formats)
- **🎮 Arrow Key Navigation**: Intuitive navigation with visual highlighting
- **🎛️ Granular Control**: Select specific servers and target applications for syncing
- **📱 Application Context**: Always shows which app you're managing
- **⚡ Real-time Validation**: Live sync status across all applications

### 🛠️ Core Engine
- **🔄 Multi-Format Support**: Handles different MCP configuration formats across applications
- **⏱️ Real-Time Sync**: Automatic file watching with instant synchronization
- **🔍 Format Detection**: Automatically detects and converts between configuration formats
- **⚖️ Conflict Resolution**: Intelligent handling of simultaneous changes with debouncing
- **🛡️ Safety Protection**: Prevents accidental loss of MCP servers with confirmation prompts

## 📱 Supported Applications

| Application | Configuration Format | File Location |
|-------------|---------------------|---------------|
| **Claude Desktop** | `mcpServers` | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **VSCode** | `mcp.servers` | `~/Library/Application Support/Code/User/settings.json` |
| **Cursor** | `mcp.*` | `~/.cursor/mcp.json` |
| **Windsurf** | `mcp.*` | `~/.codeium/windsurf/mcp_config.json` |
| **Roocode (VSCode)** | `mcp.*` | `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| **Roocode (Windsurf)** | `mcp.*` | `~/Library/Application Support/Windsurf - Next/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` |

## 📖 Usage

### 🖥️ Terminal Interface (Primary - Recommended)

**Launch the MCP Configuration Manager:**
```bash
./mcp_config_manager.py
```

## 🎯 JSON Input Formats

The terminal interface supports **three different JSON formats** you might find in MCP server documentation:

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
```
"terminal-controller": {
  "command": "uvx",
  "args": ["terminal_controller"]
}
```
*(Auto-detects server name)*

**Simply copy/paste any of these formats directly from documentation!**

## 🏗️ Architecture

### Core Components

- **`mcp_config_manager.py`** - Primary terminal interface with arrow navigation and JSON input
- **`mcp_core.py`** - Core engine with all synchronization classes and logic
- **`mcp_ui.py`** - Advanced Textual-based interface
- **Alternative UIs** - Simple menu-driven and demo interfaces

### How It Works

1. **Server Overview**: Shows comprehensive view of all MCP servers across applications
2. **Format Detection**: Automatically detects and converts between configuration formats
3. **Granular Control**: Select specific servers and target applications for syncing
4. **Real-time Validation**: Live sync status and error reporting
5. **Safety First**: Multiple confirmation steps prevent accidental operations

## 🛠️ Key Improvements

### 🎨 User Experience
- **Immediate Orientation**: Server overview at startup shows entire configuration landscape
- **Documentation-Friendly**: Paste any JSON format directly from README files
- **Visual Navigation**: Arrow keys with clear highlighting and number key fallbacks
- **Context Awareness**: Always shows which application you're modifying
- **Progressive Disclosure**: Start with overview, drill down to specific tasks

### 🔧 Technical Excellence
- **Multi-Format Support**: Handles 4+ different MCP configuration formats
- **Cross-Platform Input**: Custom keyboard handling for Windows, macOS, and Linux
- **Smart JSON Detection**: Auto-wraps partial configurations and detects formats
- **Real-time File Watching**: Automatic synchronization with debouncing
- **Comprehensive Validation**: Format-aware comparison with detailed reporting

### 🛡️ Safety & Reliability
- **Multiple Confirmation Points**: Prevents accidental broad syncs
- **Destructive Operation Protection**: User confirmation with detailed impact information
- **Format Preservation**: Maintains application-specific settings during sync
- **Error Recovery**: Clear messages with specific guidance for fixing issues

## 📋 Requirements

- **Python 3.7+**
- **macOS/Linux/Windows** (cross-platform)
- Dependencies listed in `requirements.txt` (primarily `watchdog` and `rich`)

## 🚦 Exit Codes

- `0`: Success
- `1`: Synchronization failed or validation errors

## 📄 License

MIT License

---

**🎯 Perfect for**: Developers managing MCP servers across multiple AI applications who want intuitive, interactive control with comprehensive overview and granular sync capabilities.
